# Copyright 2019 Virantha N. Ekanayake 
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Singleton interface to the Adafruit Bluetooth library"""
import Adafruit_BluefruitLE
from curio import Queue, sleep, CancelledError
import sys, functools, uuid

from .sensor import Button # Hack! only to get the button sensor_id for the fake attach message
from .process import Process
from .message_dispatch import MessageDispatch
from .const import USE_BLEAK

# Need a class to represent the bluetooth adapter provided
# by adafruit that receives messages
class BLEventQ(Process):
    """All bluetooth comms go through this object

       Provides interfaces to connect to a device/hub, send_messages to,
       and receive_messages from.  Also abstracts away the underlying bluetooth library
       that depends on the OS (Adafruit_Bluefruit for Mac, and Bleak for Linux/Win10)

       All requests to send messages to the BLE device must be inserted into
       the :class:`bricknil.BLEventQ.q` Queue object.

    """

    def __init__(self, ble):
        super().__init__('BLE Event Q')
        self.ble = ble
        self.q = Queue()
        if USE_BLEAK:
            self.message('using bleak')
            self.adapter = None
            # User needs to make sure adapter is powered up and on
            #    sudo hciconfig hci0 up
        else:
            self.message('Clearing BLE cache data')
            self.ble.clear_cached_data()
            self.adapter = self.ble.get_default_adapter()
            self.message(f'Found adapter {self.adapter.name}')
            self.message(f'Powering up adapter {self.adapter.name}')
            self.adapter.power_on()
        self.hubs = {}

    async def run(self):
        try:
            while True:
                msg = await self.q.get()
                msg_type, hub, msg_val = msg
                await self.q.task_done()
                self.message_debug(f'Got msg: {msg_type} = {msg_val}')
                await self.send_message(hub.tx, msg_val)
        except CancelledError:
            self.message(f'Terminating and disconnecxting')
            if USE_BLEAK:
                await self.ble.in_queue.put( 'quit' )
            else:
                self.device.disconnect()

    async def send_message(self, characteristic, msg):
        """Prepends a byte with the length of the msg and writes it to
           the characteristic

           Arguments:
              characteristic : An object from bluefruit, or if using Bleak,
                  a tuple (device, uuid : str)
              msg (bytearray) : Message with header
        """
        # Message needs to have length prepended
        length = len(msg)+1
        values = bytearray([length]+msg)
        if USE_BLEAK:
            device, char_uuid = characteristic
            await self.ble.in_queue.put( ('tx', (device, char_uuid, values)) )
        else:
            characteristic.write_value(values)

    async def get_messages(self, hub):
        """Instance a Message object to parse incoming messages and setup
           the callback from the characteristic to call Message.parse on the
           incoming data bytes
        """
        # Message instance to parse and handle messages from this hub
        msg_parser = MessageDispatch(hub)

        # Create a fake attach message on port 255, so that we can attach any instantiated Button listeners if present
        msg_parser.parse(bytearray([15, 0x00, 0x04,255, 1, Button._sensor_id, 0x00, 0,0,0,0, 0,0,0,0]))

        def bleak_received(sender, data):
            self.message_debug(f'Bleak Raw data received: {data}')
            msg = msg_parser.parse(data)
            self.message_debug('{0} Received: {1}'.format(hub.name, msg))
        def received(data):
            self.message_debug(f'Adafruit_Bluefruit Raw data received: {data}')
            msg = msg_parser.parse(data)
            self.message_debug('{0} Received: {1}'.format(hub.name, msg))

        if USE_BLEAK:
            device, char_uuid = hub.tx
            await self.ble.in_queue.put( ('notify', (device, char_uuid, bleak_received) ))
        else:
            # Adafruit library does not callback with the sender, only the data
            hub.tx.start_notify(received)


    def _check_devices_for(self, devices, name, manufacturer_id, address):
        """Check if any of the devices match what we're looking for
           
           First, check to make sure the manufacturer_id matches.  If the
           manufacturer_id is not present in the BLE advertised data from the 
           device, then fall back to the name (although this is unreliable because
           the name on the device can be changed by the user through the LEGO apps).

           Then, if address is supplied, only return a device with a matching id/name
           if it's BLE MAC address also agrees

           Returns:
              device : Matching device (None if no matches)
        """
        for device in devices:
            self.message(f'checking manufacturer ID for device named {device.name} for {name}')
            # Get the device manufacturer id from the advertised data if present
            if device.manufacturer_id == manufacturer_id or device.name == name:
                if not address:
                    return device
                else:
                    ble_address = device.address
                    if address == ble_address:
                        return device
                    else:
                        self.message(f'Address {ble_address} is not a match')
            else:
                self.message(f'No match for device with advertised data {device.manufacturer_id}')

        return None

    async def _ble_connect(self, uart_uuid, ble_name, ble_manufacturer_id, ble_id=None, timeout=60):
        """Connect to the underlying BLE device with the needed UART UUID
        """
        # Set hub.ble_id to a specific hub id if you want it to connect to a
        # particular hardware hub instance
        if ble_id:
            self.message_info(f'Looking for specific hub id {ble_id}')
        else:
            self.message_info(f'Looking for first matching hub')

        # Start discovery
        if not USE_BLEAK:
            self.adapter.start_scan()

        try:
            found = False
            while not found and timeout > 0:
                if USE_BLEAK:
                    await self.ble.in_queue.put('discover')  # Tell bleak to start discovery
                    devices = await self.ble.out_queue.get() # Wait for discovered devices
                    await self.ble.out_queue.task_done()
                    # Filter out no-matching uuid
                    devices = [d for d in devices if str(uart_uuid) in d.uuids]
                    # NOw, extract the manufacturer_id
                    for device in devices:
                        assert len(device.manufacturer_data) == 1
                        data = next(iter(device.manufacturer_data.values())) # Get the one and only key
                        device.manufacturer_id = data[1]
                else:
                    devices = self.ble.find_devices(service_uuids=[uart_uuid])
                    for device in devices:
                        self.message_info(f'advertised: {device.advertised}')
                        if len(device.advertised) > 4:
                            device.manufacturer_id = device.advertised[4]
                        else:
                            device.manufacturer_id = None
                        # Remap device.id to device.address to be consistent with bleak
                        device.address = device.id

                device = self._check_devices_for(devices, ble_name, ble_manufacturer_id,  ble_id)
                if device:
                    self.device = device
                    found = True
                else:
                    self.message(f'Rescanning for {uart_uuid} ({timeout} tries left)')
                    timeout -= 1
                    self.device = None
                    await sleep(1)
            if self.device is None:
                raise RuntimeError('Failed to find UART device!')
        except:
            raise
        finally:
            if not USE_BLEAK:
                self.adapter.stop_scan()


    async def connect(self, hub):
        """
            We probably need a different ble_queue type per operating system,
            and try to abstract away some of these hacks.

            Todo:
                * This needs to be cleaned up to get rid of all the hacks for
                  different OS and libraries

        """
        # Connect the messaging queue for communication between self and the hub
        hub.message_queue = self.q
        self.message(f'Starting scan for UART {hub.uart_uuid}')

        # HACK
        try:
            ble_id = uuid.UUID(hub.ble_id) if hub.ble_id else None
        except ValueError:
            # In case the user passed in a 
            self.message_info(f"ble_id {hub.ble_id} is not a parseable UUID, so assuming it's a BLE network addresss")
            ble_id = hub.ble_id

        await self._ble_connect(hub.uart_uuid, hub.ble_name, hub.manufacturer_id, ble_id)

        self.message(f"found device {self.device.name}")

        if USE_BLEAK:
            await self.ble.in_queue.put( ('connect', self.device.address) )
            device = await self.ble.out_queue.get()
            await self.ble.out_queue.task_done()
            hub.ble_id = self.device.address
            self.message_info(f'Device advertised: {device.characteristics}')
            hub.tx = (device, hub.char_uuid)   # Need to store device because the char is not an object in Bleak, unlike Bluefruit library
            # Hack to fix device name on Windows
            if self.device.name == "Unknown" and hasattr(device._requester, 'Name'):
                self.device.name = device._requester.Name
        else:
            self.device.connect()
            hub.ble_id = self.device.id
            # discover services
            self.device.discover([hub.uart_uuid], [hub.char_uuid])
            uart = self.device.find_service(hub.uart_uuid)
            hub.tx = uart.find_characteristic(hub.char_uuid) # same for rx
            self.message_info(f'Device advertised {self.device.advertised}')


        self.message_info(f"Connected to device {self.device.name}:{hub.ble_id}")
        self.hubs[hub.ble_id] = hub

        await self.get_messages(hub)




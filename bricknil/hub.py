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

"""Hub processes for the Boost Move and PoweredUp hubs

"""
import uuid
from curio import sleep, UniversalQueue, CancelledError
from .process import Process
from .sensor.peripheral import Peripheral  # for type check
from .const import USE_BLEAK
from .sockets import WebMessage

class UnknownPeripheralMessage(Exception): pass
class DifferentPeripheralOnPortError(Exception): pass

# noinspection SpellCheckingInspection
class Hub(Process):
    """Base class for all Lego hubs

       Arguments:
            name (str) : Human-readable name for this hub (for logging)
            query_port_info (bool) : Set to True if you want to query all the port information on a Hub (very communication intensive)
            ble_id (str) : BluetoothLE network(MAC) adddress to connect to (None if you want to connect to the first matching hub)

       Attributes:
      
            hubs (list [`Hub`]) : Class attr to keep track of all Hub (and subclasses) instances
            message_queue (`curio.Queue`) : Outgoing message queue to :class:`bricknil.ble_queue.BLEventQ`
            peripheral_queue (`curio.UniversalQueue`) : Incoming messages from :class:`bricknil.ble_queue.BLEventQ`
            uart_uuid (`uuid.UUID`) : UUID broadcast by LEGO UARTs
            char_uuid (`uuid.UUID`) : Lego uses only one service characteristic for communicating with the UART services
            tx : Service characteristic for tx/rx messages that's set by :func:`bricknil.ble_queue.BLEventQ.connect`
            peripherals (dict) : Peripheral name => `bricknil.Peripheral`
            port_to_peripheral (dict): Port number(int) -> `bricknil.Peripheral`
            port_info (dict):  Keeps track of all the meta-data for each port.  Usually not populated unless `query_port_info` is true

    """
    hubs = []

    # noinspection SpellCheckingInspection,SpellCheckingInspection,SpellCheckingInspection,SpellCheckingInspection
    def __init__(self, name, query_port_info=False, ble_id=None):
        super().__init__(name)
        self.ble_id = ble_id
        self.query_port_info = query_port_info
        self.message_queue = None
        self.uart_uuid = uuid.UUID('00001623-1212-efde-1623-785feabcd123')
        self.char_uuid = uuid.UUID('00001624-1212-efde-1623-785feabcd123')
        self.tx = None
        self.peripherals = {}  # attach_sensor method will add sensors to this
        self.port_to_peripheral = {}   # Quick mapping from a port number to a peripheral object
                                        # Only gets populated once the peripheral attaches itself physically
        self.peripheral_queue = UniversalQueue()  # Incoming messages from peripherals

        # Keep track of port info as we get messages from the hub ('update_port' messages)
        self.port_info = {}

        # Register this hub
        Hub.hubs.append(self)

        # Outgoing messages to web client
        # Assigned during system instantiaion before ble connect
        self.web_queue_out = None

        self.web_message = WebMessage(self)


    async def send_message(self, msg_name, msg_bytes, peripheral=None):
        """Insert a message to the hub into the queue(:func:`bricknil.hub.Hub.message_queue`) connected to our BLE
           interface

        """

        while not self.tx:  # Need to make sure we have a handle to the uart
            await sleep(1)
        await self.message_queue.put((msg_name, self, msg_bytes))
        if self.web_queue_out and peripheral:
            cls_name = peripheral.__class__.__name__
            await self.web_message.send(peripheral, msg_name)
            #await self.web_queue_out.put( f'{self.name}|{cls_name}|{peripheral.name}|{peripheral.port}|{msg_name}\r\n'.encode('utf-8') )

    async def peripheral_message_loop(self):
        """The main loop that receives messages from the :class:`bricknil.messages.Message` parser.

           Waits for messages on a UniversalQueue and dispatches to the appropriate peripheral handler.
        """
        try:
            self.message_debug(f'starting peripheral message loop')

            # Check if we have any hub button peripherals attached
            # - If so, we need to manually call peripheral.activate_updates()
            # - and then register the proper handler inside the message parser
            while True:
                msg = await self.peripheral_queue.get()
                msg, data = msg
                await self.peripheral_queue.task_done()
                if msg == 'value_change':
                    port, msg_bytes = data
                    peripheral = self.port_to_peripheral[port]
                    await peripheral.update_value(msg_bytes)
                    self.message_debug(f'peripheral msg: {peripheral} {msg}')
                    if self.web_queue_out:
                        cls_name = peripheral.__class__.__name__
                        if len(peripheral.capabilities) > 0:
                            for cap in peripheral.value:
                                await self.web_message.send(peripheral, f'value change mode: {cap.value} = {peripheral.value[cap]}')
                                #await self.web_queue_out.put( f'{self.name}|{cls_name}|{peripheral.name}|{peripheral.port}|value change mode: {cap.value} = {peripheral.value[cap]}\r\n'.encode('utf-8') )
                    handler_name = f'{peripheral.name}_change'
                    handler = getattr(self, handler_name)
                    await handler()
                elif msg == 'attach':
                    port, device_name = data
                    peripheral = await self.connect_peripheral_to_port(device_name, port)
                    if peripheral:
                        self.message_debug(f'peripheral msg: {peripheral} {msg}')
                        peripheral.message_handler = self.send_message
                        await peripheral.activate_updates()
                elif msg == 'update_port':
                    port, info = data
                    self.port_info[port] = info
                elif msg.startswith('port'):
                    port = data
                    if self.query_port_info:
                        await self._get_port_info(port, msg)
                else:
                    raise UnknownPeripheralMessage
                    

        except CancelledError:
            self.message(f'Terminating peripheral')

    async def connect_peripheral_to_port(self, device_name, port):
        """Set the port number of the newly attached peripheral
        
        When the hub gets an Attached I/O message on a new port with the device_name,
        this method is called to find the peripheral it should set this port to.  If
        the user has manually specified a port, then this function just validates that
        the peripheral name the user has specified on that port is the same as the one
        that just attached itself to the hub on that port.

        """
        # register the handler for this IO
        #  - Check the hub to see if there's a matching device or port
        for peripheral_name, peripheral in self.peripherals.items():
            if peripheral.port == port:
                if device_name == peripheral.sensor_name:
                    self.port_to_peripheral[port] = peripheral
                    return peripheral
                else:
                    raise DifferentPeripheralOnPortError

        # This port has not been reserved for a specific peripheral, so let's just 
        # search for the first peripheral with a matching name and attach this port to it
        for peripheral_name, peripheral in self.peripherals.items():
            if peripheral.sensor_name == device_name and peripheral.port == None:
                peripheral.message(f"ASSIGNING PORT {port} on {peripheral.name}")
                peripheral.port = port
                self.port_to_peripheral[port] = peripheral
                return peripheral

        # User hasn't specified a matching peripheral, so just ignore this attachment
        return None


    def attach_sensor(self, sensor: Peripheral):
        """Add instance variable for this decorated sensor

           Called by the class decorator :class:`bricknil.bricknil.attach` when decorating the sensor
        """
        # Check that we don't already have a sensor with the same name attached
        assert sensor.name not in self.peripherals, f'Duplicate {sensor.name} found!'
        self.peripherals[sensor.name] = sensor
        # Put this sensor as an attribute
        setattr(self, sensor.name, sensor)

    async def _get_port_info(self, port, msg):
        """Utility function to query information on available ports and modes from a hub.
           
        """
        if msg == 'port_detected':
            # Request mode info
            b = [0x00, 0x21, port, 0x01]
            await self.send_message(f'req mode info on {port}', b)
        elif msg == 'port_combination_info_received':
            pass
        elif msg == 'port_mode_info_received':
            pass
        elif msg == 'port_info_received':
            # At this point we know all the available modes for this port
            # let's get the name and value format
            modes = self.port_info[port]['modes']
            if self.port_info[port].get('combinable', False):
                # Get combination info on port
                b = [0x00, 0x21, port, 0x02]
                await self.send_message(f'req mode combination info on {port}', b)
            for mode in modes.keys():
                info_types = { 'NAME': 0, 'VALUE FORMAT':0x80, 'RAW Range':0x01,
                        'PCT Range': 0x02, 'SI Range':0x03, 'Symbol':0x04,
                        'MAPPING': 0x05,
                        }
                # Send a message to requeust each type of info 
                for k,v in info_types.items():
                    b = [0x00, 0x22, port, mode, v]
                    await self.send_message(f'req info({k}) on mode {mode} {port}', b)


class PoweredUpHub(Hub):
    """PoweredUp Hub class 
    """
    def __init__(self, name, query_port_info=False, ble_id=None):
        super().__init__(name, query_port_info, ble_id)
        self.ble_name = 'HUB NO.4'
        self.manufacturer_id = 65

class PoweredUpRemote(Hub):
    """PoweredUp Remote class 
    """
    def __init__(self, name, query_port_info=False, ble_id=None):
        super().__init__(name, query_port_info, ble_id)
        self.ble_name = 'Handset'
        self.manufacturer_id = 66

class BoostHub(Hub):
    """Boost Move Hub
    """
    def __init__(self, name, query_port_info=False, ble_id=None):
        super().__init__(name, query_port_info, ble_id)
        self.ble_name = 'LEGO Move Hub'
        self.manufacturer_id = 64


class DuploTrainHub(Hub):
    """Duplo Steam train and Cargo Train

       This is hub is found in Lego sets 10874 and 10875
    """
    def __init__(self, name, query_port_info=False, ble_id=None):
        super().__init__(name, query_port_info, ble_id)
        self.ble_name = 'Train Base'
        self.manufacturer_id = 32


class CPlusHub(Hub):
    """Technic Control+ Hub
    """
    def __init__(self, name, query_port_info=False, ble_id=None):
        super().__init__(name, query_port_info, ble_id)
        self.ble_name = "Control+ Hub"
        self.manufacturer_id = 128

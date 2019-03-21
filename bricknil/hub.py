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
from .peripheral import Peripheral  # for type check
from .const import USE_BLEAK


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
        self.peripheral_queue = UniversalQueue()  # Incoming messages from peripherals

        # Keep track of port info as we get messages from the hub ('update_port' messages)
        self.port_info = {}

        # Register this hub
        Hub.hubs.append(self)

    async def send_message(self, msg_name, msg_bytes):
        """Insert a message to the hub into the queue(:func:`bricknil.hub.Hub.message_queue`) connected to our BLE
           interface

        """

        while not self.tx:  # Need to make sure we have a handle to the uart
            await sleep(1)
        await self.message_queue.put((msg_name, self, msg_bytes))

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
                peripheral, msg = msg
                await self.peripheral_queue.task_done()
                if msg == 'value_change':
                    self.message_debug(f'peripheral msg: {peripheral} {msg}')
                    handler_name = f'{peripheral.name}_change'
                    handler = getattr(self, handler_name)
                    await handler()
                elif msg == 'attach':
                    self.message_debug(f'peripheral msg: {peripheral} {msg}')
                    peripheral.message_handler = self.send_message
                    peripheral.enabled = True
                    await peripheral.activate_updates()
                elif msg == 'update_port':
                    port, info = peripheral
                    self.port_info[port] = info
                elif msg.startswith('port'):
                    if self.query_port_info:
                        await self._get_port_info(peripheral, msg)

        except CancelledError:
            self.message(f'Terminating peripheral')

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

class PoweredUpRemote(Hub):
    """PoweredUp Remote class 
    """
    def __init__(self, name, query_port_info=False, ble_id=None):
        super().__init__(name, query_port_info, ble_id)
        self.ble_name = 'Handset'

class BoostHub(Hub):
    """Boost Move Hub
    """
    def __init__(self, name, query_port_info=False, ble_id=None):
        super().__init__(name, query_port_info, ble_id)
        self.ble_name = 'LEGO Move Hub'

class DuploTrainHub(Hub):
    """Duplo Steam train and Cargo Train

       This is hub is found in Lego sets 10874 and 10875
    """
    def __init__(self, name, query_port_info=False, ble_id=None):
        super().__init__(name, query_port_info, ble_id)
        self.ble_name = 'Train Base'

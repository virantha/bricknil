"""Hub processes for the Boost Move and PoweredUp hubs

"""
import uuid
from curio import sleep, UniversalQueue, CancelledError
from .process import Process
from .peripheral import Peripheral  # for type check


# noinspection SpellCheckingInspection
class Hub(Process):
    """Base class for all Lego hubs

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
    def __init__(self, name):
        super().__init__(name)
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
            self.message(f'starting peripheral message loop')

            # Check if we have any hub button peripherals attached
            # - If so, we need to manually call peripheral.activate_updates()
            # - and then register the proper handler inside the message parser
            while True:
                msg = await self.peripheral_queue.get()
                peripheral, msg = msg
                await self.peripheral_queue.task_done()
                if msg == 'value_change':
                    self.message(f'peripheral msg: {peripheral} {msg}')
                    handler_name = f'{peripheral.name}_change'
                    handler = getattr(self, handler_name)
                    await handler()
                elif msg == 'attach':
                    self.message(f'peripheral msg: {peripheral} {msg}')
                    peripheral.message_handler = self.send_message
                    peripheral.enabled = True
                    await peripheral.activate_updates()
                elif msg == 'update_port':
                    port, info = peripheral
                    self.port_info[port] = info
                elif msg.startswith('port'):
                    pass
                    #await self._get_port_info(peripheral, msg)

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
                b = [0x00, 0x22, port, mode, 0]
                await self.send_message(f'req info(NAME) on mode {mode} {port}', b)
                b = [0x00, 0x22, port, mode, 0x80]
                await self.send_message(f'req info(VALUE FORMAT) on mode {mode} {port}', b)
        return


class PoweredUpHub(Hub):
    """PoweredUp Hub class 

       Override `ble_id` instance variable if you want to connect to a specific physical Hub. This
       is useful if you have multiple hubs running at the same time performing different functions.
    """

    def __init__(self, name):
        super().__init__(name)
        self.ble_name = 'HUB NO.4'
        self.ble_id = None  # Override and set this if you want to connect ta known hub

class PoweredUpRemote(Hub):
    """PoweredUp Remote class 

       Override `ble_id` instance variable if you want to connect to a specific physical Hub. This
       is useful if you have multiple hubs running at the same time performing different functions.
    """

    def __init__(self, name):
        super().__init__(name)
        self.ble_name = 'Handset'
        self.ble_id = None  # Override and set this if you want to connect ta known hub

class BoostHub(Hub):
    """Boost Move Hub

       Override `ble_id` instance variable if you want to connect to a specific physical Hub. This
       is useful if you have multiple hubs running at the same time performing different functions.
    """

    def __init__(self, name):
        super().__init__(name)
        self.ble_name = 'LEGO Move Hub'
        self.ble_id = None  # Override and set this if you want to connect ta known hub

"""Singleton interface to the Adafruit Bluetooth library"""
import Adafruit_BluefruitLE
from curio import Queue, sleep, CancelledError

from .sensor import Button # Hack! only to get the button sensor_id for the fake attach message
from .process import Process
from .messages import Message

# Need a class to represent the bluetooth adapter provided
# by adafruit that receives messages
class BLEventQ(Process):


    def __init__(self, ble):
        super().__init__('BLE Event Q')
        self.ble = ble
        self.q = Queue()
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
                self.message(f'Got msg: {msg_type} = {msg_val}')
                await self.q.task_done()
                await self.send_message(hub.tx, msg_val)
        except CancelledError:
            self.message(f'Terminating and disconnecxting')
            self.device.disconnect()

    async def send_message(self, characteristic, msg):
        # Message needs to have length prepended
        length = len(msg)+1
        values = bytearray([length]+msg)
        characteristic.write_value(values)

    async def get_messages(self, hub):
        # Register  Message instance to parse and handle messages from this hub
        msg_parser = Message(hub)

        # Create a fake attach message on port 255, so that we can attach any instantiated Button listeners if present
        msg_parser.parse(bytearray([15, 0x00, 0x04,255, 1, Button._sensor_id, 0x00, 0,0,0,0, 0,0,0,0]))

        def received(data):
            self.message(f'Raw data received: {data}')
            msg = msg_parser.parse(data)
            self.message('{0} Received: {1}'.format(hub.name, msg))
        hub.tx.start_notify(received)

    async def connect(self, hub):
        # Connect the messaging queue for communication between self and the hub
        hub.message_queue = self.q

        uart_uuid = hub.uart_uuid
        char_uuid = hub.char_uuid
        #self.message('Disconnecting any connected UART devices')
        #self.ble.disconnect_devices([uart_uuid])
        self.message(f'Starting scan for UART {uart_uuid}')

        # Set hub.ble_id to a specific hub id if you want it to connect to a
        # particular hardware hub instance
        if hub.ble_id:
            self.message_info(f'Looking for specific hub id {hub.ble_id}')
        else:
            self.message_info(f'Looking for first matching hub')

        self.adapter.start_scan()
        try:
            timeout = 60
            found = False
            while not found and timeout > 0 :
                #self.device = self.ble.find_device(service_uuids=[uart_uuid])
                devices = self.ble.find_devices(service_uuids=[uart_uuid])
                
                for device in devices:
                    self.message(f'checking device named {device.name}')
                    if device.name == hub.ble_name:
                        if not hub.ble_id or hub.ble_id == device.id:
                            found = True
                            self.device = device
                            break
                        else:
                            self.message(f'found device id{device.id}')
                            self.message(f'found device id {type(device.id)}')
                if not found:
                    self.message(f'Rescanning for {uart_uuid} ({timeout}sec left)')
                    timeout -= 1
                    self.device = None
                    await sleep(1)
            if self.device is None:
                raise RuntimeError('Failed to find UART device!')
            assert self.device.name == hub.ble_name
        except:
            raise
        finally:
            self.adapter.stop_scan()
        self.message("found device!")
        self.device.connect()
        self.message_info("Connected to device")

        # Discover services
        self.device.discover([uart_uuid], [char_uuid])
        uart = self.device.find_service(uart_uuid)
        rx = uart.find_characteristic(char_uuid)
        self.message_info(f'Device name {self.device.name}')
        self.message_info(f'Device id {self.device.id}')
        self.message_info(f'Device advertised {self.device.advertised}')
        hub.ble_id = self.device.id
        hub.tx = rx
        self.hubs[self.device.id] = hub

        await self.get_messages(hub)
        return self.adapter




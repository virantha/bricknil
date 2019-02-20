"""Hub process that the Boost and PoweredUp hubs inherit from

"""
import uuid
from collections import OrderedDict
from curio import sleep, UniversalQueue, CancelledError
from enum import Enum
from .process import Process
from .sensor import Button # Hack to get sensor_id of Button

class Hub(Process):
    hubs = []

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
        while not self.tx:  # Need to make sure we have a handle to the uart
            await sleep(1)
        await self.message_queue.put( (msg_name, self, msg_bytes))

    async def peripheral_message_loop(self):
        try:
            self.message(f'starting peripheral message loop')

            # Check if we have any hub botton peripherals attached
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
                    #await self._get_port_info(peripheral.port, msg)
                elif msg == 'update_port':
                    port, info = peripheral
                    #self.message(f'Port info update: {port} {info}')
                    self.port_info[port] = info
                elif msg.startswith('port'):
                    await self._get_port_info(peripheral, msg)

                    
        except CancelledError:
            self.message(f'Terminating peripheral')

    def attach_sensor(self, sensor):
        # Check that we don't already have a sensor with the same name attached
        assert not sensor.name in self.peripherals, f'Duplicate {sensor.name} found!'
        self.peripherals[sensor.name] = sensor
        # Put this sensor as an attribute
        setattr(self, sensor.name, sensor)


    
    async def _get_port_info(self, port, msg):
        if msg == 'port_detected':
            # Request mode info
            b = [0x00, 0x21, port, 0x01]
            await self.send_message(f'req mode info on {port}', b)
        elif msg =='port_info_received':
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

        # Now get information on each mode and the name
        for mode in range(16):
            b = [0x00, 0x22, port, mode, 0] 
            await self.send_message(f'req info(NAME) on mode {mode} {port}', b)
            b = [0x00, 0x22, port, mode, 0x80] 
            await self.send_message(f'req info(VALUE FORMAT) on mode {mode} {port}', b)
        # Now get information on each mode data values
        for mode in range(16):
            b = [0x00, 0x22, port, mode, 128] 
            await self.send_message(f'req info on mode {mode} {port}', b)

class PoweredUpHub(Hub):

    def __init__(self, name):
        super().__init__(name)
        self.ble_name = 'HUB NO.4'
        self.ble_id = None  # Override and set this if you want to connec ta known hub


class BoostHub(Hub):

    def __init__(self, name):
        super().__init__(name)
        self.ble_name = 'LEGO Move Hub'
        self.ble_id = None  # Override and set this if you want to connec ta known hub



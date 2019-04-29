import pytest
import os, struct, copy, sys
from functools import partial
import logging, threading
from asyncio import coroutine
from curio import kernel, sleep, spawn, Event
import time

from mock import Mock
from mock import patch, call, create_autospec
from mock import MagicMock
from mock import PropertyMock

from hypothesis import given, example, settings
from hypothesis import strategies as st

from bricknil.message_dispatch import MessageDispatch
from bricknil.messages import UnknownMessageError, HubPropertiesMessage
from bricknil.sensor import *
from bricknil.const import DEVICES
from bricknil import attach, start
from bricknil.hub import PoweredUpHub, Hub, BoostHub, DuploTrainHub, PoweredUpRemote
import bricknil
import bricknil.const


class TestSensors:

    def setup(self):
        # Create the main dispatch
        self.hub = MagicMock()
        self.m = MessageDispatch(self.hub)
        self.sensor_list = [ CurrentSensor,
                             DuploSpeedSensor,
                             VisionSensor,
                             InternalTiltSensor,
                             ExternalMotionSensor,
                             ExternalTiltSensor,
                             RemoteButtons,
                             Button,
                             DuploVisionSensor,
                             VoltageSensor,
        ]
        self.hub_list = [ PoweredUpHub, BoostHub, DuploTrainHub, PoweredUpRemote]
    
    def _with_header(self, msg:bytearray):
        l = len(msg)+2
        assert l<127
        return bytearray([l, 0]+list(msg))

    def _draw_capabilities(self, data, sensor):
        if len(sensor.allowed_combo) > 0:
            # test capabilities 1 by 1, 
            # or some combination of those in the allowed_combo list
            capabilities = data.draw(
                    st.one_of(
                        st.lists(st.sampled_from([cap.name for cap in list(sensor.capability)]), min_size=1, max_size=1),
                        st.lists(st.sampled_from(sensor.capability), min_size=1, max_size=1),
                        st.lists(st.sampled_from(sensor.allowed_combo), min_size=1, unique=True)
                    )
                )
        else:
            # if no combos allowed, then just test 1 by 1
            capabilities = data.draw(st.lists(st.sampled_from(sensor.capability), min_size=1, max_size=1))
        return capabilities


    def _get_hub_class(self, hub_type, sensor, sensor_name, capabilities):
        stop_evt = Event()
        @attach(sensor, name=sensor_name, capabilities=capabilities)
        class TestHub(hub_type):
            async def sensor_change(self):
                pass
            async def run(self):
                pass
                await stop_evt.wait()

        return TestHub, stop_evt

    #@patch('bricknil.hub.PoweredUpHub', autospec=True, create=True)
    @given(data = st.data())
    def test_attach_sensor(self, data):
        
        sensor_name = 'sensor'
        sensor = data.draw(st.sampled_from(self.sensor_list))
        capabilities = self._draw_capabilities(data, sensor)

        hub_type = data.draw(st.sampled_from(self.hub_list))
        TestHub, stop_evt = self._get_hub_class(hub_type, sensor, sensor_name, capabilities)
        hub = TestHub('testhub')
        # Check to make sure we have the peripheral attached
        # and the sensor inserted as an attribute
        assert sensor_name in hub.peripherals
        assert hasattr(hub, sensor_name)

    @given(data = st.data())
    def test_run_hub(self, data):

        Hub.hubs = []
        sensor_name = 'sensor'
        sensor = data.draw(st.sampled_from(self.sensor_list))
        capabilities = self._draw_capabilities(data, sensor)

        hub_type = data.draw(st.sampled_from(self.hub_list))
        TestHub, stop_evt = self._get_hub_class(hub_type, sensor, sensor_name, capabilities)
        hub = TestHub('test_hub')

        # Start the hub
        #kernel.run(self._emit_control(TestHub))
        with patch('Adafruit_BluefruitLE.get_provider') as ble,\
             patch('bricknil.ble_queue.USE_BLEAK', False) as use_bleak:
            ble.return_value = MockBLE(hub)
            sensor_obj = getattr(hub, sensor_name)
            sensor_obj.send_message = Mock(side_effect=coroutine(lambda x,y: "the awaitable should return this"))
            kernel.run(self._emit_control, data, hub, stop_evt, ble(), sensor_obj)
            #start(system)

    async def _wait_send_message(self, mock_call, msg):
        print("in mock")
        while not mock_call.call_args:
            await sleep(0.01)
        while not msg in mock_call.call_args[0][0]:
            print(mock_call.call_args)
            await sleep(0.01)

    async def _emit_control(self, data, hub, hub_stop_evt, ble, sensor):
        async def dummy():
            pass
        system = await spawn(bricknil.bricknil._run_all(ble, dummy))
        while not hub.peripheral_queue:
            await sleep(0.1)
        #await sleep(3)
        port = data.draw(st.integers(0,254))
        await hub.peripheral_queue.put( ('attach', (port, sensor.sensor_name)) )

        # Now, make sure the sensor sent an activate updates message
        if sensor.sensor_name == "Button":
            await self._wait_send_message(sensor.send_message, 'Activate button')
        else:
            await self._wait_send_message(sensor.send_message, 'Activate SENSOR')
        # Need to generate a value on the port
        # if False:
        msg = []
        if len(sensor.capabilities) == 1:
            # Handle single capability
            for cap in sensor.capabilities:
                n_datasets, byte_count = sensor.datasets[cap][0:2]
                for i in range(n_datasets):
                    for b in range(byte_count):
                        msg.append(data.draw(st.integers(0,255)))
            msg = bytearray(msg)
            await hub.peripheral_queue.put( ('value_change', (port, msg)))
        elif len(sensor.capabilities) > 1:
            modes = 1
            msg.append(modes)
            for cap_i, cap in enumerate(sensor.capabilities):
                if modes & (1<<cap_i): 
                    n_datasets, byte_count = sensor.datasets[cap][0:2]
                    for i in range(n_datasets):
                        for b in range(byte_count):
                            msg.append(data.draw(st.integers(0,255)))
            msg = bytearray(msg)
            await hub.peripheral_queue.put( ('value_change', (port, msg)))
        
        await hub_stop_evt.set()
        await system.join()

    @given(data = st.data())
    def test_run_hub_with_bleak(self, data):

        Hub.hubs = []
        sensor_name = 'sensor'
        sensor = data.draw(st.sampled_from(self.sensor_list))
        capabilities = self._draw_capabilities(data, sensor)

        hub_type = data.draw(st.sampled_from(self.hub_list))
        TestHub, stop_evt = self._get_hub_class(hub_type, sensor, sensor_name, capabilities)
        hub = TestHub('test_hub')

        async def dummy():
            pass
        # Start the hub
        #MockBleak = MagicMock()
        sys.modules['bleak'] = MockBleak(hub)
        with patch('bricknil.bricknil.USE_BLEAK', True), \
             patch('bricknil.ble_queue.USE_BLEAK', True) as use_bleak:
            sensor_obj = getattr(hub, sensor_name)
            sensor_obj.send_message = Mock(side_effect=coroutine(lambda x,y: "the awaitable should return this"))
            from bricknil.bleak_interface import Bleak
            ble = Bleak()
            # Run curio in a thread
            async def dummy(): pass

            async def start_curio():
                system = await spawn(bricknil.bricknil._run_all(ble, dummy))
                while len(ble.devices) < 1 or not ble.devices[0].notify:
                    await sleep(0.01)
                await stop_evt.set()
                print("sending quit")
                await ble.in_queue.put( ('quit', ''))
                #await system.join()
                print('system joined')

            def start_thread():
                kernel.run(start_curio)

            t = threading.Thread(target=start_thread)
            t.start()
            print('started thread for curio')
            ble.run()
            t.join()




class MockBleak(MagicMock):
    def __init__(self, hub):
        MockBleak.hub = hub
        pass
    @classmethod
    async def discover(cls, timeout, loop):
        # Need to return devices here, which is a list of device tuples
        hub = MockBleak.hub
        devices = [MockBleakDevice(hub.uart_uuid, hub.manufacturer_id)]
        return devices

    @classmethod
    def BleakClient(cls, address, loop):
        print("starting BleakClient")
        hub = MockBleak.hub
        device = MockBleakDevice(hub.uart_uuid, hub.manufacturer_id)
        return device

class MockBleakDevice:
    def __init__(self, uuid, manufacturer_id):
        self.uuids = [str(uuid)]
        self.manufacturer_data = {'values': [0, manufacturer_id]  }
        self.name = ""
        self.address = "XX:XX:XX:XX:XX" 
        self.notify = False

    async def connect(self):
        self.characteristics = MockBleak.hub.char_uuid
        pass
    async def write_gatt_char(self, char_uuid, msg_bytes):
        print(f'Got msg on {char_uuid}: {msg_bytes}')

    async def start_notify(self, char_uuid, handler):
        print("started notify")
        self.notify = True

    async def disconnect(self):
        print("device disconnected")

class MockBLE:
    def __init__(self, hub):
        self.hub = hub

    def initialize(self):
        print("initialized")
    
    def clear_cached_data(self):
        pass

    def get_default_adapter(self):
        self.mock_adapter = MockAdapter()
        return self.mock_adapter

    def find_devices(self, service_uuids):
        self.device = MockDevice(hub_name = self.hub.ble_name, hub_id = self.hub.manufacturer_id)
        return [self.device]

    def run_mainloop_with(self, func):
        print("run mainloop")
        func()

class MockAdapter:
    def __init__(self):
        self.name = 'Mock adapter'
    def power_on(self):
        pass

    def start_scan(self):
        print("start scan called")

    def stop_scan(self):
        print("stop scan called")

class MockDevice:
    def __init__(self, hub_name, hub_id):
        self.advertised = [-1, -1, -1, -1, hub_id]
        self.id = 'XX:XX:XX:XX:XX:XX'
        self.name = hub_name

    def connect(self):
        print("device connect called")

    def discover(self, uart_uuid, char_uuid):
        print(f'discover called on uart {uart_uuid}, char {char_uuid}')
        self.uart_uuid = uart_uuid
        self.char = char_uuid
    
    def find_service(self, uart_uuid):
        self.uart = MockUart()
        return self.uart

    def disconnect(self):
        print('device disconnect called')


class MockUart:
    def __init__(self):
        pass
    def find_characteristic(self, char_uuid):
        self.char_uuid = char_uuid
        return self

    def start_notify(self, callback):
        # Spawn a task to do the attachments, etc
        self.notify = callback

    def write_value(self, values):
        print(f'received values: {values}')
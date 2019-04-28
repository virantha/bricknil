import pytest
import os, struct, copy
import logging
from asyncio import coroutine
from curio import kernel, sleep, spawn

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
from bricknil.hub import PoweredUpHub, Hub
import bricknil

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
                        st.lists(st.sampled_from(sensor.capability), min_size=1, max_size=1),
                        st.lists(st.sampled_from(sensor.allowed_combo), min_size=1, unique=True)
                    )
                )
        else:
            # if no combos allowed, then just test 1 by 1
            capabilities = data.draw(st.lists(st.sampled_from(sensor.capability), min_size=1, max_size=1))
        return capabilities


    def _get_hub_class(self, sensor, sensor_name, capabilities):
        @attach(sensor, name=sensor_name, capabilities=capabilities)
        class TestHub(PoweredUpHub):
            async def sensor_change(self):
                pass
            async def run(self):
                pass
        return TestHub

    #@patch('bricknil.hub.PoweredUpHub', autospec=True, create=True)
    @given(data = st.data())
    def test_attach_sensor(self, data):
        
        sensor_name = 'sensor'
        sensor = data.draw(st.sampled_from(self.sensor_list))
        capabilities = self._draw_capabilities(data, sensor)

        TestHub = self._get_hub_class(sensor, sensor_name, capabilities)
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

        TestHub = self._get_hub_class(sensor, sensor_name, capabilities)('testhub')

        # Start the hub
        #kernel.run(self._emit_control(TestHub))

        with patch('Adafruit_BluefruitLE.get_provider') as ble:
            ble.return_value = MockBLE()
            sensor_obj = getattr(TestHub, sensor_name)
            kernel.run(self._emit_control, TestHub, ble(), sensor_obj)
            #start(system)

    async def _emit_control(self, hub, ble, sensor):
        async def dummy():
            pass
        system = await spawn(bricknil.bricknil._run_all(ble, dummy))
        while not hub.peripheral_queue:
            await sleep(0.1)
        #await sleep(3)
        await hub.peripheral_queue.put( ('attach', (1, sensor.sensor_name)) )
        await system.join()

class MockBLE:
    def initialize(self):
        print("initialized")
    
    def clear_cached_data(self):
        pass

    def get_default_adapter(self):
        self.mock_adapter = MockAdapter()
        return self.mock_adapter

    def find_devices(self, service_uuids):
        self.device = MockDevice()
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
    def __init__(self):
        self.advertised = [-1, -1, -1, -1, 65]
        self.id = 'XX:XX:XX:XX:XX:XX'
        self.name = 'HUB No.4'

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
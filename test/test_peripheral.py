import pytest
import os, struct, copy
import logging
from asyncio import coroutine
from curio import kernel, sleep

from mock import Mock
from mock import patch, call
from mock import MagicMock
from mock import PropertyMock

from hypothesis import given, example, settings
from hypothesis import strategies as st

from bricknil.sensor.light import *
from bricknil.sensor.motor import *
from bricknil.sensor.sound import *
from bricknil.const import Color

class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

class DirectWrite:
    def get_bytes(self, port, mode, value):
        return [0x00, 0x81, port, 0x01, 0x51, mode, value ]

    def get_bytes_for_set_pos(self, port, pos, speed, max_power):
        abs_pos = list(struct.pack('i', pos))
        return [0x00, 0x81, port, 0x01, 0x0d] + abs_pos + [speed, max_power, 126, 3]
        
    def get_bytes_for_rotate(self, port, angle, speed, max_power):
        angle = list(struct.pack('i',angle))
        return [0x00, 0x81, port, 0x01, 0x0b] +  angle + [speed, max_power, 126, 3]

class TestLED:

    def setup(self):
        self.l = LED(name='led')
        self.l.send_message = Mock(side_effect=coroutine(lambda x,y: "the awaitable should return this"))
        self.write = DirectWrite()

    @pytest.mark.curio
    async def test_set_color(self):
        port = 10
        self.l.port = port
        await self.l.set_color(Color.blue)
        self.l.send_message.ask_called_once()
        args, kwargs = self.l.send_message.call_args
        assert args[1] == self.write.get_bytes(port, 0, Color.blue.value)

class TestLight:

    def setup(self):
        self.l = Light(name='light')
        self.l.send_message = Mock(side_effect=coroutine(lambda x,y: "the awaitable should return this"))
        self.write = DirectWrite()

    @given( brightness = st.integers(0,100),
            port = st.integers(0,255)
    )
    def test_set_brightness(self, port, brightness):
        self.l.port = port

        async def child():
            await self.l.set_brightness(brightness)
        kernel.run(child)

        self.l.send_message.ask_called_once()
        args, kwargs = self.l.send_message.call_args
        assert args[1] == self.write.get_bytes(port, 0, brightness)

class TestSpeaker:

    def setup(self):
        self.l = DuploSpeaker(name='light')
        self.l.send_message = Mock(side_effect=coroutine(lambda x,y: "the awaitable should return this"))
        self.write = DirectWrite()

    @given( sound = st.sampled_from(DuploSpeaker.sounds),
            port = st.integers(0,255)
    )
    def test_play_sound(self, port, sound):
        self.l.port = port

        async def child():
            await self.l.play_sound(sound)
        kernel.run(child)

        self.l.send_message.ask_called_once()
        args, kwargs = self.l.send_message.call_args
        assert args[1] == self.write.get_bytes(port, 1, sound.value)

    @given( port = st.integers(0,255)
    )
    def test_activate_updates(self, port):
        self.l.port = port
        async def child():
            await self.l.activate_updates()
        kernel.run(child)

class TestMotor:

    def setup(self):
        #self.m = TrainMotor(name='motor')
        #self.m.send_message = Mock(side_effect=coroutine(lambda x,y: "the awaitable should return this"))
        self.write = DirectWrite()

    def _create_motor(self, cls):
        self.m = cls(name='motor')
        self.m.send_message = Mock(side_effect=coroutine(lambda x,y: "the awaitable should return this"))

    @given( speed = st.integers(-100,100),
            port = st.integers(0,255),
            cls = st.sampled_from([TrainMotor, DuploTrainMotor, WedoMotor, 
                        ExternalMotor, InternalMotor])
    )
    def test_set_speed(self, cls, port, speed):
        self._create_motor(cls)
        self.m.port = port

        async def child():
            await self.m.set_speed(speed)
        kernel.run(child)

        self.m.send_message.ask_called_once()
        args, kwargs = self.m.send_message.call_args
        assert args[1] == self.write.get_bytes(port, 0, self.m._convert_speed_to_val(speed))

    @given( speed = st.integers(-100,100),
            port = st.integers(0,255),
            cls = st.sampled_from([TrainMotor, DuploTrainMotor, WedoMotor, 
                        ExternalMotor, InternalMotor])
    )
    def test_ramp_speed(self, cls, port, speed):
        self._create_motor(cls)
        self.m.port = port

        async def child():
            await self.m.ramp_speed(speed, 200)
            await self.m.ramp_in_progress_task.join()
        async def main():
            t = await spawn(child())
            await t.join()
            assert self.m.speed == speed
        kernel.run(main)

    @given( speed = st.sampled_from([-50,0,100]),
            port = st.integers(0,255),
            cls = st.sampled_from([TrainMotor, DuploTrainMotor, WedoMotor, 
                        ExternalMotor, InternalMotor])
    )
    def test_ramp_cancel_speed(self, cls, port, speed):
        self._create_motor(cls)
        self.m.port = port

        async def child():
            await self.m.ramp_speed(speed, 2000)
            await sleep(0.1)
            await self.m.set_speed(speed+10)

        async def main():
            t = await spawn(child())
            await t.join()
            assert self.m.speed == speed+10
        kernel.run(main)

    @given( pos = st.integers(-2147483648, 2147483647),
            port = st.integers(0,255),
            cls = st.sampled_from([ExternalMotor, InternalMotor])
    )
    def test_set_pos(self, cls, port, pos):
        self._create_motor(cls)
        self.m.port = port
        speed = 50
        max_power = 50

        async def child():
            await self.m.set_pos(pos, speed, max_power)

        async def main():
            t = await spawn(child())
            await t.join()
        kernel.run(main)

        args, kwargs = self.m.send_message.call_args
        assert args[1] == self.write.get_bytes_for_set_pos(port, pos, self.m._convert_speed_to_val(speed), max_power)

    @given( angle = st.integers(0, 2147483647),
            speed = st.integers(-100,100),
            port = st.integers(0,255),
            cls = st.sampled_from([ExternalMotor, InternalMotor])
    )
    def test_rotate(self, cls, port, angle, speed):
        self._create_motor(cls)
        self.m.port = port
        max_power = 50

        async def child():
            await self.m.rotate(angle, speed, max_power)

        async def main():
            t = await spawn(child())
            await t.join()
        kernel.run(main)

        args, kwargs = self.m.send_message.call_args
        assert args[1] == self.write.get_bytes_for_rotate(port, angle, self.m._convert_speed_to_val(speed), max_power)

    def test_port(self):
        t = InternalMotor('motor', port=InternalMotor.Port.A)

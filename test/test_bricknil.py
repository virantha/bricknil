import pytest
import os, sys
import logging
from asyncio import coroutine

import smtplib
from mock import Mock
from mock import patch, call
from mock import MagicMock
from mock import PropertyMock

sys.modules['bleak'] = MagicMock()
from  bricknil.process import Process
from bricknil.sensor import TrainMotor

class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


class Testbricknil:

    def setup(self):
        self.p = Process('test')

    def test_name(self):
        assert self.p.name == 'test'

    def test_increment(self):
        for i in range(10):
            p2 = Process('test2')
            assert self.p.id == p2.id-(i+1)
        assert p2.__str__() == 'test2.11'
        assert p2.__repr__() == 'Process("test2")'

    def test_messages(self):
        self.p.message('hello')
        self.p.message_info('hello')
        self.p.message_debug('hello')
        self.p.message_error('hello')

    @pytest.mark.curio
    #@patch('test_bricknil.TrainMotor.set_output', new_callable=AsyncMock)
    async def test_motor(self):
        m = TrainMotor('motor')
        m.set_output = Mock(side_effect=coroutine(lambda x,y :'the awaitable should return this'))
        await m.set_speed(10)
        assert m.set_output.call_args == call(0, 10)


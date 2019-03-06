import pytest
import os
import logging

import smtplib
from mock import Mock
from mock import patch, call
from mock import MagicMock
from mock import PropertyMock

from  bricknil.process import Process

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


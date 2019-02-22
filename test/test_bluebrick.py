import pytest
import os
import logging

import smtplib
from mock import Mock
from mock import patch, call
from mock import MagicMock
from mock import PropertyMock

from  bluebrick.process import Process

class Testbluebrick:

    def setup(self):
        self.p = Process('test')

    def test_name(self):
        assert self.p.name == 'test'

    def test_increment(self):
        for i in range(10):
            p2 = Process('test2')
            assert self.p.id == p2.id-(i+1)

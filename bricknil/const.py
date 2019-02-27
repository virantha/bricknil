"""Useful constants for BlueBrick
"""
from enum import Enum
USE_BLEAK=True
class Color(Enum):
    """11 colors"""
    black = 0 
    pink = 1
    purple = 2
    blue = 3
    light_blue = 4
    cyan = 5
    green = 6
    yellow = 7
    orange = 8
    red = 9
    white = 10

DEVICES = {     0x0001:   'Motor',
                0x0002:   'System Train Motor',
                0x0005:   'Button',
                0x0014:   'Voltage',
                0x0015:   'Current',
                0x0016:   'Piezo Tone (Sound)',
                0x0017:   'RGB Light',
                0x0022:   'External Tilt Sensor',
                0x0023:   'Motion Sensor',
                0x0025:   'Vision Sensor',
                0x0026:   'External Motor with Tacho',
                0x0027:   'Internal Motor with Tacho',
                0x0028:   'Internal Tilt',
                0x0037:   'Remote Button',
                0x0038:   'Remote Signal Level',
            }


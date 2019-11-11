# Copyright 2019 Virantha N. Ekanayake 
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Useful constants for BrickNil
"""
from enum import Enum
import platform

if platform.system() == "Darwin":
    USE_BLEAK = False
else:
    USE_BLEAK = True

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
    none = 255

DEVICES = {     0x0001:   'Motor',
                0x0002:   'System Train Motor',
                0x0005:   'Button',
                0x0008:   'Light',
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
                0x0029:   'Duplo Train Motor',
                0x002A:   'Duplo Train Speaker',
                0x002B:   'Duplo Train Color',
                0x002C:   'Duplo Train Speedometer',
                0x002E:   'Technic Control+ Large Motor',
                0x002F:   'Technic Control+ XL Motor',
                0x0036:   'Powered Up Hub IMU Gesture',
                0x0037:   'Remote Button',
                0x0038:   'Remote Signal Level',
                0x0039:   'Powered Up Hub IMU Accelerometer',
                0x003A:   'Powered Up Hub IMU Gyro',
                0x003B:   'Powered Up Hub IMU Position',
                0x003C:   'Powered Up Hub IMU Temperature',
            }


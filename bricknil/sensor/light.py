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
"""All LED/light output devices"""

from curio import sleep, current_task, spawn  # Needed for motor speed ramp

from enum import Enum
from struct import pack

from ..const import Color
from .peripheral import Peripheral

class LED(Peripheral):
    """ Changes the LED color on the Hubs::

            @attach(LED, name='hub_led')

            self.hub_led.set_output(Color.red)
    """
    _sensor_id = 0x0017

    async def set_color(self, color: Color):
        """ Converts a Color enumeration to a color value"""

        # For now, only support preset colors
        assert isinstance(color, Color)
        col = color.value
        assert col < 11
        mode = 0
        await self.set_output(mode, col)


class Light(Peripheral):
    """
        Connects to the external light.

        Example::

             @attach(Light, name='light')

        And then within the run body, use::

            await self.light.set_brightness(brightness)
    """
    _sensor_id = 0x0008

    async def set_brightness(self, brightness: int):
        """Sets the brightness of the light.

        Args:
            brightness (int) : A value between -100 and 100 where 0 is off and
                -100 or 100 are both maximum brightness.
        """
        mode = 0
        brightness, = pack('b', int(brightness))
        await self.set_output(mode, brightness)


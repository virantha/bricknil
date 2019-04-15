
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
"""All sound related output devices
"""
from curio import sleep, current_task, spawn  # Needed for motor speed ramp

from enum import Enum, IntEnum
from struct import pack

from .peripheral import Peripheral

class DuploSpeaker(Peripheral):
    """Plays one of five preset sounds through the Duplo built-in speaker

       See :class:`sounds` for the list.

       Examples::

            @attach(DuploSpeaker, name='speaker')
            ...
            await self.speaker.play_sound(DuploSpeaker.sounds.brake)
           
       Notes:
            Uses Mode 1 to play the presets

    """
    _sensor_id = 0x002A
    sounds = Enum('sounds', { 'brake': 3,
                              'station': 5,
                              'water': 7,
                              'horn': 9,
                              'steam': 10,
                              })

    async def activate_updates(self):
        """For some reason, even though the speaker is an output device
           we need to send a Port Input Format Setup command (0x41) to enable
           notifications.  Otherwise, none of the sound output commands will play.  This function
           is called automatically after this sensor is attached.
        """
        mode = 1
        b = [0x00, 0x41, self.port, mode, 0x01, 0x00, 0x00, 0x00, 0x01]
        await self.send_message('Activate DUPLO Speaker: port {self.port}', b)

    async def play_sound(self, sound):
        assert isinstance(sound, self.sounds), 'Can only play sounds that are enums (DuploSpeaker.sounds.brake, etc)'
        mode = 1
        self.message_info(f'Playing sound {sound.name}:{sound.value}')
        await self.set_output(mode, sound.value)

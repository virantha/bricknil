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

"""Actual sensor and motor peripheral definitions from Boost and PoweredUp
"""
from curio import sleep, current_task, spawn  # Needed for motor speed ramp

from enum import Enum, IntEnum
from struct import pack

from ..const import Color
from .peripheral import Peripheral

class VisionSensor(Peripheral):
    """ Access the Boost Vision/Distance Sensor

        Only the sensing capabilities of this sensor is supported right now.

        - *sense_color*: Returns one of the 10 predefined colors
        - *sense_distance*: Distance from 0-7 in roughly inches
        - *sense_count*: Running count of waving your hand/item over the sensor (32-bit)
        - *sense_reflectivity*: Under distances of one inch, the inverse of the distance
        - *sense_ambient*: Distance under one inch (so inverse of the preceeding)
        - *sense_rgb*: R, G, B values (3 sets of uint16)

        Any combination of sense_color, sense_distance, sense_count, sense_reflectivity, 
        and sense_rgb is supported.

        Examples::

            # Basic distance sensor
            @attach(VisionSensor, name='vision', capabilities=['sense_color'])
            # Or use the capability Enum
            @attach(VisionSensor, name='vision', capabilities=[VisionSensor.capability.sense_color])

            # Distance and color sensor
            @attach(VisionSensor, name='vision', capabilities=['sense_color', 'sense_distance'])

            # Distance and rgb sensor with different thresholds to trigger updates
            @attach(VisionSensor, name='vision', capabilities=[('sense_color', 1), ('sense_rgb', 5)])

        The values returned by the sensor will always be available in the instance variable
        `self.value`.  For example, when the `sense_color` and `sense_rgb` capabilities are 
        enabled, the following values will be stored and updated::

            self.value = { VisionSensor.capability.sense_color:  uint8,
                           VisionSensor.capability.sense_rgb: 
                                            [ uint16, uint16, uint16 ]
                         }

        Notes:
            The actual modes supported by the sensor are as follows:

            -  0 = color (0-10)
            -  1 = IR proximity (0-7)
            -  2 = count (32-bit int)
            -  3 = Reflt   (inverse of distance when closer than 1")
            -  4 = Amb  (distance when closer than 1")
            -  5 = COL (output) ?
            -  6 = RGB I
            -  7 = IR tx (output) ?
            -  8 = combined:  Color byte, Distance byte, 0xFF, Reflected light

    """

    _sensor_id = 0x0025
    capability = Enum("capability", 
                      [('sense_color', 0),
                       ('sense_distance', 1),
                       ('sense_count', 2),
                       ('sense_reflectivity', 3),
                       ('sense_ambient', 4),
                       ('sense_rgb', 6),
                       ])

    datasets = { capability.sense_color: (1, 1),
                 capability.sense_distance: (1, 1),
                 capability.sense_count: (1, 4),  # 4-bytes (32-bit)
                 capability.sense_reflectivity: (1, 1),
                 capability.sense_ambient: (1, 1),
                 capability.sense_rgb: (3, 2)   # 3 16-bit values
                }

    allowed_combo = [ capability.sense_color,
                      capability.sense_distance,
                      capability.sense_count,
                      capability.sense_reflectivity,
                      capability.sense_rgb,
                    ]

class InternalTiltSensor(Peripheral):
    """
        Access the internal tilt sensor in the Boost Move Hub.
        
        The various modes are:

        - **sense_angle** - X, Y angles.  Both are 0 if hub is lying flat with button up
        - **sense_tilt** - value from 0-9 if hub is tilted around any of its axis. Seems to be
          a rough mesaure of how much the hub is tilted away from lying flat.
          There is no update for just a translation along an axis
        - **sense_orientation** - returns one of the nine orientations below (0-9)
            - `InternalTiltSensor.orientation`.up = flat with button on top
            - `InternalTiltSensor.orientation`.right - standing up on side closest to button
            - `InternalTiltSensor.orientation`.left - standing up on side furthest from button
            - `InternalTiltSensor.orientation`.far_side - on long face facing away
            - `InternalTiltSensor.orientation`.near_side -  on long face facing you
            - `InternalTiltSensor.orientation`.down - upside down
        - **sense_impact** - 32-bit count of impacts to sensor
        - **sense_acceleration_3_axis** - 3 bytes of raw accelerometer data.

        Any combination of the above modes are allowed.

        Examples::

            # Basic tilt sensor
            @attach(InternalTiltSensor, name='tilt', capabilities=['sense_tilt'])
            # Or use the capability Enum
            @attach(InternalTiltSensor, name='tilt', capabilities=[InternalTiltSensor.sense_tilt])

            # Tilt and orientation sensor
            @attach(InternalTiltSensor, name='tilt', capabilities=['sense_tilt, sense_orientation'])

        The values returned by the sensor will always be available in the
        instance variable `self.value`.  For example, when the `sense_angle`
        and `sense_orientation` capabilities are enabled, the following values
        will be stored and updated::

            self.value = { InternalTiltSensor.capability.sense_angle:  [uint8, uint8],
                           InternalTiltSensor.capability.sense_orientation: 
                                            Enum(InternalTiltSensor.orientation)
                         }
    """
    _sensor_id = 0x0028
    capability = Enum("capability", 
                      [('sense_angle', 0),
                       ('sense_tilt', 1),
                       ('sense_orientation', 2),
                       ('sense_impact', 3),
                       ('sense_acceleration_3_axis', 4),
                       ])

    datasets = { capability.sense_angle: (2, 1),
                 capability.sense_tilt: (1, 1),
                 capability.sense_orientation: (1, 1),  
                 capability.sense_impact: (1, 4),
                 capability.sense_acceleration_3_axis: (3, 1),
                }

    allowed_combo = [ capability.sense_angle,
                      capability.sense_tilt,
                      capability.sense_orientation,
                      capability.sense_impact,
                      capability.sense_acceleration_3_axis,
                    ]

    orientation = Enum('orientation', 
                        {   'up': 0,
                            'right': 1, 
                            'left': 2, 
                            'far_side':3,
                            'near_side':4,
                            'down':5,
                        })


    async def update_value(self, msg_bytes):
        """If sense_orientation, then substitute the `IntenalTiltSensor.orientation`
           enumeration value into the self.value dict.  Otherwise, don't do anything
           special to the self.value dict.
        """
        await super().update_value(msg_bytes)
        so = self.capability.sense_orientation
        if so in self.value:
            self.value[so] = self.orientation(self.value[so])



class ExternalMotionSensor(Peripheral):
    """Access the external motion sensor (IR) provided in the Wedo sets

       Measures distance to object, or if an object is moving (distance varying). 

       - **sense_distance** - distance in inches from 0-10
       - **sense_count**  - Increments every time it detects motion (32-bit value)

       These are mutually exclusive (non-combinable)

       Examples::

            # Distance measurement
            @attach(ExternalMotionSensor, name='motion_sensor', capabilities=['sense_distance'])


            # Motion detection
            @attach(ExternalMotionSensor, name='motion_sensor', capabilities=['sense_count'])
    """
    _sensor_id = 0x0023
    capability = Enum("capability", 
                      [('sense_distance', 0),
                       ('sense_count', 1),
                       ])

    datasets = { capability.sense_distance: (1, 1),  
                 capability.sense_count: (1, 4),
                }
    allowed_combo = [ ]

class ExternalTiltSensor(Peripheral):
    """Access the External tilt sensor provided in the Wedo sets

       Three modes are supported (non-combinable):

       - **sense_angle** - X (around long axis), Y (around short axis) angles.  -45 to 45 degrees
       - **sense_orientation** - returns one of the orientations below (wrt looking at the sensor from the side opposite the wiring harness)
            - `ExternalTiltSensor.orientation`.up = flat with studs on top
            - `ExternalTiltSensor.orientation`.right = studs facing rigth
            - `ExternalTiltSensor.orientation`.left = studs facing left
            - `ExternalTiltSensor.orientation`.far_side = studs facing away from you
            - `ExternalTiltSensor.orientation`.near_side = studs facing towards you
       - **sense_impact** - Keeps a count of impacts, but sends three bytes (direction of hit?)

       These are mutually exclusive (non-combinable).

    """
    _sensor_id = 0x0022
    capability = Enum("capability", 
                      [('sense_angle', 0),
                       ('sense_orientation', 1),
                       ('sense_impact', 2),
                       ])

    datasets = { capability.sense_angle: (2, 1),  
                 capability.sense_orientation: (1, 1),
                 capability.sense_impact: (3, 1),
                }
    allowed_combo = [ ]

    orientation = Enum('orientation', 
                        {   'up': 0,
                            'right': 7, 
                            'left': 5, 
                            'far_side':3,
                            'near_side':9,
                        })


    async def update_value(self, msg_bytes):
        """If angle, convert the bytes being returned to twos complement ints
           If orientation, then convert to the `orientation` enumeration.

        """
        await super().update_value(msg_bytes)
        # No combinations possible, so only one capability with len(self.capabilities[])==1
        if self.capabilities[0] == self.capability.sense_angle:
            sa = self.capability.sense_angle
            sx, sy = self.value[sa]
            if sx & 128:  # negative sign bit
                sx = -(256-sx)
            if sy & 128:
                sy = -(256-sy)
            self.value[sa] = [sx, sy]
        elif self.capabilities[0] == self.capability.sense_orientation:
            so = self.capability.sense_orientation
            self.value[so] = self.orientation(self.value[so])




class RemoteButtons(Peripheral):
    """Represents one set of '+', '-', 'red' buttons on the PoweredHub Remote

       Each remote has two sets of buttons, on the left and right side.  Pick the one
       your want to attach to by using the port argument with either Port.L or Port.R.

       There are actually a few different modes that the hardware supports, but we are
       only going to use one of them called 'KEYSD' (see the notes in the documentation on the
       raw values reported by the hub).  This mode makes the remote send three values back
       in a list.  To access each button state, there are three helper methods provided 
       (see below)

       Examples::

            # Basic connection to the left buttons
            @attach(RemoteButtons, name='left_buttons', port=RemoteButtons.Port.L)

            # Getting values back in the handler
            async def left_buttons_change(self):

                is_plus_pressed = self.left_buttons.plus_pressed()
                is_minus_pressed = self.left_buttons.minus_pressed()
                is_red_pressed = self.left_buttons.red_pressed()

    """

    _sensor_id = 0x0037
    Port = Enum('Port', 'L R', start=0)
    Button = IntEnum('Button', 'PLUS RED MINUS', start=0)
    """The button index in the value list returned by the sensor"""

    capability = Enum('capability', {'sense_press':4},)

    datasets = { capability.sense_press: (3,1) }
    allowed_combo = []

    def __init__(self, name, port=None, capabilities=[]):
        """Maps the port names `L`, `R`"""
        if port:
            port = port.value
        super().__init__(name, port, capabilities)

    def plus_pressed(self):
        """Return whether `value` reflects that the PLUS button is pressed"""
        button_list = self.value[self.capability.sense_press]
        return button_list[self.Button.PLUS] == 1
    def minus_pressed(self):
        """Return whether `value` reflects that the MINUS button is pressed"""
        button_list = self.value[self.capability.sense_press]
        return button_list[self.Button.MINUS] == 1
    def red_pressed(self):
        """Return whether `value` reflects that the RED button is pressed"""
        button_list = self.value[self.capability.sense_press]
        return button_list[self.Button.RED] == 1

class Button(Peripheral):
    """ Register to be notified of button presses on the Hub (Boost or PoweredUp)

        This is actually a slight hack, since the Hub button is not a peripheral that is 
        attached like other sensors in the Lego protocol.  Instead, the buttons are accessed
        through Hub property messages.  We abstract away these special messages to make the
        button appear to be like any other peripheral sensor.

        Examples::

            @attach(Button, name='hub_btn')

        Notes:
            Since there is no attach I/O message from the hub to trigger the
            :func:`activate_updates` method, we instead insert a fake
            "attaach" message from this fake sensor on port 255 in the
            `BLEventQ.get_messages` method that is used to register for updates
            from a given sensor.

    """
    _sensor_id = 0x0005
    """Piggy back the hub button off the normal peripheral button id 0x0005.
       Might need to change this in the future"""

    capability = Enum('capability', {'sense_press':0})

    datasets = { capability.sense_press: (1,1)
               }
    allowed_combo = [capability.sense_press]

    def __init__(self, name, port=None, capabilities=[]):
        """Call super-class with port set to 255 """
        super().__init__(name, 255, capabilities)

    async def activate_updates(self):
        """Use a special Hub Properties button message updates activation message"""
        self.value = {}
        for cap in self.capabilities:
            self.value[cap] = [None]*self.datasets[cap][0]

        b = [0x00, 0x01, 0x02, 0x02]  # Button reports from "Hub Properties Message Type"
        await self.send_message(f'Activate button reports: port {self.port}', b) 


class DuploVisionSensor(Peripheral):
    """ Access the Duplo Vision/Distance Sensor

        - *sense_color*: Returns one of the 10 predefined colors
        - *sense_ctag*: Returns one of the 10 predefined tags
        - *sense_reflectivity*: Under distances of one inch, the inverse of the distance
        - *sense_rgb*: R, G, B values (3 sets of uint16)

        Any combination of sense_color, sense_ctag, sense_reflectivity, 
        and sense_rgb is supported.

        Examples::

            # Basic color sensor
            @attach(DuploVisionSensor, name='vision', capabilities=['sense_color'])
            # Or use the capability Enum
            @attach(DuploVisionSensor, name='vision', capabilities=[DuploVisionSensor.capability.sense_color])

            # Ctag and reflectivity sensor
            @attach(DuploVisionSensor, name='vision', capabilities=['sense_ctag', 'sense_reflectivity'])

            # Distance and rgb sensor with different thresholds to trigger updates
            @attach(DuploVisionSensor, name='vision', capabilities=[('sense_color', 1), ('sense_rgb', 5)])

        The values returned by the sensor will always be available in the instance variable
        `self.value`.  For example, when the `sense_color` and `sense_rgb` capabilities are 
        enabled, the following values will be stored and updated::

            self.value = { DuploVisionSensor.capability.sense_color:  uint8,
                           DuploVisionSensor.capability.sense_rgb: 
                                            [ uint16, uint16, uint16 ]
                         }

        Notes:
            The actual modes supported by the sensor are as follows:

            -  0 = color (0-10)
            -  1 = ctag (32-bit int)
            -  2 = Reflt   (inverse of distance when closer than 1")
            -  3 = RGB I
    """
    _sensor_id = 0x002B
    capability = Enum("capability", 
                      [('sense_color', 0),
                       ('sense_ctag', 1),
                       ('sense_reflectivity', 2),
                       ('sense_rgb', 3),
                       ])

    datasets = { capability.sense_color: (1, 1),
                 capability.sense_ctag: (1, 1),  # 4-bytes (32-bit)
                 capability.sense_reflectivity: (1, 1),
                 capability.sense_rgb: (3, 2)   # 3 16-bit values
                }

    allowed_combo = [ capability.sense_color,
                      capability.sense_ctag,
                      capability.sense_reflectivity,
                      capability.sense_rgb,
                    ]

class VoltageSensor(Peripheral):
    """Voltage sensor

       Returns the raw mV value (0-3893) which probably needs to be scaled to 0-9600.

       It contains two capabilities, although they both appear to do the same thing:
       * sense_l
       * sense_s

       Examples::

            @attach(VoltageSensor, name='volts', capabilities=['sense_l'])

    """
    _sensor_id = 0x14

    capability = Enum("capability", {'sense_s': 0, 'sense_l': 1})
    datasets = {capability.sense_s: (1, 2),   # 2-bytes (16-bit)
                capability.sense_l: (1, 2), 
               }
    allowed_combo = [ ]

class CurrentSensor(Peripheral):
    """Voltage sensor

       Returns the raw mA value (0-4095) which probably needs to be scaled to 0-2444.

       It contains two capabilities, although they both appear to do the same thing:
       * sense_l
       * sense_s

       Examples::

            @attach(CurrentSensor, name='cur', capabilities=['sense_l'])

    """
    _sensor_id = 0x15

    capability = Enum("capability", {'sense_s': 0, 'sense_l': 1})
    datasets = {capability.sense_s: (1, 2),   # 2-bytes (16-bit)
                capability.sense_l: (1, 2), 
               }
    allowed_combo = [ ]

class DuploSpeedSensor(Peripheral):
    """Speedometer on Duplo train base that measures front wheel speed.

       This can measure the following values:

       - *sense_speed*: Returns the speed of the front wheels
       - *sense_count*: Keeps count of the number of revolutions the front wheels have spun

       Either or both can be enabled for measurement. 

       Examples::

            # Report speed changes
            @attach(DuploSpeedSensor, name='speed_sensor', capabilities=['sense_speed'])

            # Report all
            @attach(DuploSpeedSensor, name='speed_sensor', capabilities=['sense_speed', 'sense_count'])

       The values returned by the sensor will be in `self.value`.  For the first example, get the
       current speed by::

            speed = self.speed_sensor.value
        
       For the second example, the two values will be in a dict::

            speed = self.speed_sensor.value[DuploSpeedSensor.sense_speed]
            revs  = self.speed_sensor.value[DuploSpeedSensor.sense_count]

    """
    _sensor_id = 0x002C
    capability = Enum("capability", 
                      [('sense_speed', 0),
                       ('sense_count', 1),
                       ])

    datasets = { capability.sense_speed: Peripheral.Dataset(n=1, w=2, min=-300, max=300),
                 capability.sense_count: Peripheral.Dataset(n=1, w=4, min=-(1<<31), max=(1<<31-1)),
                }

    allowed_combo = [ capability.sense_speed,
                      capability.sense_count,
                    ]

    async def update_value(self, msg_bytes):
        """Hack to negate reverse speeds.  This should really be specified elsewehre
        """
        await super().update_value(msg_bytes)
        ss = self.capability.sense_speed
        sc = self.capability.sense_count
        if ss in self.value:
            if self.value[ss] & (1<<15):  # negative sign bit
                self.value[ss] = -((1<<16) - self.value[ss])
        if sc in self.value:
            if self.value[sc] & (1<<31):  # negative sign bit
                self.value[sc] = -((1<<32) - self.value[sc])


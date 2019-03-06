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
from .const import Color

from .peripheral import Peripheral


class InternalMotor(Peripheral):
    """ Access the internal motor(s) in the Boost Move Hub.

        Unlike the train motors, these motors have a built-in sensor for sending back
        the motor's current speed and position.  You don't need to use the sensors, and
        can treat this as strictly an output.

        .. graphviz::

            digraph {
               "from" -> "to"
            }


        Examples::

            # Basic connection to the motor on Port A
            @attach(InternalMotor, 'left_motor', port=InternalMotor.Port.A)

            # Basic connection to both motors at the same time (virtual I/O port).
            # Any speed command will cause both motors to rotate at the same speed
            @attach(InternalMotor, 'motors', port=InternalMotor.Port.AB)

            # Report back when motor speed changes. You must have a motors_change method defined 
            @attach(InternalMotor, 'motors', port=InternalMotor.Port.A, capabilities=['sense_speed'])
            # Only report back when speed change exceeds 5 units
            @attach(InternalMotor, 'motors', port=InternalMotor.Port.A, capabilities=[('sense_speed', 5)])

        See Also:
            :class:`TrainMotor` for connecting to a train motor

    """
    _sensor_id = 0x0027
    _DEFAULT_THRESHOLD=2
    """Set to 2 to avoid a lot of updates since the speed seems to oscillate a lot"""

    capability = Enum("capability", {"sense_speed":1, "sense_pos":2})

    Port = Enum('Port', 'A B AB', start=0)
    """Address either motor A or Motor B, or both AB at the same time"""

    # Dict of cap: (num_datasets, bytes_per_dataset)
    datasets = { capability.sense_speed: (1, 1),
                 capability.sense_pos: (1, 4),
                }
    """ Dict of (num_datasets, bytes_per_dataset).
       `sense_speed` (1-byte), and `sense_pos` (uint32)"""

    allowed_combo = [ capability.sense_speed,
                      capability.sense_pos,
                    ]

    def __init__(self, name, port=None, capabilities=[]):
        """Maps the port names `A`, `B`, `AB` to hard-coded port numbers"""
        if port:
            port_map = [55, 56, 57]
            port = port_map[port.value]
        self.speed = 0
        super().__init__(name, port, capabilities)
    
    async def set_speed(self, speed):
        """Sets the speed of the motor, and calls the :func:`bricknil.peripheral.Peripheral._convert_speed_to_val` method
           to do some sanity checking and bounding.

           Args:
               speed (int) : -100 to 100 (I believe this is a percentage)
        """
        self.speed = speed
        speed = self._convert_speed_to_val(speed)
        mode = 0
        await self.set_output(mode, speed)

    async def ramp_speed2(self, target_speed, ramp_time_ms):
        
        # Set acceleration profile
        delta_speed = target_speed - self.speed
        zero_100_ramp_time_ms = int(ramp_time_ms/delta_speed * 100.0) 
        zero_100_ramp_time_ms = zero_100_ramp_time_ms % 10000 # limit time to 10s

        hi = (zero_100_ramp_time_ms >> 8) & 255
        lo = zero_100_ramp_time_ms & 255

        profile = 1
        b = [0x00, 0x81, self.port, 0x01, 0x05, 10, 10, profile]
        await self.send_message(f'set accel profile {zero_100_ramp_time_ms} {hi} {lo} ', b)
        b = [0x00, 0x81, self.port, 0x01, 0x07, self._convert_speed_to_val(target_speed), 80, 1]
        await self.send_message('set speed', b)
        
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
            @attach(VisionSensor, 'vision', capabilities=['sense_color'])
            # Or use the capability Enum
            @attach(VisionSensor, 'vision', capabilities=[VisionSensor.capability.sense_color])

            # Distance and color sensor
            @attach(VisionSensor, 'vision', capabilities=['sense_color', 'sense_distance'])

            # Distance and rgb sensor with different thresholds to trigger updates
            @attach(VisionSensor, 'vision', capabilities=[('sense_color', 1), ('sense_rgb', 5)])

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
            @attach(InternalTiltSensor, 'tilt', capabilities=['sense_tilt'])
            # Or use the capability Enum
            @attach(InternalTiltSensor, 'tilt', capabilities=[InternalTiltSensor.sense_tilt])

            # Tilt and orientation sensor
            @attach(InternalTiltSensor, 'tilt', capabilities=['sense_tilt, sense_orientation'])

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


    def update_value(self, msg_bytes):
        """If sense_orientation, then substitute the `IntenalTiltSensor.orientation`
           enumeration value into the self.value dict.  Otherwise, don't do anything
           special to the self.value dict.
        """
        super().update_value(msg_bytes)
        so = self.capability.sense_orientation
        if so in self.value:
            self.value[so] = self.orientation(self.value[so])


class LED(Peripheral):
    """ Changes the LED color on the Hubs::

            @attach(LED, 'hub_led')

            self.hub_led.set_output(Color.red)

        Warnings:
            No support yet for the standalone LEDs that connect to the Hub ports.

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
        #b = [0x00, 0x81, self.port, 0x11, 0x51, mode, col ]
        #await self.message_info(f'set color to {color}')

class TrainMotor(Peripheral):
    """
        Connects to the train motors.

        TrainMotor has no sensing capabilities and only supports a single output mode that
        sets the speed.

        Examples::

            @attach(TrainMotor, 'train')

        And then within the run body, use::

            self.train.set_speed(speed)

        Attributes:
            speed (int) : Keep track of the current speed in order to ramp it

        See Also:
            `InternalMotor`
    """
    _sensor_id = 0x0002

    def __init__(self, name, port=None, capabilities=[]):
        """Initialize current speed to 0"""
        self.speed = 0
        self.ramp_in_progress_task = None
        super().__init__(name, port, capabilities)

    async def set_speed(self, speed):
        """ Validate and set the train speed

            If there is an in-progress ramp, and this command is not part of that ramp, 
            then cancel that in-progress ramp first, before issuing this set_speed command.

            Args:
                speed (int) : Range -100 to 100 where negative numbers are reverse.
                    Use 0 to put the motor into neutral.
                    255 will do a hard brake
        """

        await self._cancel_existing_differet_ramp()
        self.speed = speed
        self.message_info(f'Setting speed to {speed}')
        await self.set_output(0, self._convert_speed_to_val(speed))
        
    async def _cancel_existing_differet_ramp(self):
        """Cancel the existing speed ramp if it was from a different task

            Remember that speed ramps must be a task with daemon=True, so there is no 
            one awaiting its future.
        """
        # Check if there's a ramp task in progress
        if self.ramp_in_progress_task:
            # Check if it's this current task or not
            current = await current_task()
            if current != self.ramp_in_progress_task:
                # We're trying to set the speed 
                # outside a previously in-progress ramp, so cancel the previous ramp
                await self.ramp_in_progress_task.cancel()
                self.ramp_in_progress_task = None
                self.message_info(f'Canceling previous speed ramp in progress')




    async def ramp_speed(self, target_speed, ramp_time_ms):
        """Ramp the speed by 10 units in the time given

        """
        TIME_STEP_MS = 100 
        await self._cancel_existing_differet_ramp()

        # 500ms ramp time, 100ms per step
        # Therefore, number of steps = 500/100 = 5
        # Therefore speed_step = speed_diff/5
        number_of_steps = ramp_time_ms/TIME_STEP_MS
        speed_diff = target_speed - self.speed
        speed_step = speed_diff/number_of_steps
        start_speed = self.speed
        self.message(f'ramp_speed steps: {number_of_steps}, speed_diff: {speed_diff}, speed_step: {speed_step}')
        current_step = 0
        async def _ramp_speed():
            nonlocal current_step  # Since this is being assigned to, we need to mark it as coming from the enclosed scope
            while current_step < number_of_steps:
                next_speed = int(start_speed + current_step*speed_step)
                self.message(f'Setting next_speed: {next_speed}')
                current_step +=1 
                if current_step == number_of_steps: 
                    next_speed = target_speed
                await self.set_speed(next_speed)
                await sleep(TIME_STEP_MS/1000)
            self.ramp_in_progress_task = None

        self.message_info(f'Starting ramp of speed: {start_speed} -> {target_speed} ({ramp_time_ms/1000}s)')
        self.ramp_in_progress_task = await spawn(_ramp_speed, daemon = True)


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
            @attach(RemoteButtons, 'left_buttons', port=RemoteButtons.Port.L)

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

            @attach(Button, 'hub_btn')

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

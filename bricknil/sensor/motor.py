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
"""All motor related peripherals including base motor classes"""

from curio import sleep, current_task, spawn  # Needed for motor speed ramp

from enum import Enum
from struct import pack

from .peripheral import Peripheral

class Motor(Peripheral):
    """Utility class for common functions shared between Train Motors, Internal Motors, and External Motors

    """
    def __init__(self, name, port=None, capabilities=[]):
        self.speed = 0  # Initialize current speed to 0
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
                self.message_debug(f'Canceling previous speed ramp in progress')


    async def ramp_speed(self, target_speed, ramp_time_ms):
        """Ramp the speed by 10 units in the time given in milliseconds

        """
        TIME_STEP_MS = 100 
        await self._cancel_existing_differet_ramp()
        assert ramp_time_ms > 100, f'Ramp speed time must be greater than 100ms ({ramp_time_ms}ms used)'

        # 500ms ramp time, 100ms per step
        # Therefore, number of steps = 500/100 = 5
        # Therefore speed_step = speed_diff/5
        number_of_steps = ramp_time_ms/TIME_STEP_MS
        speed_diff = target_speed - self.speed
        speed_step = speed_diff/number_of_steps
        start_speed = self.speed
        self.message_debug(f'ramp_speed steps: {number_of_steps}, speed_diff: {speed_diff}, speed_step: {speed_step}')
        current_step = 0
        async def _ramp_speed():
            nonlocal current_step  # Since this is being assigned to, we need to mark it as coming from the enclosed scope
            while current_step < number_of_steps:
                next_speed = int(start_speed + current_step*speed_step)
                self.message_debug(f'Setting next_speed: {next_speed}')
                current_step +=1 
                if current_step == number_of_steps: 
                    next_speed = target_speed
                await self.set_speed(next_speed)
                await sleep(TIME_STEP_MS/1000)
            await self.set_speed(target_speed)
            self.ramp_in_progress_task = None

        self.message_debug(f'Starting ramp of speed: {start_speed} -> {target_speed} ({ramp_time_ms/1000}s)')
        self.ramp_in_progress_task = await spawn(_ramp_speed, daemon = True)

class TachoMotor(Motor):

    capability = Enum("capability", {"sense_speed":1, "sense_pos":2})

    datasets = { 
                 capability.sense_speed: (1, 1),
                 capability.sense_pos: (1, 4),
                }
    """ Dict of (num_datasets, bytes_per_dataset).
       `sense_speed` (1-byte), and `sense_pos` (uint32)"""

    allowed_combo = [ capability.sense_speed,
                      capability.sense_pos,
                    ]

    async def set_pos(self, pos, speed=50, max_power=50):
        """Set the absolute position of the motor

           Everytime the hub is powered up, the zero-angle reference will be reset to the
           motor's current position. When you issue this command, the motor will rotate to 
           the position given in degrees.  The sign of the pos tells you which direction to rotate:
           (1) a positive number will rotate clockwise as looking from end of shaft towards the motor,
           (2) a negative number will rotate counter-clockwise


           Examples::

              await self.motor.set_pos(90)   # Rotate 90 degrees clockwise (looking from end of shaft towards motor)
              await self.motor.set_pos(-90)  # Rotate conter-clockwise 90 degrees
              await self.motor.set_pos(720)  # Rotate two full circles clockwise

           Args:
              pos (int) : Absolute position in degrees.
              speed (int) : Absolute value from 0-100
              max_power (int):  Max percentage power that will be applied (0-100%)

           Notes: 

               Use command GotoAbsolutePosition
                * 0x00 = hub id
                * 0x81 = Port Output command
                * port
                * 0x11 = Upper nibble (0=buffer, 1=immediate execution), Lower nibble (0=No ack, 1=command feedback)
                * 0x0d = Subcommand
                * abs_pos (int32)
                * speed -100 - 100
                * max_power abs(0-100%)
                * endstate = 0 (float), 126 (hold), 127 (brake)
                * Use Accel profile = (bit 0 = acc profile, bit 1 = decc profile)
                *
        """
        abs_pos = list(pack('i', pos))
        speed = self._convert_speed_to_val(speed)

        b = [0x00, 0x81, self.port, 0x01, 0x0d] + abs_pos + [speed, max_power, 126, 3]
        await self.send_message(f'set pos {pos} with speed {speed}', b)


    async def rotate(self, degrees, speed, max_power=50):
        """Rotate the given number of degrees from current position, with direction given by sign of speed

           Examples::

              await self.motor.rotate(90, speed=50)   # Rotate 90 degrees clockwise (looking from end of shaft towards motor)
              await self.motor.set_pos(90, speed=-50)  # Rotate conter-clockwise 90 degrees
              await self.motor.set_pos(720, speed=50)  # Rotate two full circles clockwise

           Args:
              degrees (uint) : Relative number of degrees to rotate
              speed (int) : -100 to 100
              max_power (int):  Max percentage power that will be applied (0-100%)

           Notes: 

               Use command StartSpeedForDegrees
                * 0x00 = hub id
                * 0x81 = Port Output command
                * port
                * 0x11 = Upper nibble (0=buffer, 1=immediate execution), Lower nibble (0=No ack, 1=command feedback)
                * 0x0b = Subcommand
                * degrees (int32) 0..1000000
                * speed -100 - 100%
                * max_power abs(0-100%)
                * endstate = 0 (float), 126 (hold), 127 (brake)
                * Use Accel profile = (bit 0 = acc profile, bit 1 = decc profile)
                *
        """
        degrees = list(pack('i', degrees))
        speed = self._convert_speed_to_val(speed)

        b = [0x00, 0x81, self.port, 0x01, 0x0b] + degrees + [speed, max_power, 126, 3]
        await self.send_message(f'rotate {degrees} deg with speed {speed}', b)


    async def ramp_speed2(self, target_speed, ramp_time_ms): # pragma: no cover
        """Experimental function, not implemented yet DO NOT USE
        """
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


class InternalMotor(TachoMotor):
    """ Access the internal motor(s) in the Boost Move Hub.

        Unlike the train motors, these motors (as well as the stand-alone Boost
        motors :class:`ExternalMotor`) have a built-in sensor/tachometer for sending back
        the motor's current speed and position.  However, you don't need to use the
        sensors, and can treat this motor strictly as an output device.

        Examples::

            # Basic connection to the motor on Port A
            @attach(InternalMotor, name='left_motor', port=InternalMotor.Port.A)

            # Basic connection to both motors at the same time (virtual I/O port).
            # Any speed command will cause both motors to rotate at the same speed
            @attach(InternalMotor, name='motors', port=InternalMotor.Port.AB)

            # Report back when motor speed changes. You must have a motor_change method defined 
            @attach(InternalMotor, name='motor', port=InternalMotor.Port.A, capabilities=['sense_speed'])

            # Only report back when speed change exceeds 5 units
            @attach(InternalMotor, name='motors', port=InternalMotor.Port.A, capabilities=[('sense_speed', 5)])

        And within the run body you can control the motor output::
            await self.motor.set_speed(50)   # Setting the speed
            await self.motor.ramp_speed(80, 2000)  # Ramp speed to 80 over 2 seconds
            await self.motor.set_pos(90, speed=20) # Turn clockwise to 3 o'clock position
            await self.motor.rotate(60, speed=-50) # Turn 60 degrees counter-clockwise from current position

        See Also:
            * :class:`TrainMotor` for connecting to a train motor
            * :class:`ExternalMotor` for connecting to a Boost tacho motor

    """
    _sensor_id = 0x0027
    _DEFAULT_THRESHOLD=2
    """Set to 2 to avoid a lot of updates since the speed seems to oscillate a lot"""

    Port = Enum('Port', 'A B AB', start=0)
    """Address either motor A or Motor B, or both AB at the same time"""

    def __init__(self, name, port=None, capabilities=[]):
        """Maps the port names `A`, `B`, `AB` to hard-coded port numbers"""
        if port:
            port_map = [55, 56, 57]
            port = port_map[port.value]
        self.speed = 0
        super().__init__(name, port, capabilities)
    
        
class ExternalMotor(TachoMotor):
    """ Access the stand-alone Boost motors

        These are similar to the :class:`InternalMotor` with build-in tachometer and
        sensor for sending back the motor's current speed and position.  You
        don't need to use the sensors, and can treat this as strictly an
        output.

        Examples::

            # Basic connection to the motor on Port A
            @attach(ExternalMotor, name='motor')

            # Report back when motor speed changes. You must have a motor_change method defined 
            @attach(ExternalMotor, name='motor', capabilities=['sense_speed'])

            # Only report back when speed change exceeds 5 units, and position changes (degrees)
            @attach(ExternalMotor, name='motor', capabilities=[('sense_speed', 5), 'sense_pos'])

        And then within the run body::

            await self.motor.set_speed(50)   # Setting the speed
            await self.motor.ramp_speed(80, 2000)  # Ramp speed to 80 over 2 seconds
            await self.motor.set_pos(90, speed=20) # Turn clockwise to 3 o'clock position
            await self.motor.rotate(60, speed=-50) # Turn 60 degrees counter-clockwise from current position

        See Also:
            * :class:`TrainMotor` for connecting to a train motor
            * :class:`InternalMotor` for connecting to the Boost hub built-in motors

    """

    _sensor_id = 0x26


class CPlusLargeMotor(TachoMotor):
    """ Access the Technic Control Plus Large motors

        These are similar to the :class:`InternalMotor` with build-in tachometer and
        sensor for sending back the motor's current speed and position.  You
        don't need to use the sensors, and can treat this as strictly an
        output.

        Examples::

            # Basic connection to the motor on Port A
            @attach(CPlusLargeMotor, name='motor')

            # Report back when motor speed changes. You must have a motor_change method defined 
            @attach(CPlusLargeMotor, name='motor', capabilities=['sense_speed'])

            # Only report back when speed change exceeds 5 units, and position changes (degrees)
            @attach(CPlusLargeMotor, name='motor', capabilities=[('sense_speed', 5), 'sense_pos'])

        And then within the run body::

            await self.motor.set_speed(50)   # Setting the speed
            await self.motor.ramp_speed(80, 2000)  # Ramp speed to 80 over 2 seconds
            await self.motor.set_pos(90, speed=20) # Turn clockwise to 3 o'clock position
            await self.motor.rotate(60, speed=-50) # Turn 60 degrees counter-clockwise from current position

        See Also:
            * :class:`TrainMotor` for connecting to a train motor
            * :class:`InternalMotor` for connecting to the Boost hub built-in motors

    """

    _sensor_id = 0x2E


class CPlusXLMotor(TachoMotor):
    """ Access the Technic Control Plus XL motors

        These are similar to the :class:`InternalMotor` with build-in tachometer and
        sensor for sending back the motor's current speed and position.  You
        don't need to use the sensors, and can treat this as strictly an
        output.

        Examples::

            # Basic connection to the motor on Port A
            @attach(CPlusXLMotor, name='motor')

            # Report back when motor speed changes. You must have a motor_change method defined 
            @attach(CPlusXLMotor, name='motor', capabilities=['sense_speed'])

            # Only report back when speed change exceeds 5 units, and position changes (degrees)
            @attach(CPlusXLMotor, name='motor', capabilities=[('sense_speed', 5), 'sense_pos'])

        And then within the run body::

            await self.motor.set_speed(50)   # Setting the speed
            await self.motor.ramp_speed(80, 2000)  # Ramp speed to 80 over 2 seconds
            await self.motor.set_pos(90, speed=20) # Turn clockwise to 3 o'clock position
            await self.motor.rotate(60, speed=-50) # Turn 60 degrees counter-clockwise from current position

        See Also:
            * :class:`TrainMotor` for connecting to a train motor
            * :class:`InternalMotor` for connecting to the Boost hub built-in motors

    """

    _sensor_id = 0x2F


class TrainMotor(Motor):
    """
        Connects to the train motors.

        TrainMotor has no sensing capabilities and only supports a single output mode that
        sets the speed.

        Examples::

             @attach(TrainMotor, name='train')

        And then within the run body, use::

            await self.train.set_speed(speed)

        Attributes:
            speed (int) : Keep track of the current speed in order to ramp it

        See Also:
            :class:`InternalMotor`
    """
    _sensor_id = 0x0002

class WedoMotor(Motor):
    """
        Connects to the Wedo motors.

        WedoMotor has no sensing capabilities and only supports a single output mode that
        sets the speed.

        Examples::

             @attach(WedoMotor, name='motor')

        And then within the run body, use::

            await self.motor.set_speed(speed)

        Attributes:
            speed (int) : Keep track of the current speed in order to ramp it

        See Also:
            * :class:`InternalMotor`
            * :class:`TrainMotor`
    """
    _sensor_id = 0x0001

class DuploTrainMotor(Motor):
    """Train Motor on Duplo Trains

       Make sure that the train is sitting on the ground (the front wheels need to keep rotating) in 
       order to keep the train motor powered.  If you pick up the train, the motor will stop operating
       withina few seconds.

       Examples::

            @attach(DuploTrainMotor, name='motor')

       And then within the run body, use::

            await self.train.set_speed(speed)

       Attributes:
            speed (int): Keep track of the current speed in order to ramp it

       See Also:
            :class:`TrainMotor` for connecting to a PoweredUp train motor
    """
    _sensor_id = 0x0029


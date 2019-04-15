import logging, struct

from curio import sleep, Queue
from bricknil import attach, start
from bricknil.hub import BoostHub
from bricknil.sensor import LED, ExternalMotionSensor, ExternalTiltSensor, WedoMotor
from bricknil.process import Process
from bricknil.const import Color


tilt_cap = ExternalTiltSensor.capability.sense_impact
motion_cap = ExternalMotionSensor.capability.sense_distance

@attach(LED, name='led') 
@attach(ExternalTiltSensor, name='tilt_sensor', capabilities=[tilt_cap])
@attach(WedoMotor, name='motor')
#@attach(ExternalMotionSensor, name='motion_sensor', capabilities=[motion_cap])
#@@attach(ExternalMotor, name='motor')
class Robot(BoostHub):
    """ Rotate the external motor connected to a boost hub by degrees

        Demonstrate both the absolute positioning as well as relative rotation.
    """

    async def motion_sensor_change(self):
        new_value = self.motion_sensor.value[motion_cap]
        print(f'motion sensor changed {new_value}')

    async def tilt_sensor_change(self):
        new_value = self.tilt_sensor.value[tilt_cap]
        if tilt_cap == ExternalTiltSensor.capability.sense_angle:
            x_angle = new_value[0]
            y_angle = new_value[1]
            print(f'tilt sensor changed {x_angle}, {y_angle}')
        elif tilt_cap == ExternalTiltSensor.capability.sense_orientation:
            print(f'orientation {new_value}')
        elif tilt_cap == ExternalTiltSensor.capability.sense_impact:
            print(f'impacts {new_value}')

    async def run(self):
        self.message("Running")

        # Set the robot LED to green to show we're ready
        await self.led.set_color(Color.green)
        await sleep(2)


        while True:
            await self.led.set_color(Color.blue)
            await self.motor.ramp_speed(50, 2000)
            await sleep(3)
            await self.led.set_color(Color.white)
            await self.motor.ramp_speed(-50, 2000)
            await sleep(3)


async def system():
    robot = Robot('Vernie')
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start(system)

import logging

from curio import sleep, Queue
from bricknil import attach, start
from bricknil.hub import PoweredUpRemote, BoostHub
from bricknil.sensor import InternalMotor, RemoteButtons, LED, Button, ExternalMotor
from bricknil.process import Process
from bricknil.const import Color

from random import randint

@attach(LED, name='led') 
@attach(ExternalMotor, name='motor')
class Robot(BoostHub):
    """ Rotate the external motor connected to a boost hub by degrees

        Demonstrate both the absolute positioning as well as relative rotation.
    """

    async def run(self):
        self.message("Running")

        # Set the robot LED to green to show we're ready
        await self.led.set_color(Color.green)
        await sleep(2)

        # The powered on position becomes the 12 o'clock reference point

        for i in range(5):
            # Turn to 11 o'clock position
            await self.led.set_color(Color.blue)
            await self.motor.set_pos(-30, speed=50)
            await sleep(2)
            await self.led.set_color(Color.red)
            # Turn to 1 o'clock position
            await self.motor.set_pos(30, speed=30)
            await sleep(2)
            await self.led.set_color(Color.yellow)
            # Turn to 3 o'clock position
            await self.motor.set_pos(90, speed=20)
            await sleep(2)

            # Rotate a random amount of degrees from 1 to 180
            await self.led.set_color(Color.purple)
            await self.motor.rotate(randint(1,180), speed=10)
            await sleep(3)

            # Then reset to 12 o'clock position
            await self.led.set_color(Color.green)
            await self.motor.set_pos(0)
            await sleep(2)



async def system():
    robot = Robot('Vernie')
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    start(system)

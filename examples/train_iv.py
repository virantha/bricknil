import logging
from itertools import cycle
from curio import sleep
from bricknil import attach, start
from bricknil.hub import PoweredUpHub
from bricknil.sensor import TrainMotor, VisionSensor, Button, LED, VoltageSensor, CurrentSensor
from bricknil.const import Color

@attach(CurrentSensor, name='current', capabilities=[('sense_l', 2)])
@attach(TrainMotor, name='motor')
class Train(PoweredUpHub):

    async def voltage_change(self):
        mv = self.voltage.value
        self.message_info(f'train voltage {mv}')

    async def current_change(self):
        ma = self.current.value
        self.message_info(f'train current {ma}')

    async def run(self):
        self.message_info("Running")

        await self.motor.ramp_speed(50,3000)
        await sleep(60)

        for i in range(10,100,10):
            self.message_info(f'ramping speed {i}')
            await self.motor.ramp_speed(i, 900)  # Ramp to new speed in 0.9 seconds
            await sleep(3)
        for i in range(100,10,-10):
            self.message_info(f'ramping down speed {i}')
            await self.motor.ramp_speed(i, 900)  # Ramp to new speed in 0.9 seconds
            await sleep(3)


async def system():
    train = Train('My Train')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start(system)

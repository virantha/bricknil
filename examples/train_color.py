import logging
from itertools import cycle
from curio import sleep
from bricknil import attach, start
from bricknil.hub import PoweredUpHub
from bricknil.sensor import TrainMotor, VisionSensor, Button, LED
from bricknil.process import Process
from bricknil.const import Color
from random import randint

@attach(Button, name='train_btn', capabilities=['sense_press'])
@attach(LED, name='train_led')
@attach(VisionSensor, name='train_sensor', capabilities=['sense_color', 'sense_reflectivity'])
@attach(TrainMotor, name='motor')
class Train(PoweredUpHub):

    def __init__(self, name):
        self.go = False
        super().__init__(name)

    async def train_btn_change(self):
        self.message_info(f'train button push {self.train_btn.value}')
        btn = self.train_btn.value[Button.capability.sense_press]
        if btn == 1 and not self.go:
            # Pushed!
            self.go = True
        elif btn==1 and self.go:
            self.go = False


    async def train_sensor_change(self):
        #self.message_info(f'Train sensor value change {self.train_sensor.value}')
        refl = self.train_sensor.value[VisionSensor.capability.sense_reflectivity]
        if refl >18:
            self.message_info('Switch!')
        color = self.train_sensor.value[VisionSensor.capability.sense_color]
        c = Color(color)
        if c == Color.blue:
            self.message_info('Blue')
            self.slow = False
        elif c == Color.yellow:
            self.message_info('Yellow')
            self.slow = True


        #count = self.train_sensor.value[VisionSensor.capability.sense_count]
        #self.message_info(f'Count {count}')


    async def run(self):
        self.message_info("Running")
        self.motor_speed = 0
        self.go = False
        slow = 40
        fast = 70

        # Blink the color  from purple and yellow
        colors = cycle([Color.purple, Color.yellow])
        while not self.go:  # Wait until the hub button is pushed
            await self.train_led.set_color(next(colors))
            await sleep(1)

        colors = cycle([Color.green, Color.orange])
        # Ready to go, let's change the color to green!
        await self.motor.ramp_speed(fast, 2000)
        self.slow = False
        while self.go:
            #speed = randint(30,30)
            #await self.motor.ramp_speed(speed, 2000)
            await self.train_led.set_color(next(colors))
            if self.slow:
                await self.motor.ramp_speed(slow, 2000)
                await self.train_led.set_color(Color.red)
                while self.slow:
                    await sleep(1)
                await self.motor.ramp_speed(fast, 2000)
            await sleep(1)

async def system():
    train = Train('My Train')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start(system)

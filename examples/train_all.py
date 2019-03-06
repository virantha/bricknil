import logging
from itertools import cycle
from curio import sleep
from bricknil import attach, start
from bricknil.hub import PoweredUpHub
from bricknil.sensor import TrainMotor, VisionSensor, Button, LED
from bricknil.process import Process
from bricknil.const import Color

@attach(Button, name='train_btn', capabilities=['sense_press'])
@attach(LED, name='train_led')
@attach(VisionSensor, name='train_sensor', capabilities=['sense_count', 'sense_distance'])
@attach(TrainMotor, name='motor')
class Train(PoweredUpHub):

    async def train_btn_change(self):
        self.message_info(f'train button push {self.train_btn.value}')
        btn = self.train_btn.value[Button.capability.sense_press]
        if btn == 1:
            # Pushed!
            self.go = True


    async def train_sensor_change(self):
        self.message_info(f'Train sensor value change {self.train_sensor.value}')
        distance = self.train_sensor.value[VisionSensor.capability.sense_distance]
        count = self.train_sensor.value[VisionSensor.capability.sense_count]

        if count > 3:
            # Wave your hand more than three times in front of the sensor and the program ends
            self.keep_running = False

        # The closer your hand gets to the sensor, the faster the motor runs
        self.motor_speed = (10-distance)*10

        # Flag a change
        self.sensor_change = True

    async def run(self):
        self.message_info("Running")
        self.motor_speed = 0
        self.keep_running = True
        self.sensor_change = False
        self.go = False

        # Blink the color  from purple and yellow
        colors = cycle([Color.purple, Color.yellow])
        while not self.go:  # Wait until the hub button is pushed
            await self.train_led.set_color(next(colors))
            await sleep(1)

        colors = cycle([Color.green, Color.orange])
        # Ready to go, let's change the color to green!
        while self.keep_running:
            if self.sensor_change:
                await self.train_led.set_color(next(colors))
                await self.motor.ramp_speed(self.motor_speed, 900)  # Ramp to new speed in 0.9 seconds
                self.sensor_change = False
                await sleep(1)
                await self.train_led.set_color(next(colors))
            else:
                await sleep(1)

async def system():
    train = Train('My Train')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start(system)

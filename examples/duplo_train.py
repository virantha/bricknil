
from itertools import cycle
from curio import sleep
from bricknil import attach, start
from bricknil.hub import DuploTrainHub
from bricknil.sensor import DuploTrainMotor, DuploSpeedSensor, LED, DuploVisionSensor, DuploSpeaker, Button, VoltageSensor
from bricknil.const import Color
import logging

#@attach(DuploSpeaker, name='speaker')
@attach(DuploVisionSensor, name='vision_sensor', capabilities=[('sense_reflectivity', 5)])
@attach(LED, name='led')
@attach(DuploSpeedSensor, name='speed_sensor', capabilities=['sense_speed', 'sense_count'])
#@attach(VoltageSensor, name='voltage', capabilities=[('sense_l', 50)])
@attach(DuploTrainMotor, name='motor')
class Train(DuploTrainHub):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.go = False     # Only becomes true with hub button is pressed

    async def voltage_change(self):
        pass
    async def speed_sensor_change(self):
        speed = self.speed_sensor.value[DuploSpeedSensor.capability.sense_speed]
        if not self.go and speed > 0:
            self.go = True
            self.message_info('Movement detected: starting...')
        elif self.go:
            #count = self.speed_sensor.value[DuploSpeedSensor.capability.sense_count]
            #self.message_info(f'Speed sensor changed speed: {speed} count: {count}')
            self.message_info(f'Speed sensor changed speed: {speed}')

    async def vision_sensor_change(self):
        cap = DuploVisionSensor.capability
        #color = self.vision_sensor.value[cap.sense_color]
        #ctag  = self.vision_sensor.value[cap.sense_ctag]
        reflt  = self.vision_sensor.value[cap.sense_reflectivity]
        if self.go:
            #self.message_info(f'Vision sensor changed color: {color} ctag: {ctag} reflt: {reflt}')
            self.message_info(f'Vision sensor changed color: reflt: {reflt}')

    async def run(self):
        self.message_info("Running")

        colors = cycle([Color.red, Color.purple, Color.yellow, Color.blue, Color.white])

        snd = DuploSpeaker.sounds
        sounds = cycle([snd.brake, snd.station, snd.water, snd.horn, snd.steam])

        self.message_info('Please move the train to start the program')
        while not self.go:
            await self.led.set_color(next(colors))
            await sleep(0.3)

        for i in range(5):
            await self.led.set_color(next(colors))       # Cycle through the colors
            #await self.speaker.play_sound(next(sounds))  # cycle through the sounds
            tgt_speed = 20 + i*15                        # Keep increasing the speed
            await self.motor.ramp_speed(tgt_speed, 2000)
            self.message_info(f"Set speed to {i}")
            await sleep(3)

        self.message_info("Done")

async def system():
    hub = Train('train', False)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start(system)

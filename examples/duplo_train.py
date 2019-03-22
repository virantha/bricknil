
from itertools import cycle
from curio import sleep
from bricknil import attach, start
from bricknil.hub import DuploTrainHub
from bricknil.sensor import DuploTrainMotor, DuploSpeedSensor, LED, DuploVisionSensor, DuploSpeaker
from bricknil.const import Color
import logging

@attach(DuploSpeaker, name='speaker')
@attach(DuploVisionSensor, name='vision_sensor', capabilities=['sense_color', 'sense_ctag', 'sense_reflectivity'])
@attach(LED, name='led')
@attach(DuploSpeedSensor, name='speed_sensor', capabilities=['sense_speed', 'sense_count'])
@attach(DuploTrainMotor, name='motor')
class Robot(DuploTrainHub):

    async def speed_sensor_change(self):
        speed = self.speed_sensor.value[DuploSpeedSensor.capability.sense_speed]
        count = self.speed_sensor.value[DuploSpeedSensor.capability.sense_count]
        logging.info(f'Speed sensor changed speed: {speed} count: {count}')

    async def vision_sensor_change(self):
        cap = DuploVisionSensor.capability
        color = self.vision_sensor.value[cap.sense_color]
        ctag  = self.vision_sensor.value[cap.sense_ctag]
        reflt  = self.vision_sensor.value[cap.sense_reflectivity]
        logging.info(f'Vision sensor changed color: {color} ctag: {ctag} reflt: {reflt}')

    async def motor_change(self):
        pass
    async def tilt_sensor_change(self):
        pass

    async def run(self):
        self.message_info("Running")

        colors = cycle([Color.red, Color.purple, Color.yellow, Color.blue, Color.white])
        snd = DuploSpeaker.sounds
        sounds = cycle([snd.brake, snd.station, snd.water, snd.horn, snd.steam])
        for i in range(5):
            await self.led.set_color(next(colors))
            await self.speaker.play_sound(next(sounds))
            tgt_speed = 30 + i*15
            await self.motor.ramp_speed(tgt_speed, 2000)
            self.message_info(f"Set speed to {i}")
            await sleep(3)

        self.message_info("Done")

async def system():
    hub = Robot('robot')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start(system)

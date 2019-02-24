from itertools import cycle
from curio import sleep
from bricknil import attach, start
from bricknil.hub import PoweredUpHub
from bricknil.sensor import TrainMotor, VisionSensor, Button, LED, InternalTiltSensor, InternalMotor
from bricknil.process import Process
from bricknil.const import Color

@attach(Button, name='hub_btn', capabilities=['sense_press'])
@attach(LED, name='hub_led')
@attach(VisionSensor, name='vision_sensor', capabilities=['sense_count', 'sense_distance'])
@attach(TrainMotor, name='motor_l')
class Robot(PoweredUpHub):

    async def hub_btn_change(self):
        pass
    async def vision_sensor_change(self):
        pass
    async def motor_l_change(self):
        pass
    async def motor_r_change(self):
        pass
    async def tilt_sensor_change(self):
        pass

    async def run(self):
        self.message_info("Running")
        await sleep(10) # Give it enough time to gather data

async def system():
    hub = Robot('robot')

if __name__ == '__main__':
    Process.level = Process.MSG_LEVEL.DEBUG
    start(system)

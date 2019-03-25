from itertools import cycle
from curio import sleep
from bricknil import attach, start
from bricknil.hub import PoweredUpHub
from bricknil.sensor import TrainMotor, VisionSensor, Button, LED, InternalTiltSensor, InternalMotor
from bricknil.process import Process
from bricknil.const import Color
import logging

@attach(Button, name='hub_btn', capabilities=['sense_press'])
@attach(LED, name='hub_led')
#@attach(VisionSensor, name='vision_sensor', capabilities=['sense_count', 'sense_distance'])
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
        await sleep(20) # Give it enough time to gather data
        self.message_info("Done")

        self.message_info(self.port_info)

async def system():
    hub = Robot('robot', query_port_info=True, ble_id='05c5e50e-71e9-4dcf-871a-7e5b93b36d6a')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start(system)

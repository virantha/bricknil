from itertools import cycle
from curio import sleep
from bricknil import attach, start
from bricknil.hub import DuploTrainHub
from bricknil.sensor import DuploTrainMotor
from bricknil.process import Process
from bricknil.const import Color
import logging

@attach(DuploTrainMotor, name='motor')
class Robot(DuploTrainHub):

    async def hub_btn_change(self):
        pass
    async def vision_sensor_change(self):
        pass
    async def motor_change(self):
        pass
    async def tilt_sensor_change(self):
        pass

    async def run(self):
        self.message_info("Running")
        await sleep(20) # Give it enough time to gather data
        self.message_info("Done")

        self.message_info(self.port_info)

async def system():
    hub = Robot('robot', query_port_info=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    start(system)


from curio import sleep
from bluebrick import attach, start
from bluebrick.hub import PoweredUpHub
from bluebrick.sensor import TrainMotor, VisionSensor
from bluebrick.process import Process

@attach(TrainMotor, name='motor')
class Train(PoweredUpHub):

    async def run(self):
        self.message_info("Running")
        self.motor_speed = 0
        for i in range(2):
            await self.motor.ramp_speed(80,5000)
            await sleep(5)
            await self.motor.ramp_speed(0,1000) 
            await sleep(2)

async def system():
    train = Train('My train')

if __name__ == '__main__':
    Process.level = Process.MSG_LEVEL.INFO
    start(system)

from itertools import cycle
from curio import sleep
from bluebrick import attach, start
from bluebrick.hub import PoweredUpRemote
from bluebrick.sensor import TrainMotor, VisionSensor, Button, LED, InternalTiltSensor, InternalMotor, RemoteButtons
from bluebrick.process import Process
from bluebrick.const import Color

@attach(Button, name='hub_btn', capabilities=['sense_press'])
@attach(RemoteButtons, name='btn_r', capabilities=['sense_press'])
@attach(RemoteButtons, name='btn_l', capabilities=['sense_press'])
class Remote(PoweredUpRemote):

    async def hub_btn_change(self):
        self.message_info(f'Hub Btn change {self.hub_btn.value}')
    async def btn_r_change(self):
        self.message_info(f'Btn r change {self.btn_r.value}')
    async def btn_l_change(self):
        self.message_info(f'Btn l change {self.btn_l.value}')

    async def run(self):
        self.message_info("Running")
        await sleep(20) # Give it enough time to gather data

async def system():
    remote = Remote('remote')

if __name__ == '__main__':
    Process.level = Process.MSG_LEVEL.INFO
    start(system)

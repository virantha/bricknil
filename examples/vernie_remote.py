import logging

from curio import sleep, Queue
from bricknil import attach, start
from bricknil.hub import PoweredUpRemote, BoostHub
from bricknil.sensor import InternalMotor, RemoteButtons, LED, Button
from bricknil.process import Process
from bricknil.const import Color


@attach(LED, name='led') 
@attach(RemoteButtons, name='btns_right',  capabilities=['sense_press'])
@attach(RemoteButtons, name='btns_left',  capabilities=['sense_press'])
class Remote(PoweredUpRemote):

    async def btns_left_change(self):
        if self.btns_left.plus_pressed():
            await self.tell_robot.put('forward')
        elif self.btns_left.minus_pressed():
            await self.tell_robot.put('backward')
        else:
            await self.tell_robot.put('stop')

    async def btns_right_change(self):
        if self.btns_right.plus_pressed():
            await self.tell_robot.put('right')
        elif self.btns_right.minus_pressed():
            await self.tell_robot.put('left')
        else:
            await self.tell_robot.put('stop')

    async def run(self):
        self.message('Running')
        # Set the remote LED to green to show we're ready
        await self.led.set_color(Color.green)
        while True:
            await sleep(10)   # Keep the remote running

@attach(LED, name='led') 
@attach(InternalMotor, name='motor_right', port=InternalMotor.Port.B)
@attach(InternalMotor, name='motor_left', port=InternalMotor.Port.A)
class Robot(BoostHub):

    async def run(self):
        self.message("Running")
        speed = 30

        # Set the robot LED to green to show we're ready
        await self.led.set_color(Color.green)
        while True:
            msg = await self.listen_remote.get()
            await self.listen_remote.task_done()
            if msg=='forward':
                self.message('going forward')
                await self.motor_left.set_speed(speed)
                await self.motor_right.set_speed(speed)
            elif msg=='backward':
                self.message('going backward')
                await self.motor_left.set_speed(-speed)
                await self.motor_right.set_speed(-speed)
            elif msg=='stop':
                self.message('stop')
                await self.motor_left.set_speed(0)
                await self.motor_right.set_speed(0)
            elif msg=='left':
                self.message('left')
                await self.motor_left.set_speed(-speed)
                await self.motor_right.set_speed(speed)
            elif msg=='right':
                self.message('right')
                await self.motor_left.set_speed(speed)
                await self.motor_right.set_speed(-speed)


async def system():
    robot = Robot('Vernie')
    remote = Remote('remote')
    
    # Define a message passing queue from the remote to the robot
    remote.tell_robot = Queue()
    robot.listen_remote = remote.tell_robot

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start(system)

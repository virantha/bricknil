#!/usr/bin/env python3

import logging
from curio import sleep
from bricknil import attach, start
from bricknil.hub import CPlusHub
from bricknil.sensor.motor import CPlusXLMotor


@attach(CPlusXLMotor, name='front_drive', port=0)
@attach(CPlusXLMotor, name='rear_drive', port=1)
class Truck(CPlusHub):

    async def run(self):
        self.message_info("Running")
        await self.front_drive.set_speed(-100)
        await self.rear_drive.set_speed(-100)
        await sleep(20) # Give it enough time to gather data

async def system():
    hub = Truck('truck', True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    start(system)

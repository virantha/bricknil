import pprint, uuid
from curio import sleep

# Local imports
from hub import PoweredUpHub, BoostHub
from sensor import LED, VisionSensor, InternalTiltSensor, InternalMotor, TrainMotor, Button
from const import Color

import bricknil
from bricknil import attach


@attach(LED, name='hub_led')
@attach(TrainMotor, name='train_motor')
@attach(Button, name='hub_btn')
class Train(PoweredUpHub):

    async def hub_btn_change(self):
        self.message(f'hub button change detected to {self.hub_btn.value}')

    def __init__(self, name, queue):
        super().__init__(name, queue)
        self.ble_id = uuid.UUID('05c5e50e-71e9-4dcf-871a-7e5b93b36d6a')

    async def run(self):
        self.message("Running")
        await sleep(3)
        for i in range(4):
            await sleep(2)
            self.message(i)
            await self.train_motor.set_output(i*10+40)
            await self.hub_led.set_output(Color(i+4))
        #await self.set_speed(0)
        self.message("terminated")


@attach(InternalMotor, name='right_motor', port=InternalMotor.Port.B, capabilities=[])
@attach(InternalMotor, name='left_motor', port=InternalMotor.Port.A,  capabilities=['sense_speed'])
#@attach(InternalMotor, name='left_motor', port=InternalMotor.Port.A,  capabilities=[InternalMotor.capability.sense_speed])
#@attach(ColorSensor, name='vision_sensor', capabilities=[ColorSensor.capability.sense_color])
#@attach(VisionSensor, name='vision_sensor', capabilities=[('sense_rgb', 5), ])
@attach(InternalTiltSensor, name='tilt_sensor', capabilities=['sense_orientation'])
@attach(LED, name = 'led')
class Robot(BoostHub):

    #tilt_sensor: TiltSensor


    async def vision_sensor_change(self):
        self.message(f'sensor color change detected to {self.vision_sensor.value}')

    async def tilt_sensor_change(self):
        self.message(f'tilt change detected {self.tilt_sensor.value}')

    async def left_motor_change(self):
        self.message(f'internal_motor change detected {self.left_motor.value}')


    async def run(self):

        self.message("Running")

        await sleep(2)
        #pprint.pprint(self.port_info)
        #await self._get_port_info(2)
        #await self._get_port_info(58)
        #await self._set_combo(2, [0,1,2,3,6])
        #await self._set_combo(2, [2,3])
        await self.led.set_output(Color.green)
        for i in range(1):
            #await self.left_motor.set_speed(50)
            #await self.right_motor.set_speed(-50)
            await sleep(5)
            await self.led.set_output(Color.red)
            #await self.left_motor.set_speed(-50)
            #await self.right_motor.set_speed(0)
            await sleep(5)
            await self.led.set_output(Color.orange)
            self.message(i)
            #await self.set_hub_led_color(i+4)
        #awat self.set_speed(0)
        self.message("terminated")
        pprint.pprint(self.port_info)


async def system():

    robot = Robot('vernie')
    #train = Train('my train', ble_q.q)

if __name__=='__main__':
    bricknil.start(system)

import logging
from curio import sleep
from bricknil import attach, start
from bricknil.hub import PoweredUpHub
from bricknil.sensor import Light


@attach(Light, name='light')
class Train(PoweredUpHub):

    async def run(self):
        self.message_info("Running")
        self.keep_running = True
        brightness = 0
        delta = 10

        while self.keep_running:
            # change the brightness up and down between -100 and 100
            brightness += delta
            if brightness >= 100:
                delta = -10
            elif brightness <= -100:
                delta = 10
            self.message_info("Brightness: {}".format(brightness))
            await self.light.set_brightness(brightness)
            await sleep(1)


async def system():
    Train('My Train')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start(system)

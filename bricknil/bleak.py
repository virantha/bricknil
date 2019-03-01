"""Interface to the BLEAK library in Linux for BLE calls

"""
import curio, asyncio, threading, logging
from curio.bridge import AsyncioLoop

import bleak
from bleak import BleakClient

class Bleak:

    def __init__(self):
        # Need to start an event loop
        self.in_queue = curio.UniversalQueue()  # Incoming message queue
        self.out_queue = curio.UniversalQueue()  # Outgoing message queue

        self.devices = []
        #self.loop = threading.Thread(target=self.run, daemon=True)
        #self.loop.start()

    def run(self):
        #self.loop = asyncio.new_event_loop()
        #asyncio.set_event_loop(self.loop)
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.asyncio_loop())

    async def asyncio_loop(self):

        # Wait for messages on in_queue
        done = False
        while not done:
            msg = await self.in_queue.get()
            if isinstance(msg, tuple):
                msg, val = msg
            await self.in_queue.task_done()
            if msg == 'discover':
                print('Awaiting on bleak discover')
                devices = await bleak.discover(loop=self.loop)
                print('Done Awaiting on bleak discover')
                await self.out_queue.put(devices)
            elif msg == 'connect':
                device = BleakClient(address=val, loop=self.loop)
                self.devices.append(device)
                await device.connect()
                await self.out_queue.put(device)
            elif msg == 'tx':
                device, char_uuid, msg_bytes = val
                await device.write_gatt_char(char_uuid, msg_bytes)
            elif msg == 'notify':
                device, char_uuid, msg_handler = val
                await device.start_notify(char_uuid, msg_handler)
            elif msg =='quit':
                logging.info('quitting')
                for device in self.devices:
                    await device.disconnect()
                done = True
            else:
                print(f'Unknown message to Bleak: {msg}')



    

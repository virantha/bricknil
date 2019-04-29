# Copyright 2019 Virantha N. Ekanayake 
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Interface to the BLEAK library in Linux for BLE calls

"""
import curio, asyncio, threading, logging

import bleak
#from bleak import BleakClient

class Bleak:
    """Interface class between curio loop and asyncio loop running bleak
       
       This class is basically just a queue interface.  It has two queue, 
       one for incoming messages `in_queue` and one for outgoing messages `out_queue`.

       A loop running in asyncio's event_loop waits for messages on the `in_queue`.

       The `out_queue` is used to respond to "discover" and "connect" messages with the
       list of discovered devices and a connected device respectively.  All messages
       incoming from a device are relayed directly to a call back function, and does
       not go through either of these queues.


    """

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
                devices = await bleak.discover(timeout=1, loop=self.loop)
                print('Done Awaiting on bleak discover')
                await self.out_queue.put(devices)
            elif msg == 'connect':
                device = bleak.BleakClient(address=val, loop=self.loop)
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
                print("quitting")
                logging.info('quitting')
                for device in self.devices:
                    await device.disconnect()
                done = True
                print("quit")
            else:
                print(f'Unknown message to Bleak: {msg}')



    

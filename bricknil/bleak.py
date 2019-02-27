"""Interface to the BLEAK library in Linux for BLE calls

"""
import curio, asyncio, threading
from curio.bridge import AsyncioLoop

import bleak

class Bleak:

    def __init__(self):
        # Need to start an event loop
        self.in_queue = curio.UniversalQueue  # Incoming message queue
        self.out_queue = curio.UniversalQueue  # Outgoing message queue

        self.loop = AsyncioLoop()

    async def curio_connect(self):
        devices = await self.loop.run_until_complete(bleak.discover())

        return devices



    


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
"""Experimental socket updates of devices and hubs"""

import logging
import json
from curio import run, spawn,  sleep, Queue, tcp_server

logger = logging.getLogger(str(__name__))
#async def socket_server(web_out_queue, address):
    #sock = socket(AF_INET, SOCK_STREAM)
    #sock.setsockopt(SOL_SOCKET, SO_REUSEADDR,1)
    #sock.bind(address)
    #sock.listen(5)
    #print(f'Server listening at {address}')
    #async with sock:
        #while True:
            #client, addr = await sock.accept()
            #wc = WebClient(client, addr, web_out_queue)
            #await spawn(wc.run, daemon=True)

async def bricknil_socket_server(web_out_queue, address): #pragma: no cover
    """Listen for client connections on port 25000 and spawn
       `WebClient` instance.
       This fuction is spawned as a task during system instantiation
       in :func:`bricknil.bricknil._run_all``
    """
    async def web_client_connected(client, addr):
        logger.info('connection from', addr)
        wc = WebClient(client, addr, web_out_queue)
        await wc.run()

    task = await spawn(tcp_server, '', 25000, web_client_connected, daemon=True)


class WebClient: #pragma: no cover
    """ Represents a client that has connected to BrickNil's server

        Each client has a connection to the global BrickNil `curio.Queue`
        that handles broadcast messages about peripherals.  Peripherals
        insert the messages into the queue, and clients can read from 
        it (hence why it's called in_queue in this class).
    """
    def __init__(self, client, addr, in_queue):
        assert in_queue is not None
        self.in_queue = in_queue
        self.client = client
        self.addr = addr
        logger.info(f'Web client {client} connected from {addr}')
        

    async def run(self):

        async with self.client:
            while True:
                msg = await self.in_queue.get()
                #print(f'Webclient queue got: {msg}')
                await self.in_queue.task_done()
                await self.client.sendall(msg)
        logger.info('connection closed')

class WebMessage:
    """Handles message conversion into JSON and transmission
    """

    def __init__(self, hub):
        self.hub = hub
    
    async def send(self, peripheral, msg):
        obj = { 'hub': self.hub.name,
                'peripheral_type': peripheral.__class__.__name__,
                'peripheral_name': peripheral.name,
                'peripheral_port': peripheral.port,
                'message': msg ,
        }
        obj_string = json.dumps(obj)
        logger.debug(obj_string)
        await self.hub.web_queue_out.put(f'{obj_string}\n'.encode('utf-8'))
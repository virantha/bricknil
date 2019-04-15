from quart import Quart
from quart import render_template, make_response, websocket

import asyncio
from functools import wraps
import sys

from bricknil.sensor import *
from bricknil.sensor.motor import Motor

from random import randint
app = Quart(__name__)

@app.route('/')
async def index():
   return await render_template('base.html', message='hello world')


connected = set()
hubs = {}  # Per websocket set
replay_messages = {}  # Dict is mainly for the value

def collect_websocket(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global connected
        connected.add(websocket._get_current_object())
        try:
            return await func(*args, **kwargs)
        finally:
            connected.remove(websocket._get_current_object())
    return wrapper

@app.websocket('/ws')
@collect_websocket
async def ws():
    # Replay all the relevant messages seen before this time:
    #   - ADD_HUB
    #   - ADD_PERIPHERAL
    #   - UPDATE_VALUE (only the last message is stored)
    for msg, val in replay_messages.items():
        print(f'Replaying:  {msg} {val}')
        await websocket.send(f'{msg} {val}')

    while True:
        data = await websocket.receive()
        rn = randint(0,100)
        msg = f'Got your message: {data}. Here is your treat: {rn}!'
        await websocket.send(f'echo {msg}')


@app.before_serving
def startup():
    # Start up an socket listener for bricknil messages
    asyncio.ensure_future(socket_listener())


async def _broadcast(message):
    if message.startswith("UPDATE_VALUE"):
        msg_parts = message.split(' ')
        key = ' '.join(msg_parts[:-1])
        val = msg_parts[-1]
        replay_messages[key] = val
    else:
        replay_messages[message] = ""

    for websock in connected:
        await websock.send(message)

async def broadcast(message):
    global hubs
    print(message)
    message = message.decode('utf-8')
    print(message.split('|'))
    hub_name, peripheral_type, peripheral_name, port, msg = message.split('|')
    if 'Motor' in peripheral_type:
        peripheral_type = 'Motor'
    if msg.startswith('flush'):
        msg = 'RESET {hub_name}'
        await _broadcast(msg)
    elif msg.startswith('set') or msg.startswith('value change'):
        mode_val = msg.split('mode:')[1].strip()
        print(mode_val)
        mode, val = [int(m.strip()) for m in mode_val.split('=')]
        local_peripheral_name = f'{peripheral_name}_{mode}' # append the mode so we have different peripherals for each mode

        # Get the class name to get the attributes
        thismodule = sys.modules[__name__]
        class_ = getattr(thismodule, peripheral_type)
        # map the capabilities to mode if present
        if 'capability' in dir(class_):
            # This is a sensor!
            mode_str = class_.capability(mode).name
            if mode_str in ['sense_distance', 'sense_reflectivity']:
                peripheral_type = 'Distance'
        else:
            mode_str = str(mode)  # Find some way to set this for a pure output device

        if not hub_name in hubs:
            hub = hubs.setdefault(hub_name, {})
            msg = f'ADD_HUB {hub_name}'
            await _broadcast(msg)
        hub = hubs[hub_name]
        if local_peripheral_name not in hub:
            msg = f'ADD_PERIPHERAL {hub_name} {peripheral_type} {peripheral_name} {mode_str}'
            await _broadcast(msg)
        hub[local_peripheral_name] = val
        msg = f'UPDATE_VALUE {hub_name} {peripheral_type} {peripheral_name} {mode_str} {val}'
        await _broadcast(msg)


async def socket_listener():
    
    #await asyncio.sleep(5)
    #await broadcast(b'test|LED|led|19|set output mode: 0 = 5')
    #await broadcast(b'test|DuploSpeaker|speakr|19|set output mode: 0 = 1')
    #await broadcast(b'test|DuploTrainMotor|motor|19|set output mode: 0 = 50')
    #await broadcast(b'test|LED|led|19|set output mode: 0 = 6')
    #await broadcast(b'test|VoltageSensor|voltage|19|value change mode: 0 = 3000')
    #await broadcast(b'test|DuploVisionSensor|vision|19|value change mode: 2 = 30')
    #await broadcast(b'test|DuploSpeedSensor|speed_sensor|19|value change mode: 1 = 30')
    #await asyncio.sleep(1)
    #await broadcast(b'test|DuploTrainMotor|motor|19|set output mode: 0 = 80')
    #await asyncio.sleep(5)
    #await broadcast(b'test|*|*|*|flush')
    #return
    loop = asyncio.get_running_loop()
    reader, writer = await asyncio.open_connection('127.0.0.1', 25000, loop=loop)
    print('Connected')
    while True:
        #rn = randint(0,100)
        #data = f'{rn}'
        #await asyncio.sleep(1)
        #data = await reader.read(1000)
        data = await reader.readline()
        if not data:
            break
        await broadcast(data)
        print(f'received: {data}')
    print('Connection closed')

    #server = await loop.create_server(BricknilProtocol, '127.0.0.1', 25000)
    #print('starting to serve')
    #await server.serve_forever()
    #print('served!')
    #return 'Success'

    #while True:
        #print('hello')
        #await asyncio.sleep(1)

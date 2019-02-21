BlueBrick - Control LEGO Bluetooth Sensors and Motors with Python
=================================================================

|image_pypi| |image_downloads| |image_license| |passing| |quality| |Coverage Status|

BlueBrick provides an easy way to connect to and program LEGO\ |reg|
Bluetooth hubs (including the newer 60197 and 60198 train sets) using Python on OS X and
Linux.  This work was inspired by this EuroBricks_ thread, and the NodeJS Powered-Up_
library.  It requires modern Python (designed and tested for 3.7) and uses asynchronous
event programming built on top of the Curio_ async library.  As an aside, the choice of
async library is fairly arbitrary; and conceivably enabling another library such as asyncio or Trio 
should be straightforward.

An example BlueBrick program for controlling the Train motor speed is shown below::

   from curio import sleep
   from bluebrick import attach, start
   from bluebrick.hub import PoweredUpHub
   from bluebrick.sensor import TrainMotor

   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):

       async def run(self):
           for i in range(2):  # Repeat this control two times
               await self.motor.ramp_speed(80,5000) # Ramp speed to 80 over 5 seconds
               await sleep(6)
               await self.motor.ramp_speed(0,1000)  # Brake to 0 over 1 second
               await sleep(2)

   async def system():
       train = Train('My train')

   if __name__ == '__main__':
       start(system)


* Free and open-source software: ASL2 license
* Blog: http://virantha.com/category/projects/bluebrick
* Documentation: http://virantha.github.io/bluebrick
* Source: https://github.com/virantha/bluebrick

Features
########

* Supports the following LEGO\ |reg| Bluetooth systems:
   * PoweredUp hubs for trains
   * Boost Move hub
* Supports the following actuators/sensors:
   * Internal motors
   * Train motors
   * Hub LED color
   * Boost vision sensor (color, distance)
   * Internal tilt/orientation/accelerometer 
   * Hub buttons
* Fully supports Python asynchronous keywords and coroutines
* Allows expressive concurrent programming using async/await syntax
   * The current implmentation uses the async library Curio_ by David Beazley 
* Leverages the Adafruit Bluefruit BluetoothLE library
   * Supports Mac OS X (possibly the only BLE library in Python to support native CoreBluetooth access). 
   * Should also support Linux with BlueZ but currently not tested.


.. _Curio: http://curio.readthedocs.io
.. _EuroBricks: https://www.eurobricks.com/forum/index.php?/forums/topic/162288-powered-up-a-tear-down/
.. _Powered-Up: https://github.com/nathankellenicki/node-poweredup

Building a simple train controller
##################################

Let's build a simple program to control a LEGO\ |reg| PoweredUp train.  The first thing to do
is create a class that subclasses the Bluetooth hub that we'll be using::

   from bluebrick.hub import PoweredUpHub

   class Train(PoweredUpHub):

      async def run(self):
         ...

The ``run`` async function (it's actually a coroutine) will contain the code that will control
everything attached to this hub.  Speaking of which, because we'll be wanting to control the train
motor connected to this hub, we'd better attach it to the code like so::

   from bluebrick.hub import PoweredUpHub
   from bluebrick.sensor import TrainMotor

   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):

      async def run(self):
         ...

Now, we can access the motor functions by calling the object `self.motor` inside `run`.  For example,
let's say that we wanted to set the motor speed to 50 (the allowed range is -100 to 100 where negative
numbers are reverse speeds)::

   from curio import sleep
   from bluebrick.hub import PoweredUpHub
   from bluebrick.sensor import TrainMotor

   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):

      async def run(self):
         await self.motor.set_speed(50)
         await sleep(5)  # Wait 5 seconds before exiting 

Notice that we're using the `await` keyword in front of all the calls, because
those are also asynchronous coroutines that will get run in the event loop.
At some point, the :func:`bluebrick.sensor.TrainMotor.set_speed` coroutine
will finish executing and control will return back to the statement after it.
The next statement is a call to the `sleep` coroutine from the `curio`
library. It's important to use this, instead of the regular *function*
`time.sleep` because `curio.sleep` is a coroutine that will **not** block
other tasks from running.

Note that we can use arbitrary Python to build our controller; suppose that we
wanted to ramp the motor speed gradually to 80 over 5 seconds, and then reduce
speed back to a stop in 1 second, and then repeat it over again.  We could implement
the `run` logic as::

    async def run(self):
        for i in range(2):
            await self.motor.ramp_speed(80,5000)
            await sleep(5)
            await self.motor.ramp_speed(0,1000) 
            await sleep(2)

The :func:`bluebrick.sensor.TrainMotor.ramp_speed` function will ramp the speed from 
whatever it is currently to the target speed over the millisecond duration given (internally, it will
change the train speed every 100ms).  Here, you can see how things are running concurrently:  we issue
the ramp_speed command, that will take 5 seconds to complete in the background,
so we need to make sure our control logic sleeps for 5 seconds too, to ensure
the train has enough time to get up to speed, before we issue the braking command.  Once the train
comes to a stop, it will stay stopped for 1 second, then repeat this sequence of speed changes
once more before exiting.

It's also useful to print out what's happening as we run our program. In order to facilitate that, 
there is some rudimentary logging capability built-in to `bluebrick` via the 
:class:`bluebrick.process.Process` class that all of these concurrent processes are sub-classed from.
Here's the run coroutine with logging statements via
:func:`bluebrick.process.Process.message_info` enabled::

    async def run(self):
        self.message_info("Running")
        for i in range(2):
            self.message_info('Increasing speed')
            await self.motor.ramp_speed(80,5000)
            await sleep(5)
            self.message_info('Coming to a stop')
            await self.motor.ramp_speed(0,1000) 
            await sleep(2)


Of course, just running the above code isn't quite enough to execute the
controller.  Once we have the controller logic implemented, we need to define
our entire system in a separate top-level coroutine like so::

   async def system():
       train = Train('My train')

This coroutine instantiates all the hubs we want to control; once we have that,
we can go ahead and implement the full program that calls
:func:`bluebrick.start` with this `system` coroutine::

   from curio import sleep
   from bluebrick import attach, start
   from bluebrick.hub import PoweredUpHub
   from bluebrick.sensor import TrainMotor
   from bluebrick.process import Process

   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):

       async def run(self):
           self.message_info("Running")
           for i in range(2):
               self.message_info('Increasing speed')
               await self.motor.ramp_speed(80,5000)
               await sleep(5)
               self.message_info('Coming to a stop')
               await self.motor.ramp_speed(0,1000) 
               await sleep(2)

   async def system():
       train = Train('My train')

   if __name__ == '__main__':
       Process.level = Process.MSG_LEVEL.INFO
       start(system)

Running this program will output the following::

   BLE Event Q.0: Looking for first matching hub
   BLE Event Q.0: Connected to device
   BLE Event Q.0: Device name HUB NO.4
   BLE Event Q.0: Device id XXXX-XXXX
   BLE Event Q.0: Device advertised [UUID('XXXXX')]
   My train.2: Waiting for peripheral motor to attach to a port
   My train.2: Running
   My train.2: Increasing speed
   motor.1: Starting ramp of speed: 0 -> 80 (5.0s)
   motor.1: Setting speed to 0
   motor.1: Setting speed to 1
   motor.1: Setting speed to 3
   motor.1: Setting speed to 4
   ...
   motor.1: Setting speed to 80
   My train.2: Coming to a stop
   motor.1: Starting ramp of speed: 76 -> 0 (1.0s)
   motor.1: Setting speed to 76
   motor.1: Setting speed to 68
   motor.1: Setting speed to 60
   motor.1: Setting speed to 53
   motor.1: Setting speed to 45
   motor.1: Setting speed to 38
   motor.1: Setting speed to 30
   motor.1: Setting speed to 22
   motor.1: Setting speed to 15
   motor.1: Setting speed to 0
   ... repeats

Integrating a vision sensor into a simple train controller
##########################################################

Now let's build a controller that sets the speed of the train depending on how
close your hand is to a snensor, and will quit the program if you wave your hand
more than three times in front of it.

We'll be using the Vision Sensor that comes with the LEGO Boost robotics kit;
plug the sensor into the second port of the train's PoweredUP hub.  This sensor
has a multitude of different sensing abilities including distance and color,
but for this example, we're just going to use the `sense_count` and
`sense_distance` capabilities.  The former measures how many times it sees
something pass in front of it at a distance of ~2 inches, while the latter
measures roughly how many inches something is from the sensor (from 1-10
inches).  For a full list of the supported capabilities, please see the API
documentation at :class:`bluebrick.sensor.VisionSensor`.

The full program is listed at the end of this section, but let's just go through
it bit by bit.  The first thing we'll do is attach the sensor to the Train class::

   @attach(VisionSensor, name='train_sensor', capabilities=['sense_count', 'sense_distance'])
   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):
	...

Anytime you attach a sensor to the system (motion, tilt, color, etc), you need to define
what capabilities you want to enable; each sensor can physically provide different capabilities
depending on which sensor you're using.  As soon as you attach a sensor, you need to provide
a call-back coroutine that will be called whenever the sensor detects a change like so::

   @attach(VisionSensor, name='train_sensor', capabilities=['sense_count', 'sense_distance'])
   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):

       async def train_sensor_change(self):
	   ...

The values will be provided in dictionary called `self.value` that is indexed by the capability.
Let's look at a practical example, and implement the logic we were discussing above::

   @attach(VisionSensor, name='train_sensor', capabilities=['sense_count', 'sense_distance'])
   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):

       async def train_sensor_change(self):
	   distance = self.train_sensor.value[VisionSensor.capability.sense_distance]
	   count = self.train_sensor.value[VisionSensor.capability.sense_count]

	   if count > 3:
	       # Wave your hand more than three times in front of the sensor and the program ends
	       self.keep_running = False

	   # The closer your hand gets to the sensor, the faster the motor runs
	   self.motor_speed = (10-distance)*10

	   # Flag a change
	   self.sensor_change = True

Here, we get the `distance` and `count` from the `value` dict.  If the `count` is greater than
3 (more than 3 hand waves), we set a flag that keeps the system running to `False`.  Next, based
on the inverse of the distance, we set a motor_speed instance variable, and then use `self.sensor_change`
to signal to the main `run` routine that a sensor update has happened.  Our `run` logic can now
use these values to implement the controller::

    async def run(self):
        self.motor_speed = 0
        self.keep_running = True
        self.sensor_change = False

        while self.keep_running:
            if self.sensor_change:
                await self.motor.ramp_speed(self.motor_speed, 900)  # Ramp to new speed in 0.9 seconds
                self.sensor_change = False
            await sleep(1)

We keep running the train while `keep_running` flag is `True`; if a `sensor_change` is detected,
we ramp the train speed to the new target `self.motor_speed` in 0.9 seconds, and then wait
for the next sensor update, whenever that may be, at intervals of 1 second.  As soon as you pass
your hand more than three times in front of the sensor, the program will exit this `while` loop
and end.

Here's the full code::

   from curio import sleep
   from bluebrick import attach, start
   from bluebrick.hub import PoweredUpHub
   from bluebrick.sensor import TrainMotor, VisionSensor
   from bluebrick.process import Process

   @attach(VisionSensor, name='train_sensor', capabilities=['sense_count', 'sense_distance'])
   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):

       async def train_sensor_change(self):
	   distance = self.train_sensor.value[VisionSensor.capability.sense_distance]
	   count = self.train_sensor.value[VisionSensor.capability.sense_count]

	   if count > 3:
	       # Wave your hand more than three times in front of the sensor and the program ends
	       self.keep_running = False

	   # The closer your hand gets to the sensor, the faster the motor runs
	   self.motor_speed = (10-distance)*10

	   # Flag a change
	   self.sensor_change = True

       async def run(self):
	   self.motor_speed = 0
	   self.keep_running = True
	   self.sensor_change = False

	   while self.keep_running:
	       if self.sensor_change:
		   await self.motor.ramp_speed(self.motor_speed, 900)  # Ramp to new speed in 0.9 seconds
		   self.sensor_change = False
	       await sleep(1)

   async def system():
       train = Train('My Train')

   if __name__ == '__main__':
       Process.level = Process.MSG_LEVEL.INFO
       start(system)

Further examples
################

Hub buttons and LED colors
--------------------------
Here's an example that enables the train motor, vision sensor, hub button, and hub LED.  First,
we'll wait until the hub button is pressed before we do anything; the LED will blink purple and yellow
while it's waiting.  Then, we'll change the speed like the previous example based on the vision distance,
while at the same time changing the LED color orange if it's responding to a distance change.


.. literalinclude:: ../examples/train_all.py
    :language: python

Multiple hubs
-------------
TODO: Need to show an example here; maybe two trains or a Boost-hub-controlled switch with a train hub.
   
BlueBrick Architecture
######################
This section documents the internal architecture of BlueBrick and how all the components communicate with
each other.

Run loops
---------
There are actually two threads of execution in the current system architecture.
The main Bluetooth radio communication loop is provided by the BluetoothLE
library, which manages everything in the background and can callback directly
into user code.  In parallel with this, inside this library, a separate
execution loop is running the Curio event library, which provides the async
event loop that executes our user code. Thus, we need to be careful about
maintaining thread safety between the Curio async event loop and the background
Bluetooth event processing.  

.. figure:: images/run_loops.svg
    :align: center

    BlueBrick running inside Curio's event loop, which in turn is run by the
    Adafruit_BluefruitLE library run loop

I'd much have preferred to have the Bluetooth library be implemented via an
async library like Curio, asyncio, or Trio, but I wasn't able to find any such
library. This admitted kludge of nested run loops was the only way I could get everything
working.  



Installation
############

On Mac OS X, it should just be a simple:

.. code-block:: bash

    $ pip install bluebrick

Installing on other platforms like Linux is not supported at this time until I can break out the
mac requirements, and test bluez.

Disclaimer
##########

The software is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  Licensed under ASL 2.0

.. |image_pypi| image:: https://badge.fury.io/py/bluebrick.png
   :target: https://pypi.python.org/pypi/bluebrick
.. |image_downloads| image:: https://img.shields.io/pypi/mm/bluebrick.svg
.. |image_license| image:: https://img.shields.io/pypi/l/bluebrick.svg
   :target: https://www.apache.org/licenses/LICENSE-2.0
.. |passing| image:: https://scrutinizer-ci.com/g/virantha/bluebrick/badges/build.png?b=master
.. |quality| image:: https://scrutinizer-ci.com/g/virantha/bluebrick/badges/quality-score.png?b=master
   :target: https://scrutinizer-ci.com/g/virantha/bluebrick
.. |Coverage Status| image:: https://coveralls.io/repos/virantha/bluebrick/badge.png?branch=develop
   :target: https://coveralls.io/r/virantha/bluebrick

.. |reg|    unicode:: U+000AE .. REGISTERED SIGN

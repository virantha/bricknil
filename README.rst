BrickNil - Control LEGO Bluetooth Sensors and Motors with Python
=================================================================

|image_pypi| |image_downloads| |image_license| |passing| |quality| |Coverage Status|

.. |image_pypi| image:: https://img.shields.io/pypi/v/bricknil.svg
   :target: https://pypi.python.org/pypi/bricknil
.. |image_downloads| image:: https://img.shields.io/pypi/dd/bricknil.svg
.. |image_license| image:: https://img.shields.io/pypi/l/bricknil.svg
   :target: https://www.apache.org/licenses/LICENSE-2.0
.. |passing| image:: https://scrutinizer-ci.com/g/virantha/bricknil/badges/build.png?b=master
.. |quality| image:: https://scrutinizer-ci.com/g/virantha/bricknil/badges/quality-score.png?b=master
   :target: https://scrutinizer-ci.com/g/virantha/bricknil
.. |Coverage Status| image:: https://img.shields.io/coveralls/github/virantha/bricknil.svg
   :target: https://coveralls.io/r/virantha/bricknil

.. |reg|    unicode:: U+000AE .. REGISTERED SIGN

BrickNil [*]_ provides an easy way to connect to and program LEGO\ |reg|
Bluetooth hubs (including the PoweredUp Passenger Train 60197_ and Cargo Train 60198_ sets, and the Lego
Duplo Steam Train 10874_ and Cargo Train 10875_ ) using Python on OS X and
Linux.  This work was inspired by this EuroBricks_ thread, and the NodeJS Powered-Up_
library. Unlike the official apps available from LEGO, BrickNil allows you to control multiple
hubs with a single program, which lets you easily scale to programming large interactive systems.

BrickNil requires modern Python (designed and tested for 3.7) and uses asynchronous
event programming built on top of the Curio_ async library.  As an aside, the choice of
async library is fairly arbitrary; and enabling another library such as asyncio or Trio 
should be straightforward.

An example BrickNil program for controlling the Train motor speed is shown below:

.. code-block:: python

   from curio import sleep
   from bricknil import attach, start
   from bricknil.hub import PoweredUpHub
   from bricknil.sensor import TrainMotor

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
* Documentation: http://virantha.github.io/bricknil
* Source: https://github.com/virantha/bricknil

.. [*] BrickNil's name comes from the word "Nil" (නිල්) in Sinhala_ which means Blue (as in Bluetooth)

.. _Sinhala: https://en.wikipedia.org/wiki/Sinhalese_language
.. _60197: https://www.amazon.com/gp/product/B07CC37F63/ref=as_li_tl?ie=UTF8&tag=virantha-20&camp=1789&creative=9325&linkCode=as2&creativeASIN=B07CC37F63
.. _60198: https://www.amazon.com/gp/product/B07C39LCZ9/ref=as_li_tl?ie=UTF8&tag=virantha-20&camp=1789&creative=9325&linkCode=as2&creativeASIN=B07C39LCZ9
.. _10874: https://www.amazon.com/gp/product/B07BK6M2WC/ref=as_li_tl?ie=UTF8&tag=virantha-20&camp=1789&creative=9325&linkCode=as2&creativeASIN=B07BK6M2WC
.. _10875: https://www.amazon.com/gp/product/B07BK6KQR6/ref=as_li_tl?ie=UTF8&tag=virantha-20&camp=1789&creative=9325&linkCode=as2&creativeASIN=B07BK6KQR6
.. _Boost: https://www.amazon.com/gp/product/B06Y6JCTKH/ref=as_li_tl?ie=UTF8&tag=virantha-20&camp=1789&creative=9325&linkCode=as2&creativeASIN=B06Y6JCTKH

Features
########

* Supports the following LEGO\ |reg| Bluetooth systems:
   * PoweredUp hubs for trains 60197_, 60198_
   * Duplo trains 10874_ and 10875_
   * PoweredUp remote
   * Boost_ Move hub
* Supports the following actuators/sensors:
   * Internal motors
   * Train motors
   * Hub LED color
   * Boost vision sensor (color, distance)
   * Boost internal tilt/orientation/accelerometer 
   * Boost external motor 
   * External light
   * Hub buttons
   * Wedo external motor
   * Wedo tiltand motion sensors
* Fully supports Python asynchronous keywords and coroutines
   * Allows expressive concurrent programming using async/await syntax
   * The current implementation uses the async library Curio_ by David Beazley 
* Cross-platform
   * Uses the Adafruit Bluefruit BluetoothLE library for Mac OS X
   * Uses the Bleak Bluetooth library for Linux and Win10; also tested on Raspberry Pi.


.. _Curio: http://curio.readthedocs.io
.. _EuroBricks: https://www.eurobricks.com/forum/index.php?/forums/topic/162288-powered-up-a-tear-down/
.. _Powered-Up: https://github.com/nathankellenicki/node-poweredup
.. _Bleak: https://github.com/hbldh/bleak

Building a simple train controller
##################################

Let's build a simple program to control a LEGO\ |reg| PoweredUp train.  The first thing to do
is create a class that subclasses the Bluetooth hub that we'll be using:

.. code-block:: python

   from bricknil.hub import PoweredUpHub

   class Train(PoweredUpHub):

      async def run(self):
         ...

The ``run`` async function (it's actually a coroutine) will contain the code that will control
everything attached to this hub.  Speaking of which, because we'll be wanting to control the train
motor connected to this hub, we'd better attach it to the code like so:

.. code-block:: python

   from bricknil.hub import PoweredUpHub
   from bricknil.sensor import TrainMotor

   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):

      async def run(self):
         ...

Now, we can access the motor functions by calling the object `self.motor` inside `run`.  For example,
let's say that we wanted to set the motor speed to 50 (the allowed range is -100 to 100 where negative
numbers are reverse speeds):

.. code-block:: python

   from curio import sleep
   from bricknil.hub import PoweredUpHub
   from bricknil.sensor import TrainMotor

   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):

      async def run(self):
         await self.motor.set_speed(50)
         await sleep(5)  # Wait 5 seconds before exiting 

Notice that we're using the `await` keyword in front of all the calls, because
those are also asynchronous coroutines that will get run in the event loop.
At some point, the :meth:`bricknil.peripheral.Motor.set_speed` coroutine
will finish executing and control will return back to the statement after it.
The next statement is a call to the `sleep` coroutine from the `curio`
library. It's important to use this, instead of the regular *function*
`time.sleep` because `curio.sleep` is a coroutine that will **not** block
other tasks from running.

Note that we can use arbitrary Python to build our controller; suppose that we
wanted to ramp the motor speed gradually to 80 over 5 seconds, and then reduce
speed back to a stop in 1 second, and then repeat it over again.  We could implement
the `run` logic as:

.. code-block:: python

    async def run(self):
        for i in range(2):
            await self.motor.ramp_speed(80,5000)
            await sleep(5)
            await self.motor.ramp_speed(0,1000) 
            await sleep(2)

The :meth:`bricknil.peripheral.Motor.ramp_speed` function will ramp the speed from 
whatever it is currently to the target speed over the millisecond duration given (internally, it will
change the train speed every 100ms).  Here, you can see how things are running concurrently:  we issue
the ramp_speed command, that will take 5 seconds to complete in the background,
so we need to make sure our control logic sleeps for 5 seconds too, to ensure
the train has enough time to get up to speed, before we issue the braking command.  Once the train
comes to a stop, it will stay stopped for 1 second, then repeat this sequence of speed changes
once more before exiting.

It's also useful to print out what's happening as we run our program. In order to facilitate that, 
there is some rudimentary logging capability built-in to `bricknil` via the 
:class:`bricknil.process.Process` class that all of these concurrent processes are sub-classed from.
Here's the run coroutine with logging statements via
:meth:`bricknil.process.Process.message_info` enabled:

.. code-block:: python

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
our entire system in a separate top-level coroutine like so:

.. code-block:: python

   async def system():
       train = Train('My train')

This coroutine instantiates all the hubs we want to control; once we have that,
we can go ahead and implement the full program that calls
:func:`bricknil.start` with this `system` coroutine:

.. code-block:: python

   from curio import sleep
   from bricknil import attach, start
   from bricknil.hub import PoweredUpHub
   from bricknil.sensor import TrainMotor
   from bricknil.process import Process
   import logging

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
       logging.basicConfig(level=logging.INFO)
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
documentation at :class:`bricknil.sensor.VisionSensor`.

The full program is listed at the end of this section, but let's just go through
it bit by bit.  The first thing we'll do is attach the sensor to the Train class:

.. code-block:: python

   @attach(VisionSensor, name='train_sensor', capabilities=['sense_count', 'sense_distance'])
   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):
	...

Anytime you attach a sensor to the system (motion, tilt, color, etc), you need to define
what capabilities you want to enable; each sensor can physically provide different capabilities
depending on which sensor you're using.  As soon as you attach a sensor, you need to provide
a call-back coroutine that will be called whenever the sensor detects a change like so:

.. code-block:: python

   @attach(VisionSensor, name='train_sensor', capabilities=['sense_count', 'sense_distance'])
   @attach(TrainMotor, name='motor')
   class Train(PoweredUpHub):

       async def train_sensor_change(self):
	   ...

The values will be provided in dictionary called `self.value` that is indexed by the capability.
Let's look at a practical example, and implement the logic we were discussing above:

.. code-block:: python

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
use these values to implement the controller:

.. code-block:: python

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

Here's the full code:

.. code-block:: python

   from curio import sleep
   from bricknil import attach, start
   from bricknil.hub import PoweredUpHub
   from bricknil.sensor import TrainMotor, VisionSensor
   from bricknil.process import Process
   import logging

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
       logging.basicConfig(level=logging.INFO)
       start(system)

More examples
################

Connecting to a specific hub
----------------------------
If you know the BluetoothLE network address of the hub you want to connect to, then you can force a Hub object
to only connect to that hub.  This can be useful, for example, for connecting to two trains that need to have different
code and can be accomplished by passing in the ``ble_id`` argument during instantiation of the Hub.  

On Windows and Linux, you will use the 6-byte Bluetooth network address:

.. code-block:: python

   async def system():
       hub = Train('train1', ble_id='XX:XX:XX:XX:XX:XX')
       hub = Train('train2', ble_id='YY:YY:YY:YY:YY:YY')

And on OS X systems, you will use the UUID for the Bluetooth hub like so:

.. code-block:: python

   async def system():
       hub = Train('train1', ble_id='05c5e50e-XXXX-XXXX-XXXX-XXXXXXXXXXXX')
       hub = Train('train2', ble_id='05c5e50e-YYYY-YYYY-YYYY-YYYYYYYYYYYY')





Hub buttons and LED colors
--------------------------
Here's an example that enables the train motor, vision sensor, hub button, and hub LED.  First,
we'll wait until the hub button is pressed before we do anything; the LED will blink purple and yellow
while it's waiting.  Then, we'll change the speed like the previous example based on the vision distance,
while at the same time changing the LED color orange if it's responding to a distance change.


.. literalinclude:: ../examples/train_all.py
    :language: python

Controlling Vernie (Boost Hub) with the PoweredUp Remote
--------------------------------------------------------
Here's a nice example of controlling two hubs (the remote is also a type of hub) and 
feeding the button presses of the remote to make Vernie move forward, backward, left, and right.

.. raw:: html

    <div style="position: relative; height: 0; overflow: hidden; max-width: 100%; height: auto;">
            <iframe width="560" height="315" src="https://www.youtube.com/embed/Mme2gFRiMI0" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
    </div>

And here's the code that's being used in the video above:

.. literalinclude:: ../examples/vernie_remote.py 
    :language: python

Here, we are using two hubs running in parallel, and we use a `curio.Queue` to send messages
from the remote telling the robot(Boost hub) what to do. Notice that each RemoteButtons 
instance consists of 3 buttons, so there are some helper methods to check if a particular
button is pressed.

Using the Duplo Train and Playing Sounds
----------------------------------------
The Duplo trains 10874_ and 10875_ have the ability to play a set of 5
predetermined sounds through their built-in speakers
(:class:`bricknil.sensor.DuploSpeaker`).  In addition, there is a
speedometer(:class:`bricknil.sensor.DuploSpeedSensor`) built-in to the front
wheels, and a vision sensor(:class:`bricknil.sensor.DuploVisionSensor`) in the
undercarriage pointing straight down.  This vision sensor is slightly less
capable than the stand-alone Boost Vision Sensor discussed above, but it can
still recognize colors, distance, and the special blocks that Lego provides in
those sets.  Here's an example that puts everything together:

.. literalinclude:: ../examples/duplo_train.py
    :language: python


BrickNil Architecture
######################
This section documents the internal architecture of BrickNil and how all the components communicate with
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

    BrickNil running inside Curio's event loop, which in turn is run by the
    Adafruit_BluefruitLE library run loop

I'd much have preferred to have the Bluetooth library be implemented via an
async library like Curio, asyncio, or Trio, but I wasn't able to find any such
library. This admitted kludge of nested run loops was the only way I could get everything
working.  



Installation
############

On all platforms (OS X, Linux, Win10), it should just be a simple:

.. code-block:: bash

    $ pip install bricknil

On Linux, you might need to install the `BlueZ >= 5.43` libraries. 

On a Raspberry Pi (and other Linux boxes should be similar), you can follow my automated 
:doc:`setup instructions <pi_setup>`


Supported Devices
#################

.. list-table:: BrickNil supported |lego| devices
   :header-rows: 1
   :widths: 35 25 40

   * - Peripheral
     - Sets
     - Support
   * - PoweredUp Hub (88009_)
     - :amzn:`60197 <B07CC37F63>`, :amzn:`60198 <B07C39LCZ9>`, :amzn:`76112 <B07BMGR1FN>`
     - :class:`~bricknil.hub.PoweredUpHub` 
         - LED: :class:`~bricknil.sensor.light.LED`
         - Button: :class:`~bricknil.sensor.sensor.Button`
         - Current: :class:`~bricknil.sensor.sensor.CurrentSensor`
         - Voltage: :class:`~bricknil.sensor.sensor.VoltageSensor`
   * - PoweredUp Train Motor (88011_)
     - :amzn:`60197 <B07CC37F63>`, :amzn:`60198 <B07C39LCZ9>`
     - :class:`~bricknil.sensor.motor.TrainMotor`
   * - PoweredUp Remote (88010_)
     - :amzn:`60197 <B07CC37F63>`, :amzn:`60198 <B07C39LCZ9>`
     - :class:`~bricknil.hub.PoweredUpRemote`
         - :class:`~bricknil.sensor.sensor.RemoteButtons`
   * - PoweredUp Light (88005_)
     - 88005_
     - :class:`~bricknil.sensor.light.Light`
   * - Boost Hub (88006_)
     - :amzn:`17101 <B06Y6JCTKH>`
     - :class:`~bricknil.hub.BoostHub` 
         - Motors: :class:`~bricknil.sensor.motor.InternalMotor`
         - Tilt: :class:`~bricknil.sensor.sensor.InternalTiltSensor` 
         - LED: :class:`~bricknil.sensor.light.LED`
         - Button: :class:`~bricknil.sensor.sensor.Button`
         - Current: :class:`~bricknil.sensor.sensor.CurrentSensor`
         - Voltage: :class:`~bricknil.sensor.sensor.VoltageSensor`
   * - Boost Vision Sensor (88007_)
     - :amzn:`17101 <B06Y6JCTKH>`
     - :class:`~bricknil.sensor.sensor.VisionSensor`
   * - Boost External Motor (88008_)
     - :amzn:`17101 <B06Y6JCTKH>`
     - :class:`~bricknil.sensor.motor.ExternalMotor`
   * - Wedo External Motor (45303_)
     - :amzn:`45300 <B01A9A9XLW>`
     - :class:`~bricknil.sensor.motor.WedoMotor`
   * - Wedo Tilt Sensor (45305_)
     - :amzn:`45300 <B01A9A9XLW>`
     - :class:`~bricknil.sensor.sensor.ExternalTiltSensor`
   * - Wedo Motion Sensor (45304_)
     - :amzn:`45300 <B01A9A9XLW>`
     - :class:`~bricknil.sensor.sensor.ExternalMotionSensor`
   * - Duplo Train Base
     - :amzn:`10874 <B07BK6M2WC>`, :amzn:`10875 <B07BK6KQR6>`
     - :class:`~bricknil.hub.DuploTrainHub`
         - Motor: :class:`~bricknil.sensor.motor.DuploTrainMotor`
         - Speedometer: :class:`~bricknil.sensor.sensor.DuploSpeedSensor`
         - Vision: :class:`~bricknil.sensor.sensor.VisionSensor`
         - Speaker: :class:`~bricknil.sensor.sound.DuploSpeaker`
         - Voltage: :class:`~bricknil.sensor.sensor.VoltageSensor`


.. _88005: https://click.linksynergy.com/deeplink?id=seuBib7H7fY&mid=13923&murl=http%3A%2F%2Fshop.lego.com%2Fen-US%2Fproduct%2FLight-88005
.. _88006: https://click.linksynergy.com/deeplink?id=seuBib7H7fY&mid=13923&murl=http%3A%2F%2Fshop.lego.com%2Fen-US%2Fproduct%2FMove-Hub-88006
.. _88007: https://click.linksynergy.com/deeplink?id=seuBib7H7fY&mid=13923&murl=http%3A%2F%2Fshop.lego.com%2Fen-US%2Fproduct%2FColor-Distance-Sensor-88007
.. _88008: https://click.linksynergy.com/deeplink?id=seuBib7H7fY&mid=13923&murl=http%3A%2F%2Fshop.lego.com%2Fen-US%2Fproduct%2FMedium-Linear-Motor-88008
.. _88009: https://click.linksynergy.com/deeplink?id=seuBib7H7fY&mid=13923&murl=http%3A%2F%2Fshop.lego.com%2Fen-US%2Fproduct%2FHub-88009
.. _88010: https://click.linksynergy.com/deeplink?id=seuBib7H7fY&mid=13923&murl=http%3A%2F%2Fshop.lego.com%2Fen-US%2Fproduct%2FRemote-Control-88010
.. _88011: https://click.linksynergy.com/deeplink?id=seuBib7H7fY&mid=13923&murl=http%3A%2F%2Fshop.lego.com%2Fen-US%2Fproduct%2FTrain-Motor-88011
.. _45303: https://click.linksynergy.com/deeplink?id=seuBib7H7fY&mid=13923&murl=http%3A%2F%2Fshop.lego.com%2Fen-US%2Fproduct%2FSimple-Medium-Linear-Motor-45303
.. _45305: https://education.lego.com/en-us/products/wedo-2-0-tilt-sensor/45305
.. _45304: https://education.lego.com/en-us/products/wedo-2-0-motion-sensor/45304

.. |lego|  replace:: Lego\ |reg|
   

Credits
#######

* Virantha N. Ekanayake :gh_user:`virantha` - lead developer
* David Lechner :gh_user:`dlech` - contributor
   * Added Windows 10 support
   * Added support for Lego 88005 stand-alone LED peripheral

This project is also greatly indebted to the following persons, as well as their open-sourced libraries, portions of which have been incorporated into
BrickNil under the terms of their respective licenses:

* **Tony DiCola** for his Adafruit_Python_BluefruitLE_ library that provides the BluetoothLE communication stack on Mac OS X
* :gh_user:`Henrik Blidh <hbldh>` for his Bleak_ library that provided a pure python way to communicate with BluetoothLE over DBus on Linux.

.. _Bleak: https://github.com/hbldh/bleak
.. _Adafruit_Python_BluefruitLE: https://github.com/adafruit/Adafruit_Python_BluefruitLE


Disclaimer
##########

The software is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  Licensed under ASL 2.0


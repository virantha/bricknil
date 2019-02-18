BlueBrick - Control LEGO Bluetooth Sensors and Motors with Python
=================================================================

|image_pypi| |image_downloads| |image_license| |passing| |quality| |Coverage Status|

This library provides an easy way to connect to and program LEGO\ |reg|
Bluetooth hubs (including the newer 60197 and 60198 train sets) using Python on OS X and
Linux.  This work was inspired by this EuroBricks_ thread, and the NodeJS Powered-Up_
library.  It requires modern Python (designed and tested for 3.7) and uses asynchronous
event programming built on top of the Curio_ async library.  

* Free and open-source software: ASL2 license
* Blog: http://virantha.com/category/projects/bluebrick
* Documentation: http://virantha.github.io/bluebrick/html
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
* Fully supports Python asynchronous keywords and co-routines
* Allows expressive concurrent programming using async/await syntax
   * Uses the async library Curio_ by David Beazley
* Leverages the Adafruit Bluefruit BluetoothLE library
   * Supports Mac OS X (possibly the only BLE library in Python to support native CoreBluetooth access). 
   * Should also support Linux with BlueZ but currently not tested.


.. _Curio: http://curio.readthedocs.io
.. _EuroBricks: https://www.eurobricks.com/forum/index.php?/forums/topic/162288-powered-up-a-tear-down/
.. _Powered-Up: https://github.com/nathankellenicki/node-poweredup

Usage:
######

Here's a simple program that will let you control a PoweredUp train motor:

.. code-block:: python

   import pprint

   from curio import sleep
   from bluebrick import attach, start
   from bluebrick.hub import BoostHub
   from bluebrick.sensor import VisionSensor

   @attach(VisionSensor, name='vision_sensor', capabilities=['sense_distance'])
   class Robot(BoostHub):
       async def vision_sensor_change(self):
	   self.message(f'sensor change detected')

       async def run(self):
	   self.message("Running")
	   for i in range(2):
	       await sleep(5)
	   pprint.pprint(self.port_info)

   async def system():
       robot = Robot('vernie')

   if __name__ == '__main__':
       start(system)

Installation
############

.. code-block: bash

    $ pip install bluebrick

Disclaimer
##########

The software is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  Licensed under ASL 2.0

.. |image_pypi| image:: https://badge.fury.io/py/bluebrick.png
   :target: https://pypi.python.org/pypi/bluebrick
.. |image_downloads| image:: https://pypip.in/d/bluebrick/badge.png
   :target: https://crate.io/packages/bluebrick?version=latest
.. |image_license| image:: https://pypip.in/license/bluebrick/badge.png
.. |passing| image:: https://scrutinizer-ci.com/g/virantha/bluebrick/badges/build.png?b=master
.. |quality| image:: https://scrutinizer-ci.com/g/virantha/bluebrick/badges/quality-score.png?b=master
.. |Coverage Status| image:: https://coveralls.io/repos/virantha/bluebrick/badge.png?branch=develop
   :target: https://coveralls.io/r/virantha/bluebrick

.. |reg|    unicode:: U+000AE .. REGISTERED SIGN

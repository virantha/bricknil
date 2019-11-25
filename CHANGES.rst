0.9.3 - 11/25/19
---------------
- Support for Control+ devices by :gh_user:`dlech`
   - :class:`~bricknil.sensor.motor.CPlusXLMotor`
   - :class:`~bricknil.sensor.motor.CPlusLargeMotor`

0.9.2 - 5/7/19
---------------
- Fixed extraneous print statements

0.9.1 - 4/24/19
---------------
- Fixed regression in tachomotor position/rotation setting

0.9 - 4/5/19
------------
- Added support for Wedo sensors 
   - :class:`~bricknil.sensor.sensor.ExternalTiltSensor`
   - :class:`~bricknil.sensor.sensor.ExternalMotionSensor`
   - :class:`~bricknil.sensor.motor.WedoMotor`
- Refactored peripheral code into multiple files in `sensor/`
- Fixed a regression in port information querying

0.8.2 - 4/3/19
--------------
- Added support for Boost external motors (:class:`~bricknil.sensor.ExternalMotor`)
- Added positioning commands for External and Internal motors:
    - :meth:`~bricknil.peripheral.TachoMotor.set_pos` to set an absolute position in degrees on a clock-face
    - :meth:`~bricknil.peripheral.TachoMotor.rotate` to rotate a relative number of degrees

0.8.1 - 4/2/19
--------------
- Quick fix for :gh_issue:`3`. When instantiating a hub, use arg `ble_id` with either a UUID (mac) or BLE Network Address (Linux/Win) string

0.8 - 4/1/19
------------
- Added support for PoweredUp light module 88005 and Win10 (thanks to :gh_user:`dlech`)

0.7.2 - 3/26/19
---------------
- Added support for current and voltage sensors
- Fixed bug with hub buttons

0.7.1 - 3/25/19
---------------
- Rewrote message parsing structure to be more modular
   - Each message is separated out into its own class
   - State is now stored only in the dispatch and the hub, and not the message parsing
   - Peripheral value update is now handled safely as messages on the UniversalQueue going to the hub

0.7 - 3/22/19
-------------
- Changed hub matching to be more robust
   - Since the name can change, we now use the manufacturer data instead to match hubs
   - Tested using both Mac (adafruit) and Linux (bleak) libraries

0.6 - 3/21/19
-------------
- Added support for Duplo trains
   - Motor speed control and sensing
   - LED color
   - Vision sensor
   - Speaker sounds

v0.5.1 - 3/21/19 
-----------------
- Hotfix for issue with UUID

v0.5.0 - 3/18/19
----------------
- Fixed connecting to specific BTLE adapters based on network address

v0.4.0 - 2/28/19     
---------------------
- Added linux support with Bleak (and possibly Win10).  Tested on RPi

v0.3.0 - 2/26/19     
---------------------
- Changed name to BrickNil

v0.2.0 - 2/23/19     
---------------------
- Added support for PoweredUp Remote

v0.1.0 - 2/18/19     
---------------------
- First release

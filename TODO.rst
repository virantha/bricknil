Todo list
=========

High-level todos:

- Add py.test (this is difficult because of async coroutines.  need to figure out how to mock)
- Look into internal accel/decel profiles for the internal motors in the Boost Hub (since these have tacho/speed sensors)
- Document the system architecture
- Add in cleaner exit and hub shutdown code
- Add support for Wedo hubs
- Add ability to specify range of values when specifying capabilities (so we can handle negative numbers from sensor)

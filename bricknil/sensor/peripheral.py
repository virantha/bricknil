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

"""Base class for all sensors and motors

"""
import struct
from enum import Enum
from collections import namedtuple

from ..process import Process
from curio import sleep, spawn, current_task
from ..const import DEVICES


class Peripheral(Process):
    """Abstract base class for any Lego Boost/PoweredUp/WeDo peripherals

       A LEGO sensor can provide either a single_ sensing capability, or a combined_  mode where it returns multiple
       sensing values.  All the details can be found in the official protocol description.

       * **Single capability** - This is the easiest to handle:
            * Send a 0x41 Port Input Format Setup command to put the sensor port into the respective mode and activate updates
            * Read back the 0x45 Port Value(Single) messages with updates from the sensor on the respective mode
       * **Multiple capabilities** - This is more complicated because we need to put the sensor port into CombinedMode
            * Send a [0x42, port, 0x02] message to lock the port
            * Send multiple 0x41 messages to activate each capability/mode we want updates from
            * Send a [0x42, port, 0x01, ..] message with the following bytes:
                * 0x00 = Row entry 0 in the supported combination mode table
                    (hard-coded for simplicity here because LEGO seems to only use this entry most of the time)
                * For each mode/capability, send a byte like the following:
                    * Upper 4-bits is mode number
                    * Lower 4-bits is the dataset number
                    * For example, for getting RGB values, it's mode 6, and we want all three datasets 
                        (for each color), so we'd add three bytes [0x60, 0x61, 0x62].  
                        If you just wanted the Red value, you just append [0x60]
            * Send a [0x42, port, 0x03] message to unlock the port
            * Now, when the sensor sends back values, it uses 0x46 messages with the following byte sequence:
                * Port id
                * 16-bit entry where the true bits mark which mode has values included in this message
                    (So 0x00 0x05 means values from Modes 2 and 0)
                * Then the set of values from the sensor, which are ordered by Mode number 
                    (so the sensor reading from mode 0 would come before the reading from mode 2)
                * Each set of values includes however many bytes are needed to represent each dataset
                    (for example, up to 3 for RGB colors), and the byte-width of each value (4 bytes for a 32-bit int)


       .. _single: https://lego.github.io/lego-ble-wireless-protocol-docs/index.html#port-input-format-single
       .. _combined: https://lego.github.io/lego-ble-wireless-protocol-docs/index.html#port-input-format-combinedmode

       Args:
          capabilities : can be input in the following formats (where the
            number in the tuple can be a threshold to trigger updates)

               * ['sense_color', 'sense_distannce'] 
               * [capability.sense_color, capability.sense_distance]
               * [('sense_color', 1), ('sense_distance', 2)]

          name (str) : Human readable name
          port (int) : Port to connect to (otherwise will connect to first matching peripheral with defined sensor_id)
           

       Attributes:
            port (int) : Physical port on the hub this Peripheral attaches to
            sensor_name (str) : Name coming out of `const.DEVICES`
            value (dict) : Sensor readings get dumped into this dict
            message_handler (func) : Outgoing message queue to `BLEventQ` that's set by the Hub when an attach message is seen
            capabilites (list [ `capability` ]) : Support capabilities 
            thresholds (list [ int ]) : Integer list of thresholds for updates for each of the sensing capabilities

    """
    _DEFAULT_THRESHOLD = 1
    Dataset = namedtuple('Dataset', ['n', 'w', 'min', 'max'])

    def __init__(self, name, port=None, capabilities=[]):
        super().__init__(name)
        self.port = port
        self.sensor_name = DEVICES[self._sensor_id]
        self.value = None
        self.message_handler = None
        self.web_queue_output = None
        self.capabilities, self.thresholds = self._get_validated_capabilities(capabilities)

    def _get_validated_capabilities(self, caps):
        """Convert capabilities in different formats (string, tuple, etc)

           Returns:
                
                validated_caps, thresholds  (list[`capability`], list[int]): list of capabilities and list of associated thresholds
        """
        validated_caps = []
        thresholds = [1]*len(validated_caps)
        for cap in caps:
            # Capability can be a tuple of (cap, threshold)
            if isinstance(cap, tuple):
                cap, threshold = cap
                thresholds.append(threshold)
            else:
                thresholds.append(self._DEFAULT_THRESHOLD)

            if isinstance(cap, self.capability):
                # Make sure it's the write type of enumerated capability
                validated_caps.append(cap)
            elif type(cap) is str:
                # Make sure we can convert this string capability into a defined enum
                enum_cap = self.capability[cap]
                validated_caps.append(enum_cap)
        return validated_caps, thresholds

    def _convert_bytes(self, msg_bytes:bytearray, byte_count):
        """Convert bytearry into a set of values based on byte_count per value

           Args:
                msg_bytes (bytearray): Bytes to convert
                byte_count (int): How many bytes per value to use when computer (can be 1, 2, or 4)

           Returns:
                If a single value, then just that value
                If multiple values, then a list of those values
                Value can be either uint8, uint16, or uint32 depending on value of `byte_count`
        """
        if byte_count == 1:   # just a uint8
            val = msg_bytes[0]
        elif byte_count == 2: # uint16 little-endian
            val = struct.unpack('<H', msg_bytes)[0]
        elif byte_count == 4: # uint32 little-endian
            val = struct.unpack('<I', msg_bytes)[0]
        else:
            self.message_error(f'Cannot convert array of {msg_bytes} length {len(msg_bytes)} to python datatype')
            val = None
        return val

    async def _parse_combined_sensor_values(self, msg: bytearray):
        """
            Byte sequence is as follows:
                # uint16 where each set bit indicates data value from that mode is present 
                  (e.g. 0x00 0x05 means Mode 2 and Mode 0 data is present
                # The data from the lowest Mode number comes first in the subsequent bytes
                # Each Mode has a number of datasets associated with it (RGB for example is 3 datasets), and
                  a byte-width per dataset (RGB dataset is each a uint8)

            Args:
                msg (bytearray) : the sensor message

            Returns:
                None

            Side-effects:
                self.value
          
        """
        msg.pop(0)  # Remove the leading 0 (since we never have more than 7 datasets even with all the combo modes activated
        # The next byte is a bit mask of the mode/dataset entries present in this value
        modes = msg.pop(0)
        dataset_i = 0
        for cap in self.capabilities:  # This is the order we prgogramed the sensor
            n_datasets, byte_count = self.datasets[cap][0:2]
            for dataset in range(n_datasets):
                if modes & (1<<dataset_i):  # Check if i'th bit of mode is set
                    # Data corresponding to this dataset is present!
                    # Now, pop off however many bytes are associated with this
                    # dataset
                    data = msg[0:byte_count]
                    msg = msg[byte_count:]
                    val = self._convert_bytes(data, byte_count)
                    if n_datasets == 1:
                        self.value[cap] = val
                    else:
                        self.value[cap][dataset] = val
                dataset_i += 1



    async def send_message(self, msg, msg_bytes):
        """ Send outgoing message to BLEventQ """
        while not self.message_handler:
            await sleep(1)
        await self.message_handler(msg, msg_bytes, peripheral=self)

    def _convert_speed_to_val(self, speed):
        """Map speed of -100 to 100 to a byte range

            * -100 to 100 (negative means reverse)
            * 0 is floating
            * 127 is brake

            Returns:
                byte
        """
        if speed == 127: return 127
        if speed > 100: speed = 100
        if speed < 0: 
            # Now, truncate to 8-bits
            speed = speed & 255 # Or I guess I could do 256-abs(s)
        return speed


    async def set_output(self, mode, value):
        """Don't change this unless you're changing the way you do a Port Output command
        
           Outputs the following sequence to the sensor
            * 0x00 = hub id from common header
            * 0x81 = Port Output Command
            * port
            * 0x11 = Upper nibble (0=buffer, 1=immediate execution), Lower nibble (0=No ack, 1=command feedback)
            * 0x51 = WriteDirectModeData
            * mode
            * value(s)
        """
        b = [0x00, 0x81, self.port, 0x01, 0x51, mode, value ]
        await self.send_message(f'set output port:{self.port} mode: {mode} = {value}', b)

    # Use these for sensor readings
    async def update_value(self, msg_bytes):
        """ Message from message_dispatch will trigger Hub to call this to update a value from a sensor incoming message
            Depending on the number of capabilities enabled, we end up with different processing:

            If zero, then just set the `self.value` field to the raw message.

            If one, then:
                * Parse the single sensor message which may have multiple data items (like an RGB color value)
                * `self.value` dict entry for this capability becomes a list of these values

            If multiple, then:
                * Parse multiple sensor messages (could be any combination of the enabled modes)
                * Set each dict entry to `self.value` to either a list of multiple values or a single value

        """
        msg = bytearray(msg_bytes)
        if len(self.capabilities)==0:
            self.value = msg
        if len(self.capabilities)==1:
            capability = self.capabilities[0]
            datasets, bytes_per_dataset = self.datasets[capability][0:2]
            for i in range(datasets):
                msg_ptr = i*bytes_per_dataset
                val = self._convert_bytes(msg[msg_ptr: msg_ptr+bytes_per_dataset], bytes_per_dataset)
                if datasets==1:
                    self.value[capability] = val
                else:
                    self.value[capability][i] = val
        if len(self.capabilities) > 1:
            await self._parse_combined_sensor_values(msg)

    async def activate_updates(self):
        """ Send a message to the sensor to activate updates

            Called via an 'attach' message from
            :func:`bricknil.messages.Message.parse_attached_io` that triggers
            this call from :func:`bricknil.hub.Hub.peripheral_message_loop`

            See class description for explanation on how Combined Mode updates are done.
            
            Returns:
                None

        """
        
        assert self.port is not None, f"Cannot activate updates on sensor before it's been attached to {self.name}!"
        
        if len(self.capabilities) == 0: 
            # Nothing to do since no capabilities defined
            return

        self.value = {}
        for cap in self.capabilities:
            self.value[cap] = [None]*self.datasets[cap][0]

        if len(self.capabilities)==1:  # Just a normal single sensor
            mode = self.capabilities[0].value
            b = [0x00, 0x41, self.port, mode, self.thresholds[0], 0, 0, 0, 1]
            await self.send_message(f'Activate SENSOR: port {self.port}', b) 
        else:
            # Combo mode.  Need to make sure only allowed combinations are preset
            # Lock sensor
            b = [0x00, 0x42, self.port, 0x02]
            await self.send_message(f'Lock port {self.port}', b)

            for cap, threshold in zip(self.capabilities, self.thresholds):
                assert cap in self.allowed_combo, f'{cap} is not allowed to be sensed in combination with others'
                # Enable each capability
                b = [0x00, 0x41, self.port, cap.value, threshold, 0, 0, 0, 1]
                await self.send_message(f'enable mode {cap.value} on {self.port}', b)

            # Now, set the combination mode/dataset report order
            b = [0x00, 0x42, self.port, 0x01, 0x00]
            for cap in self.capabilities:
                # RGB requires 3 datasets
                datasets, byte_width = self.datasets[cap][0:2]
                for i in range(datasets):
                    b.append(16*cap.value+i)  # Mode is higher order nibble, dataset is lower order nibble
            await self.send_message(f'Set combo port {self.port}', b)

            # Unlock and start
            b = [0x00, 0x42, self.port, 0x03]
            await self.send_message(f'Activate SENSOR multi-update {self.port}', b)



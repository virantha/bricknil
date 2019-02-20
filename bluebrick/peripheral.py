import struct
from .process import Process
from curio import sleep
from .const import DEVICES


class Peripheral(Process):
    """ Abstract base class for any Lego Boost/PoweredUp/WeDo peripherals

        Attributes:

            port (int) : Physical port on the hub this Peripheral attaches to
            sensor_name (str) : Name coming out of `const.DEVICES`
            enabled (bool) : `True` when the Hub sends an attach message. For future use
            value (dict) : Sensor readings get dumped into this dict
            message_handler (func) : Outgoing message queue to `BLEventQ` that's set by the Hub when an attach message is seen
            capabilites (list [ `capability` ]) : Support capabilities 
            thresholds (list [ int ]) : Integer list of thresholds for updates for each of the sensing capabilities

    """
    _DEFAULT_THRESHOLD = 1
    def __init__(self, name, port=None, capabilities=[]):
        super().__init__(name)
        self.port = port
        self.sensor_name = DEVICES[self._sensor_id]
        self.enabled = False
        self.value = None
        self.message_handler = None
        self.capabilities, self.thresholds = self._get_validated_capabilities(capabilities)

    def _get_validated_capabilities(self, caps):
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

    def _parse_combined_sensor_values(self, msg: bytearray):
        msg.pop(0)  # Remove the leading 0 (since we never have more than 7 datasets even with all the combo modes activated
        # The next byte is a bit mask of the mode/dataset entries present in this value
        modes = msg.pop(0)
        dataset_i = 0
        for cap in self.capabilities:  # This is the order we prgogramed the sensor
            n_datasets, byte_count = self.datasets[cap]
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
        await self.message_handler(msg, msg_bytes)

    # Use this for motors and leds
    def _convert_speed_to_val(self, speed):
        # -100 to 100 (negative means reverse)
        # 0 is floating
        # 127 is brake
        if speed == 127: return 127
        if speed > 100: speed = 100
        if speed < 0: 
            # Now, truncate to 8-bits
            speed = speed & 255 # Or I guess I could do 256-abs(s)
        return speed


    async def set_output(self, mode, value):
        """Don't change this unless you're changing the way you do a Port Output command"""
        b = [0x00, 0x81, self.port, 0x11, 0x51, mode, value ]
        await self.send_message('set output', b)


    # Use these for sensor readings
    def update_value(self, msg_bytes):
        """ Callback from message parser to update a value from a sensor incoming message """
        msg = bytearray(msg_bytes)
        if len(self.capabilities)==0:
            self.value = msg
        if len(self.capabilities)==1:
            capability = self.capabilities[0]
            datasets, bytes_per_dataset = self.datasets[capability]
            for i in range(datasets):
                msg_ptr = i*bytes_per_dataset
                val = self._convert_bytes(msg[msg_ptr: msg_ptr+bytes_per_dataset], bytes_per_dataset)
                if datasets==1:
                    self.value[capability] = val
                else:
                    self.value[capability][i] = val
        if len(self.capabilities) > 1:
            self._parse_combined_sensor_values(msg)

    async def activate_updates(self):
        """ Send a message to the sensor to activate updates"""
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
                datasets, byte_width = self.datasets[cap]
                for i in range(datasets):
                    b.append(16*cap.value+i)  # Mode is higher order nibble, dataset is lower order nibble
            await self.send_message(f'Set combo port {self.port}', b)

            # Unlock and start
            b = [0x00, 0x42, self.port, 0x03]
            await self.send_message(f'Activate SENSOR multi-update {self.port}', b)




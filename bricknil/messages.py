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
"""Message parsers for each message type

"""
import struct, logging
from .const import DEVICES

logger = logging.getLogger(__name__)
class UnknownMessageError(Exception): pass

class Message:
    """Base class for each message parser.

       This class instance keeps track of each subclass and stores an object of
       each subclass in the attribue `parsers`.  None of these subclass instances
       should ever store any instance data since these are shared across multiple
       hubs.

       Attributes:
            parsers (dict) : msg_type (int) -> Message parser
            msg_type(int)  : msg_type of each subclassed message
    """

    parsers = {}

    def __init_subclass__(cls):
        """Register message subclasses"""
        logger.debug(f"registering {cls}")
        assert cls.msg_type not in Message.parsers, f'Duplicate Message parser type {cls.msg_type} found in code!'
        Message.parsers[cls.msg_type] = cls()

    def _parse_msg_bytes(self, msg_bytes):
        hex_bytes = ':'.join(hex(c) for c in msg_bytes)
        return hex_bytes

    def parse(self, msg_bytes, l, dispatcher):
        """Implement this handle parsing of each message body type.

           Args:
               msg_bytes (bytearray): Message body
               l (list):  text description of what's being parsed for logging (just append details as you go along)
               dispatcher (:class:`bricknil.message_dispatch.MessageDispatch`):  The dispatch object that is sending messages. 
                   Call back into its methods to send messages back to the hub.
        """
        pass

class PortValueMessage(Message):
    """Single value update from a sensor
    """
    msg_type = 0x45

    def parse(self, msg_bytes, l, dispatcher):
        port = msg_bytes.pop(0)
        dispatcher.message_update_value_to_peripheral(port,  msg_bytes)
        l.append(f'Port {port} changed value to {msg_bytes}')

class PortComboValueMessage(Message):
    """Multiple (combination) value updates from different modes of a sensor
    """
    msg_type = 0x46

    def parse(self, msg_bytes, l, dispatcher):
        port = msg_bytes.pop(0)
        dispatcher.message_update_value_to_peripheral(port,  msg_bytes)
        l.append(f'Port {port} changed combo value to {msg_bytes}')

class HubPropertiesMessage(Message):
    """Used to get data on the hub as well as button press information on the hub
    """
    msg_type = 0x01
    prop_names = {  0x01: 'Advertising Name',
                    0x02: 'Button',
                    0x03: 'FW Version',
                    0x04: 'HW Version',
                    0x05: 'RSSI',
                    0x06: 'Battery Voltage',
                    0x07: 'Battery Type',
                    0x08: 'Manufacturer Name',
                    0x09: 'Radio FW Version',
                    0x0A: 'LEGO Wireles Protocol Version',
                    0x0B: 'System Type ID',
                    0x0C: 'HW Network ID', 
                    0x0D: 'Primary MAC address',
                    0x0E: 'Seconary MAC address',
                    0X0F: 'HW Network Family',
                    }
    operation_names = { 0x01: 'Set (downstream)',
                        0x02: 'Enable Updates (Downstream)',
                        0x03: 'Disable Updates (Downstream)',
                        0x04: 'Reset (Downstream)',
                        0x05: 'Request Update (Downstream)',
                        0x06: 'Update (Upstream)',
                        }
    def parse(self, msg_bytes, l, dispatcher):
        l.append('Hub property: ')

        prop = msg_bytes.pop(0)
        if prop not in self.prop_names:
            raise UnknownMessageError
        l.append(self.prop_names[prop])

        op = msg_bytes.pop(0)
        if op not in self.operation_names:
            raise UnknownMessageError
        l.append(self.operation_names[op])

        # Now, just append the number 
        l.append(self._parse_msg_bytes(msg_bytes))

        # Now forward any button presses as if it were a "port value" change
        if prop==0x02 and op == 0x06:  # Button and update op
            msg_bytes.insert(0, 0xFF)  # Insert Dummy port value of 255
            Message.parsers[PortValueMessage.msg_type].parse(msg_bytes, l, dispatcher)

class PortInformationMessage(Message):
    """Information on what modes are supported on a port and whether a port
       is input/output.
    """
    msg_type = 0x43

    def _parse_mode_info(self, msg_bytes, l, port_info):
        l.append(' INFO:')
        capabilities = msg_bytes.pop(0)
        bitmask = ['output', 'input', 'combinable', 'synchronizable']
        for i, attr in enumerate(bitmask):
            port_info[attr] = capabilities & 1<<i
            if port_info[attr]: l.append(attr[:3])
        
    def _parse_mode_info_input_output(self, msg_bytes, l, modes_info):
        input_modes = msg_bytes.pop(0) + msg_bytes.pop(0)*256
        output_modes = msg_bytes.pop(0) + msg_bytes.pop(0)*256
        for i in range(16):
            if input_modes & (1<<i):
                l.append(i)
                mode_info = modes_info.setdefault(i, {})
                mode_info['input'] = True
        l.append(', output: ')
        for i in range(16):
            if output_modes & (1<<i):
                l.append(i)
                mode_info = modes_info.setdefault(i, {})
                mode_info['output'] = True

    def _parse_combination_info(self, msg_bytes, l, port_info):
        port_info['mode_combinations'] = []
        
        mode_combo = msg_bytes.pop(0) + msg_bytes.pop(0)*256
        l.append('Combinations:')
        while mode_combo != 0:
            cmodes = []
            for i in range(16):
                if mode_combo & (1<<i):
                    cmodes.append(i)
            l.append('+'.join([f'Mode {m}' for m in cmodes]))
            port_info['mode_combinations'].append(cmodes)
            if len(msg_bytes) == 0:
                mode_combo = 0
            else:
                mode_combo = msg_bytes.pop(0) + msg_bytes.pop(0)*256
                l.append(', ')
        
    def parse(self, msg_bytes, l, dispatcher):
        port = msg_bytes.pop(0)
        mode = msg_bytes.pop(0)
        l.append(f'Port {port} Mode {mode}:')

        port_info = dispatcher.port_info.setdefault(port, {})
        modes_info = port_info.setdefault('modes', {})
        if mode == 0x01: # MODE INFO
            self._parse_mode_info(msg_bytes, l, port_info)
            nModes = msg_bytes.pop(0)
            l.append(f'nModes:{nModes}, input:')
            self._parse_mode_info_input_output(msg_bytes, l, modes_info)
            dispatcher.message_port_info_to_peripheral(port, 'port_info_received')
        elif mode == 0x02: # Combination info
            self._parse_combination_info(msg_bytes, l, port_info)
            dispatcher.message_port_info_to_peripheral(port, 'port_combination_info_received')
        else:
            raise UnknownMessageError

class PortOutputFeedbackMessage(Message):
    """Ack messages/error messages sent in response to a command being issued to the hub
    """
    msg_type = 0x82

    def parse(self, msg_bytes, l, dispatcher):
        port = msg_bytes.pop(0)
        l.append(f'Command feedback: Port {port}')
        feedback = msg_bytes.pop(0)
        if feedback & 1:
            l.append('Buffer empty, Command in progess')
        if feedback & 2:
            l.append('Buffer empty, Command completed')
        if feedback & 8:
            l.append(': Idle ')
        if feedback & 4:
            l.append(': Command discarded')
        if feedback & 16: 
            l.append(': Busy/Full')

class PortModeInformationMessage(Message):
    """Information on a specific mode

       This tells us a mode's name, what numeric format it uses, and it's range.
    """
    msg_type = 0x44
    def parse(self, msg_bytes, l, dispatcher):
        port = msg_bytes.pop(0)
        mode = msg_bytes.pop(0)
        mode_type = msg_bytes.pop(0)

        port_info = dispatcher.port_info.setdefault(port, {})
        modes_info = port_info.setdefault('modes', {})
        mode_info = modes_info.setdefault(mode, {})

        l.append(f'MODE INFO Port:{port} Mode:{mode}')
        mode_types = { 0: self._parse_name,
                       0x1: self._parse_raw_range,
                       0x2: self._parse_pct_range,
                       0x3: self._parse_si_range,
                       0x4: self._parse_symbol,
                       0x5: self._parse_mapping,
                       0x80: self._parse_format,
                     }
        if mode_type in mode_types:
            mode_types[mode_type](msg_bytes, l, mode_info)
        else:
            raise UnknownMessageError
        dispatcher.message_port_info_to_peripheral(port, 'port_mode_info_received')


    def _parse_format(self, msg_bytes, l, mode_info):
        # 4 bytes
        # [0] = Number of datasets (e.g. RBG has 3 for each color)
        # [1] = Dataset type.  00-byte, 01=16b, 10=32b, 11=float
        # [2] = Total figures
        # [3] = Decimals if any
        mode_info['datasets'] = msg_bytes.pop(0)
        dataset_types = ['8b', '16b', '32b', 'float']
        mode_info['dataset_type'] = dataset_types[msg_bytes.pop(0)]
        mode_info['dataset_total_figures'] = msg_bytes.pop(0)
        mode_info['dataset_decimals'] = msg_bytes.pop(0)

    def _parse_mapping(self, msg_bytes, l, mode_info):
        l.append('Input Mapping:')
        bits = ['NA', 'NA', 'Discrete', 'Relative', 'Absolute', 'NA', 'Supports Functional Mapping 2.0}', 'Supports NULL']
        # First byte is bit-mask of input details
        mask = msg_bytes[0]
        maps = [ bits[i]  for i in range(8) if (mask>>i) & 1]
        l.append(','.join(maps))
        mode_info['input_mapping'] = maps

        l.append('Output Mapping:')
        mask = msg_bytes[1]
        maps = [ bits[i]  for i in range(8) if (mask>>i)&1]
        l.append(','.join(maps))
        mode_info['output_mapping'] = maps

    def _parse_symbol(self, msg_bytes, l, mode_info):
        l.append('Symbol:')
        symbol = ''.join( [chr(b) for b in msg_bytes if b!=0])
        l.append(symbol)
        mode_info['symbol'] =symbol

    def _unpack_float(self, b):
        return struct.unpack('<f', bytearray(b[0:4]))

    def _parse_si_range(self, msg_bytes, l, mode_info):
        l.append('SI range:')
        mn = self._unpack_float(msg_bytes[0:4])[0]
        mx = self._unpack_float(msg_bytes[4:])[0]
        l.append(f'{mn} to {mx}')
        mode_info['si_range'] = (mn, mx)

    def _parse_pct_range(self, msg_bytes, l, mode_info):
        l.append('Pct range:')
        b_array = bytearray(msg_bytes)
        pct_min = struct.unpack('<f', b_array[0:4])[0]
        pct_max = struct.unpack('<f', b_array[4:])[0]
        l.append(f'{pct_min} to {pct_max}')
        mode_info['pct_range'] = (pct_min, pct_max)

    def _parse_raw_range(self, msg_bytes, l, mode_info):
        l.append('Raw range:')
        b_array = bytearray(msg_bytes)
        raw_min = struct.unpack('<f', b_array[0:4])[0]
        raw_max = struct.unpack('<f', b_array[4:])[0]
        l.append(f'{raw_min} to {raw_max}')
        mode_info['raw_range'] = (raw_min, raw_max)

    def _parse_name(self, msg_bytes, l, mode_info):
        l.append('Name:')
        name = ''.join( [chr(b) for b in msg_bytes if b!=0])
        l.append(name)
        mode_info['name'] = name

class AttachedIOMessage(Message):
    """Peripheral attach and detach message
    """
    msg_type = 0x04

    def parse(self, msg_bytes, l, dispatcher):
        # 5-bytes = detached
        # 15 bytes = attached
        # 9 bytes = virtual attached
        # Subtract 3 bytes for what we've already popped off
        port = msg_bytes.pop(0)
        event = msg_bytes.pop(0)
        detach, attach, virtual_attach = [event==x  for x in range(3)]
        if detach:
            l.append(f'Detached IO Port:{port}')
            return
        elif attach:
            l.append(f'Attached IO Port:{port}')
        elif virtual_attach:
            l.append(f'Attached VirtualIO Port:{port}')

        if attach or virtual_attach:
            # Next two bytes (little-endian) is the device number (MSB is not used)
            device_id = msg_bytes.pop(0)
            assert device_id in DEVICES, f'Unknown device with id {device_id} being attached (port {port}'
            device_name = DEVICES[device_id]
            self._add_port_info(dispatcher,port, 'id', device_id)
            self._add_port_info(dispatcher,port, 'name', device_name)

            msg_bytes.pop(0) # pop off MSB that's always 0 
            l.append(f'{device_name}')

            # register the handler for this IO
            dispatcher.message_attach_to_hub(device_name, port)

        if attach:
            for ver_type in ['HW', 'SW']:
                # NExt few bytes are fw versions
                build0 = hex(msg_bytes.pop(0))
                build1 = hex(msg_bytes.pop(0))
                bugfix = hex(msg_bytes.pop(0))
                ver = hex(msg_bytes.pop(0))
                l.append(f'{ver_type}:{ver}.{bugfix}.{build1}{build0}')

        if virtual_attach:
            assert len(msg_bytes) == 2
            port0, port1 = msg_bytes
            l.append(f'Port A: {port0}, Port B: {port1}')
            self._add_port_info(dispatcher, port, 'virtual', (port0, port1))

    def _add_port_info(self, dispatcher, port, info_key, info_val):
        port_info_item = dispatcher.port_info.get(port, {})
        port_info_item[info_key] = info_val
        dispatcher.port_info[port] = port_info_item


if __name__ == '__main__':
    from mock import MagicMock
    hub = MagicMock()
    dis = MessageDispatch(hub)
    dis.port_to_peripheral[1] = MagicMock()

    msg = bytearray([0,0,0x45,1,9,9,9])
    l = dis.parse(msg)
    print(l)

    msg = bytearray([0,0,0x46,1,9,9,9])
    l = dis.parse(msg)
    print(l)

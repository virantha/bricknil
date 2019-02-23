"""Message parser for parsing incoming messages from a Hub

   Called exclusively by the method :func:`bricknil.ble_queue.BLEventQ.get_message` that is the callback
   running inside the Adafruit_BluefruitLE library thread.

   All communication to the event system in Curio-land should happen through the UniversalQueue instance
   to ensure thread safety.  However, for now, value updates happen through a direct method call into
   the :func:`bricknil.peripheral.Peripheral.update_value` method of a peripheral instance.  We may want
   to change to go through the peripheral_queue in the future.

   TODO: change msg_bytes to use a Deque instead of a list for faster pop(0) operations

"""
from .const import DEVICES

class UnknownMessageError(Exception):
    pass

class Message:
    """ Each hub has its own Message parser instance

        Attributes:
            hub (:class:`bricknil.hub.Hub`): hub subclass this is sending messages to be parsed
            handlers (dict(port => peripheral)): dict of peripherals for each port
            port_info (dict (port => port_info)): dict containing all the port/mode information
    """

    def __init__(self, hub):
        self.hub = hub
        self.handlers = {}
        self.port_info = {}

    def parse(self, msg:bytearray):
        """Main parse method called by bluetooth event queur
           
           Args:
                msg (bytearray) : The raw message bytes
        """
        # Remove the first byte that is the legnth
        # Remove the second byte that is the hub id
        msg_bytes = list(msg)
        msg_bytes = msg_bytes[2:]

        msg_type = msg_bytes.pop(0)
        l = []  # keep track of the parsed return message
        try:
            if msg_type == 0x01: # Hub properties
                l = self.parse_hub_properties(msg_bytes, l)
            elif msg_type == 0x04: # Attached or detached I/O
                l = self.parse_attached_io(msg_bytes, l)
            elif msg_type == 0x43: # Port information
                l = self.parse_port_information(msg_bytes, l)
            elif msg_type == 0x44: # Port Mode information
                l = self.parse_port_mode_information(msg_bytes, l)
            elif msg_type == 0x45: # Port Single Value
                l = self.parse_port_value(msg_bytes, l)
            elif msg_type == 0x46: # Port Combo Value
                l = self.parse_port_combo_value(msg_bytes, l)
            elif msg_type == 0x82: # Port output command feedback (messages from hub after a command is issued)
                l = self.parse_port_output_feedback(msg_bytes, l)

            else:
                raise UnknownMessageError
        except UnknownMessageError:
            l.append(self._parse_msg_bytes(msg))

        return ' '.join([str(x) for x in l])

    def _parse_msg_bytes(self, msg_bytes):
        hex_bytes = ':'.join(hex(c) for c in msg_bytes)
        return hex_bytes

    def parse_port_value(self, msg_bytes, l):
        port = msg_bytes.pop(0)

        if port in self.handlers:
            sensor = self.handlers[port]
            sensor.update_value(msg_bytes)
            l.append(f'Port {port} changed value to {sensor.value}')
            self.hub.peripheral_queue.put((sensor, 'value_change'))
            return l
        else:
            raise UnknownMessageError

    def parse_port_combo_value(self, msg_bytes, l):
        port = msg_bytes.pop(0)

        if port in self.handlers:
            sensor = self.handlers[port]
            sensor.update_value(msg_bytes)
            l.append(f'Port {port} changed combo value to {sensor.value}')
            self.hub.peripheral_queue.put((sensor, 'value_change'))
            return l
        else:
            raise UnknownMessageError

    def parse_port_information(self, msg_bytes, l):
        port_info = {}  # Store all the information on this port
        port = msg_bytes.pop(0)
        mode = msg_bytes.pop(0)
        l.append(f'Port {port} Mode {mode}:')

        port_info = self.port_info.setdefault(port, {})
        modes_info = port_info.setdefault('modes', {})

        
        if mode == 0x01:  # MODE INFO
            l.append(' INFO:')
            capabilities = msg_bytes.pop(0)
            if capabilities & 1<<3:
                l.append('sync')
                port_info['synchronizable'] = True
            if capabilities & 1<<2:
                l.append('comb')
                port_info['combinable'] = True
            if capabilities & 1<<1:
                l.append('input')
                port_info['input'] = True
            if capabilities & 1<<0:
                l.append('output')
                port_info['output'] = True
            nModes = msg_bytes.pop(0)
            l.append(f'nModes:{nModes}, input:')
            input_modes = msg_bytes.pop(0) + msg_bytes.pop(0)*256
            for i in range(16):
                if input_modes & (1<<i):
                    l.append(i)
                    mode_info = modes_info.setdefault(i, {})
                    mode_info['input'] = True
            output_modes = msg_bytes.pop(0) + msg_bytes.pop(0)*256
            l.append(', output(): ')
            for i in range(16):
                if output_modes & (1<<i):
                    l.append(i)
                    mode_info = modes_info.setdefault(i, {})
                    mode_info['output'] = True
            self.hub.peripheral_queue.put( ((port, self.port_info[port]), 'update_port'))
            self.hub.peripheral_queue.put( (port, 'port_info_received'))
        elif mode == 0x02: # Combination info
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
            self.hub.peripheral_queue.put( ((port, self.port_info[port]), 'update_port'))

        return l


    def parse_port_mode_information(self, msg_bytes, l):
        port = msg_bytes.pop(0)
        mode = msg_bytes.pop(0)
        mode_type = msg_bytes.pop(0)

        port_info = self.port_info.setdefault(port, {})
        modes_info = port_info.setdefault('modes', {})
        mode_info = modes_info.setdefault(mode, {})

        l.append(f'MODE INFO Port:{port} Mode:{mode}')
        if mode_type == 0: # Name of mode
            l.append('Name:')
            name = ''.join( [chr(b) for b in msg_bytes if b!=0])
            l.append(name)
            mode_info['name'] = name
        elif mode_type ==0x80:  # Value format of modej
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

        else:
            raise UnknownMessageError
        self.hub.peripheral_queue.put( ((port, self.port_info[port]), 'update_port'))
        return l

    def parse_port_output_feedback(self, msg_bytes, l):
        port = msg_bytes.pop(0)
        l.append(f'Command feedback: Port {port}')
        feedback = msg_bytes.pop(0)
        if feedback & 1:
            l.append('Buffer empty, Command in progess')
        if feedback & 2:
            l.append('Buffer empty, Command completed')
        if feedback & 4:
            l.append('Command discarded')
        if feedback & 8:
            l.append('Idle')
        if feedback & 16: 
            l.append('Busy/Full')
        return l

    def _get_hub_registerd_device(self, device_name, port):
        for peripheral_name, peripheral in self.hub.peripherals.items():
            if peripheral.port == port:
                assert device_name == peripheral.sensor_name
                return peripheral
        # No matching port name, so let's just search for the name and assign the port
        for peripheral_name, peripheral in self.hub.peripherals.items():
            if peripheral.sensor_name == device_name and peripheral.port == None:
                peripheral.message(f"ASSIGNING PORT {port} on {peripheral.name}")
                peripheral.port = port
                return peripheral
        return None



    def _add_port_info(self, port, info_key, info_val):
        port_info_item = self.port_info.get(port, {})
        port_info_item[info_key] = info_val
        self.port_info[port] = port_info_item


    def parse_attached_io(self, msg_bytes, l):
        # 5-bytes = detached
        # 15 bytes = attached
        # 9 bytes = virtual attached
        # Subtract 3 bytes for what we've already popped off
        port = msg_bytes.pop(0)
        event = msg_bytes.pop(0)
        detach, attach, virtual_attach = [event==x  for x in range(3)]
        if detach:
            l.append(f'Detached IO Port:{port}')
        elif attach:
            l.append(f'Attached IO Port:{port}')
        elif virtual_attach:
            l.append(f'Attached VirtualIO Port:{port}')

        if attach or virtual_attach:
            # Next two bytes (little-endian) is the device number (MSB is not used)
            device_id = msg_bytes.pop(0)
            assert device_id in DEVICES, f'Unknown device with id {device_id} being attached (port {port}'
            device_name = DEVICES[device_id]
            self._add_port_info(port, 'id', device_id)
            self._add_port_info(port, 'name', device_name)

            msg_bytes.pop(0) # pop off MSB that's always 0 
            l.append(f'{device_name}')

            # Send a message saying this port is detected, in case the hub
            # wants to query for more properties
            self.hub.peripheral_queue.put( (port, 'port_detected'))

            # register the handler for this IO
            #  - Check the hub to see if there's a matching device or port
            peripheral = self._get_hub_registerd_device(device_name, port)
            if peripheral:
                self.handlers[port] = peripheral
                l.append(f':Attached to handler:')
                # Now, we should activate updates from this sensor
                self.hub.peripheral_queue.put( (peripheral, 'attach'))
            self.hub.peripheral_queue.put( ((port, self.port_info[port]), 'update_port'))

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
            self._add_port_info(port, 'virtual', (port0, port1))

        return l


    def parse_hub_properties(self, msg_bytes, l):
        l.append('Hub property: ')
        prop = msg_bytes.pop(0)
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
        if prop not in prop_names.keys():
            raise UnknownMessageError
        else:
            l.append(prop_names[prop])

        operation_names = { 0x01: 'Set (downstream)',
                            0x02: 'Enable Updates (Downstream)',
                            0x03: 'Disable Updates (Downstream)',
                            0x04: 'Reset (Downstream)',
                            0x05: 'Request Update (Downstream)',
                            0x06: 'Update (Downstream)',
                            }
        op = msg_bytes.pop(0)
        if op not in operation_names.keys():
            raise UnknownMessageError

        l.append(operation_names[op])

        # Now, just append the number 
        l.append(self._parse_msg_bytes(msg_bytes))

        # Now forward any button presses as if it were a "port value" change
        if prop==0x02 and op == 0x06:  # Button and update op
            msg_bytes.insert(0, 0xFF)  # Insert Dummy port value of 255
            self.parse_port_value(msg_bytes, l)

        return l





import pytest
import os, struct, copy
import logging

from mock import Mock
from mock import patch, call
from mock import MagicMock
from mock import PropertyMock

from hypothesis import given, example, settings
from hypothesis import strategies as st

from bricknil.message_dispatch import MessageDispatch
from bricknil.messages import UnknownMessageError, HubPropertiesMessage
from bricknil.const import DEVICES

class TestMessages:

    def setup(self):
        # Create the main dispatch
        self.hub = MagicMock()
        self.m = MessageDispatch(self.hub)
    
    def _with_header(self, msg:bytearray):
        l = len(msg)+2
        assert l<127
        return bytearray([l, 0]+list(msg))

    @given(st.data())
    def test_port_value_message(self, data):
        port = data.draw(st.integers(0,255))
        width = data.draw(st.integers(1,3))
        nbytes = 1<<(width-1)
        values = data.draw(st.lists(st.integers(0,255),min_size=nbytes,max_size=nbytes ))
        msg_type = 0x45
        msg = bytearray([msg_type, port]+values)
        l = self.m.parse(self._with_header(msg))
        self.hub.peripheral_queue.put.assert_called_with(('value_change', (port,values)))

    @given(port=st.integers(0,255),
           mode_ptr=st.integers(0, 0xffff),
           mode_data=st.lists(st.integers(0,255), min_size=1, max_size=100),
    ) 
    def test_port_combo_value_message(self, port, mode_ptr, mode_data):
        msg_type = 0x46
        mptr = struct.pack('H', mode_ptr)
        msg = bytearray([msg_type, int(port)])+mptr+bytearray(mode_data)
        l = self.m.parse(self._with_header(msg))
        assert l==f'Port {port} changed combo value to {list(msg[2:])}'
        self.hub.peripheral_queue.put.assert_called_with(('value_change', (port,list(msg[2:]))))

    @given(prop=st.integers(0,255),
           op = st.integers(0,255),
           msg_data=st.lists(st.integers(0,255), min_size=1, max_size=100),
    )
    @example(prop=0, op=1, msg_data=[0])
    @example(prop=0, op=0, msg_data=[0])
    @example(prop=2, op=6, msg_data=[0])
    def test_hub_properties_message(self, prop, op, msg_data):
        msg_type = 0x01
        msg = bytearray([msg_type, prop, op]+msg_data)
        msg = self._with_header(msg)
        msg_original = self.m._parse_msg_bytes(list(msg))

        if prop not in list(range(1,16)):
            l = self.m.parse(msg)
            assert l == f'Hub property:  {msg_original}'
        else:
            if op not in list(range(1,7)):
                l = self.m.parse(msg)
                assert l == f'Hub property:  {HubPropertiesMessage.prop_names[prop]} {msg_original}'
            else:
                l = self.m.parse(msg)
                remaining = self.m._parse_msg_bytes(list(msg[5:]))
                if prop==0x02 and op==0x06:
                    self.hub.peripheral_queue.put.assert_called_with(('value_change', (255,list(msg[5:]))))
                else:
                    assert l == f'Hub property:  {HubPropertiesMessage.prop_names[prop]} {HubPropertiesMessage.operation_names[op]} {remaining}'


    @given( event=st.integers(0,2),
            port=st.integers(0,255),
            data=st.data()
    )
    def test_attach_message(self, data, port, event):
        msg_type = 0x04
        msg = bytearray([msg_type, port, event])
        if event == 0: #detach
            l = self.m.parse(self._with_header(msg))
            assert l == f'Detached IO Port:{port}'
        elif event == 1: #attach
            # Need 10 bytes
            #dev_id = data.draw(st.integers(0,255))
            dev_id = data.draw(st.sampled_from(sorted(DEVICES.keys())))
            fw_version = data.draw(st.lists(st.integers(0,255), min_size=8, max_size=8))
            msg = msg + bytearray([dev_id, 0])+ bytearray(fw_version)
            l = self.m.parse(self._with_header(msg))
            self.hub.peripheral_queue.put.assert_any_call(('update_port', (port, self.m.port_info[port])))
            self.hub.peripheral_queue.put.assert_any_call(('port_detected', port))
            # ALso need to make sure the port info is added to dispatch
            assert self.m.port_info[port]['name'] == DEVICES[dev_id]
        elif event == 2: # virtual attach
            dev_id = data.draw(st.sampled_from(sorted(DEVICES.keys())))
            v_port_a = data.draw(st.integers(0,255))
            v_port_b = data.draw(st.integers(0,255))
            msg = msg + bytearray([dev_id, 0, v_port_a, v_port_b])
            l = self.m.parse(self._with_header(msg))
            self.hub.peripheral_queue.put.assert_any_call(('update_port', (port, self.m.port_info[port])))
            self.hub.peripheral_queue.put.assert_any_call(('port_detected', port))
            assert l == f'Attached VirtualIO Port:{port} {self.m.port_info[port]["name"]} Port A: {v_port_a}, Port B: {v_port_b}'
            assert self.m.port_info[port]['virtual'] == (v_port_a, v_port_b)
            assert self.m.port_info[port]['name'] == DEVICES[dev_id]

    @given( mode = st.integers(1,2),
            port = st.integers(0,255),
            data = st.data()
           )
    def test_port_information_message(self, data, port, mode):
        msg_type = 0x43
        if mode == 1:
            capabilities = data.draw(st.integers(0,15)) # bit mask of 4 bits
            nmodes = data.draw(st.integers(0,255))
            input_modes = [data.draw(st.integers(0,255)), data.draw(st.integers(0,255))]
            output_modes = [data.draw(st.integers(0,255)), data.draw(st.integers(0,255))]
            msg = bytearray([msg_type, port, mode, capabilities, nmodes]+input_modes+output_modes)
            l = self.m.parse(self._with_header(msg))

            self.hub.peripheral_queue.put.assert_any_call(('update_port', (port, self.m.port_info[port])))
            self.hub.peripheral_queue.put.assert_any_call(('port_info_received', port))

            # Make sure the proper capabilities have been set
            bitmask = ['output', 'input', 'combinable', 'synchronizable'] # capabilities
            for i,cap in enumerate(bitmask):
                assert self.m.port_info[port][cap] == capabilities & (1<<i)
            
            for i in range(8):
                if input_modes[0] & (1<<i):
                    assert self.m.port_info[port]['modes'][i]['input']
                if input_modes[1] & (1<<i):
                    assert self.m.port_info[port]['modes'][i+8]['input']
                if output_modes[0] & (1<<i):
                    assert self.m.port_info[port]['modes'][i]['output']
                if output_modes[1] & (1<<i):
                    assert self.m.port_info[port]['modes'][i+8]['output']
                    
        elif mode == 2:
            # Combination info
            # Up to 8x 16-bit words (bitmasks) of combinations possible
            ncombos = data.draw(st.integers(0,6))  # how many combos should we allow
            combos = data.draw(st.lists(st.integers(0,255), min_size=ncombos*2, max_size=ncombos*2))
            msg = bytearray([msg_type, port, mode]+combos+[0,0])
            l = self.m.parse(self._with_header(msg))

            self.hub.peripheral_queue.put.assert_any_call(('update_port', (port, self.m.port_info[port])))
            self.hub.peripheral_queue.put.assert_any_call(('port_combination_info_received', port))

            # Assert number of combos
            #assert len(combos)/2 == len(self.m.port_info[port]['mode_combinations'])

    @given(feedback=st.integers(0,32),
           port=st.integers(0,255)
    )
    def test_port_output_feedback_message(self, port, feedback):
        msg_type = 0x82
        msg = bytearray([msg_type, port, feedback])
        self.m.parse(self._with_header(msg))
        
    @given(mode_type=st.sampled_from([0,1,2,3,4,5, 0x80]),#([0,1,2,3,4,5,0x80]),
           mode=st.integers(0,255),
           port=st.integers(0,255),
           data=st.data()
    )
    @settings(deadline=None)
    def test_port_mode_info_message(self, port, mode, mode_type, data):
        msg_type = 0x44

        if mode_type == 0:
            name = data.draw(st.text(min_size=1, max_size=11))
            payload = bytearray(name.encode('utf-8'))
        elif mode_type == 1 or mode_type == 2 or mode_type==3:
            payload = data.draw(st.lists(st.integers(0,255), min_size=8, max_size=8))
            payload = bytearray(payload)
        elif mode_type == 4:
            name = data.draw(st.text(min_size=1, max_size=5))
            payload = bytearray(name.encode('utf-8'))
        elif mode_type == 5:
            payload = data.draw(st.lists(st.integers(0,255), min_size=2, max_size=2))
            payload = bytearray(payload)
        elif mode_type == 0x80:
            ndatasets = data.draw(st.integers(0,255))
            dataset_type = data.draw(st.integers(0,3))
            total_figures = data.draw(st.integers(0,255))
            decimals = data.draw(st.integers(0,255))
            payload = bytearray([ndatasets, dataset_type, total_figures, decimals])
            pass
        else:
            assert False

        msg = bytearray([msg_type, port, mode, mode_type]) + payload
        self.m.parse(self._with_header(msg))
            







            



    
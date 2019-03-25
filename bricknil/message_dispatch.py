"""Parse incoming BLE Lego messages from hubs

Each hub has one of these objects to control access to the underlying BLE library notification thread.
Communication back into the hub (running in python async-land) is through a :class:`curio.UniversalQueue` 
object.

Todo:
    * The message parsers need to handle detaching of peripherals
"""
import struct, logging
from .const import DEVICES
from .messages import Message, UnknownMessageError

logger = logging.getLogger(__name__)

class MessageDispatch:
    """Parse messages (bytearray)

       Once the :meth:`parse` method is called, the message header will be parsed, and based on the msg_type
       byte, the processing of the message body will be dispatched to the `parse` method of the matching Message body parser.  
       Message body parsers are subclasses of :class:`bricknil.messages.Message`, and will call back
       to the `message*` methods below.  This object will then send a message to the connected :class:`bricknil.hub.Hub`
       object.
    """
    def __init__(self, hub):
        """
            Args:
                hub (:class:`bricknil.hub.Hub`) : The hub that will be sending messages

            Attributes:
                port_info (dict): A mirror copy of the :py:attr:`bricknil.hub.Hub.port_info` object.  This object is sent every time
                    an update on the port meta data is made.
        """
        self.hub = hub
        self.port_info = {}
        
    def parse(self, msg:bytearray):
        """Parse the header of the message and dispatch message body processing

           `l` is only used to build up a log message to display during operation, telling
           the user what kind of message was received and how it was parsed. If the message
           cannot be parsed, then `l` contains the remaining unparsed raw message that was received from the
           hardware ble device.
        """
        msg_bytes = list(msg)
        msg_bytes = msg_bytes[2:]  # Skip the first two bytes (msg length and hub id (always 0) )

        msg_type = msg_bytes.pop(0)
        l = []  # keep track of the parsed return message
        try:
            if msg_type in Message.parsers:
                Message.parsers[msg_type].parse(msg_bytes, l, self)
            else:
                raise UnknownMessageError
        except UnknownMessageError:
            l.append(self._parse_msg_bytes(msg))

        return ' '.join([str(x) for x in l])

    def _parse_msg_bytes(self, msg_bytes):
        hex_bytes = ':'.join(hex(c) for c in msg_bytes)
        return hex_bytes

    def message_update_value_to_peripheral(self, port,  value):
        """Called whenever a peripheral on the hub reports a change in its sensed value
        """
        self.hub.peripheral_queue.put( ('value_change', (port, value)) )

    def message_port_info_to_peripheral(self, port, message):
        """Called whenever a peripheral needs to update its meta-data
        """
        self.hub.peripheral_queue.put( ('update_port', (port, self.port_info[port])) )
        self.hub.peripheral_queue.put( (message, port) )

    def message_attach_to_hub(self, device_name, port):
        """Called whenever a peripheral is attached to the hub
        """
        # Now, we should activate updates from this sensor
        self.hub.peripheral_queue.put( ('attach', (port, device_name)) )

        # Send a message to update the information on this port
        self.hub.peripheral_queue.put( ('update_port',  (port, self.port_info[port])) )

        # Send a message saying this port is detected, in case the hub
        # wants to query for more properties.  (Since an attach message
        # doesn't do anything if the user hasn't @attach'ed a peripheral to it)
        self.hub.peripheral_queue.put( ('port_detected', port))


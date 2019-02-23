"""Super-class of all the Tasks in the event-loop
"""
from enum import Enum

class Process:
    """Subclass this for anything going into the Async Event Loop
        
       This class keeps track of a unique numeric ID for each process, and its name.
       It also provides some utilty functions to log messages at various levels.

       Attributes:
          id (int) : Process ID (unique)
          name (str):  Human readable name for process (does not need to be unique)
          level (:class:`MSG_LEVEL`): Max message level.  Any messages with higher levels will not be logged

    """

    _next_id = 0  
    MSG_LEVEL = Enum('MSG_LEVEL', 'NONE ERROR WARN INFO DEBUG')
    level = MSG_LEVEL.NONE  
    """No messages by default"""


    def __init__(self, name):
        self.name = name

        # Assign ID
        self.id = Process._next_id
        Process._next_id += 1

    def __str__(self):
        return f'{self.name}.{self.id}'

    def __repr__(self):
        return f'{type(self).__name__}("{self.name}")'

    def message(self, m : str , level = MSG_LEVEL.DEBUG):
        """Print message *m* if its level is lower than the instance level"""

        msg_level = level.value
        if self.level.value >= msg_level:
            print(f'{str(self)}: {m}')

    def message_info(self, m):
        """Helper function for logging messages at INFO level"""
        self.message(m, self.MSG_LEVEL.INFO)

    def message_debug(self, m):
        """Helper function for logging messages at DEBUG level"""
        self.message(m, self.MSG_LEVEL.DEBUG)

    def message_error(self, m):
        """Helper function for logging messages at ERROR level"""
        self.message(m, self.MSG_LEVEL.ERROR)

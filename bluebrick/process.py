from enum import Enum

class Process:

    next_id = 0  # Internal tracking of hub number

    MSG_LEVEL = Enum('MSG_LEVEL', 'NONE ERROR WARN INFO DEBUG')
    level = MSG_LEVEL.NONE  # No messages by default


    def __init__(self, name):
        self.name = name

        # Assign ID
        self.id = Process.next_id
        Process.next_id += 1


    def __str__(self):
        return f'{self.name}.{self.id}'

    def __repr__(self):
        return f'{type(self).__name__}("{self.name}")'

    def message(self, m, level = MSG_LEVEL.DEBUG):

        msg_level = level.value
        if self.level.value >= msg_level:
            print(f'{str(self)}: {m}')

    def message_info(self, m):
        self.message(m, self.MSG_LEVEL.INFO)

    def message_debug(self, m):
        self.message(m, self.MSG_LEVEL.DEBUG)

    def message_error(self, m):
        self.message(m, self.MSG_LEVEL.ERROR)

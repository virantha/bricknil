
class Process:

    next_id = 0  # Internal tracking of hub number

    def __init__(self, name):
        self.name = name

        # Assign ID
        self.id = Process.next_id
        Process.next_id += 1


    def __str__(self):
        return f'{self.name}.{self.id}'

    def __repr__(self):
        return f'{type(self).__name__}("{self.name}")'

    def message(self, m):
        print(f'{str(self)}: {m}')


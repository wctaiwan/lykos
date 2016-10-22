from src.context import IRCContext

Main = None # main channel

_states = ("not yet joined", "pending join", "joined", "pending leave", "left channel", "", "quit", "deleted", "cleared")

class Channel(IRCContext):

    is_channel = True

    def __init__(self, name, client):
        super().__init__(name, client)
        self.users = set()
        self.modes = {}
        self.timestamp = None
        self.state = 0

    def __str__(self):
        return "{self.__class__.__name__}: {self.name} ({_states[self.state]})".format(self=self)

    def __repr__(self):
        return "{self.__class__.__name__}({self.name})".format(self=self)


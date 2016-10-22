from src.context import IRCContext

Main = None # main channel

all_channels = {}

_states = ("not yet joined", "pending join", "joined", "pending leave", "left channel", "", "quit", "deleted", "cleared")

get = all_channels.__getitem__

def add(name, cli):
    """Add and return a new channel, or an existing one if it exists."""

    if name in all_channels:
        if cli is not all_channels[name].client:
            raise RuntimeError("different IRC client for channel {0}".format(name))
        return all_channels[name]

    chan = all_channels[name] = Channel(name, cli)
    return chan

exists = all_channels.__contains__

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


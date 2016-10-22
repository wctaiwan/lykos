from src.context import IRCContext, Features

Main = None # main channel

all_channels = {}

_states = ("not yet joined", "pending join", "joined", "pending leave", "left channel", "", "quit", "deleted", "cleared")

def _strip(name):
    return name.lstrip("".join(Features["STATUSMSG"]))

def get(name):
    """Return an existing channel, or raise a KeyError if it doesn't exist."""

    return all_channels[_strip(name)]

def add(name, cli):
    """Add and return a new channel, or an existing one if it exists."""

    name = _strip(name)

    if name in all_channels:
        if cli is not all_channels[name].client:
            raise RuntimeError("different IRC client for channel {0}".format(name))
        return all_channels[name]

    chan = all_channels[name] = Channel(name, cli)
    return chan

def exists(name):
    """Return True if a channel with the name exists, False otherwise."""

    return _strip(name) in all_channels

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

    def join(self, key=""):
        if self.state in (0, 4):
            self.state = 1
            self.client.send("JOIN {0} :{1}".format(self.name, key))

    def part(self, message=""):
        if self.state == 2:
            self.state = 3
            self.client.send("PART {0} :{1}".format(self.name, message))

    def kick(self, target, message=""):
        if self.state == 2:
            self.client.send("KICK {0} {1} :{2}".format(self.name, target, message))


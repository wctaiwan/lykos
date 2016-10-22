"""Handlers and dispatchers for IRC hooks live in this module.

Most of these hooks fire off specific events, which can be listened to
by code that wants to operate on these events. The events are explained
further in the relevant hook functions.

"""

from src.decorators import hook
from src.context import Features

### Server PING handling

@hook("ping")
def on_ping(cli, prefix, server):
    """Send out PONG replies to the server's PING requests.

    Ordering and meaning of arguments for a PING request:

    0 - The IRCClient instance (like everywhere else)
    1 - Nothing (always None)
    2 - The server which sent out the request

    """

    cli.send("PONG", server)

### Fetch and store server information

@hook("featurelist")
def get_features(cli, rawnick, *features):
    """Fetch and store the IRC server features.

    Ordering and meaning of arguments for a feature listing:

    0 - The IRCClient instance(like everywhere else)
    1 - The raw nick (nick!ident@host) of the requester (i.e. the bot)
    * - A variable number of arguments, one per available feature

    """

    for feature in features:
        if "=" in feature:
            name, data = feature.split("=")
            if ":" in data:
                Features[name] = {}
                for param in data.split(","):
                    param, value = param.split(":")
                    if param.isupper():
                        settings = [param]
                    else:
                        settings = param

                    for setting in settings:
                        if value.isdigit():
                            value = int(value)
                        elif not value:
                            value = None
                        Features[name][setting] = value

            elif "(" in data and ")" in data:
                gen = (x for y in data.split("(") for x in y.split(")") if x)
                # Reverse the order
                value = next(gen)
                Features[name] = dict(zip(next(gen), value))

            elif "," in data:
                Features[name] = data.split(",")

            else:
                if data.isdigit():
                    data = int(data)
                elif not data.isalnum() and "." not in data:
                    data = frozenset(data)
                Features[name] = data

        else:
            Features[name] = None

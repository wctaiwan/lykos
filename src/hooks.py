"""Handlers and dispatchers for IRC hooks live in this module.

Most of these hooks fire off specific events, which can be listened to
by code that wants to operate on these events. The events are explained
further in the relevant hook functions.

"""

from src.decorators import hook
from src.context import Features
from src.events import Event

from src import channel, user, settings as var

### WHO/WHOX requests and responses handling

# Always use this function whenever sending out a WHO request!

def who(cli, target, data=b""):
    """Send a WHO request with respect to the server's capabilities.

    To get the WHO replies, add an event listener for "who_result", and
    an event listener for "who_end" for the end of WHO replies.

    The return value of this function is an integer equal to the data
    given. If the server supports WHOX, the same integer will be in the
    event.params.data attribute. Otherwise, this attribute will be 0.

    """

    if isinstance(data, str):
        data = data.encode(Features["CHARSET"])
    elif isinstance(data, int):
        if data > 0xFFFFFF:
            data = b""
        else:
            data = data.to_bytes(3, "little")

    if len(data) > 3:
        data = b""

    if Features["WHOX"]:
        cli.send("WHO", target, b"%tcuihsnfdlar," + data)
    else:
        cli.send("WHO", target)

    return int.from_bytes(data, "little")

@hook("whoreply")
def who_reply(cli, bot_server, bot_nick, chan, ident, host, server, nick, status, hopcount_gecos):
    """Handle WHO replies for servers without WHOX support.

    Ordering and meaning of arguments for a bare WHO response:

    0 - The IRCClient instance (like everywhere else)
    1 - The server the requester (i.e. the bot) is on
    2 - The nickname of the requester (i.e. the bot)
    3 - The channel the request was made on
    4 - The ident of the user in this reply
    5 - The hostname of the user in this reply
    6 - The server the user in this reply is on
    7 - The nickname of the user in this reply
    8 - The status (H = Not away, G = Away, * = IRC operator, @ = Opped in the channel in 4, + = Voiced in the channel in 4)
    9 - The hop count and realname (gecos)

    This fires off the "who_result" event, and dispatches it with three
    arguments, the game state namespace, a Channel, and a User. Less
    important attributes can be accessed via the event.params namespace.

    """

    hop, realname = hopcount_gecos.split(None, 1)
    hop = int(hop)

    ch = None
    modes = {Features["PREFIX"].get(s) for s in status} - {None}

    if nick == bot_nick:
        user.Bot.nick = nick
        cli.ident = user.Bot.ident = ident
        cli.hostmask = user.Bot.host = host
        cli.real_name = user.Bot.realname = realname

    try:
        val = user.get(nick, ident, host, realname, allow_bot=True)
    except KeyError:
        val = user.add(cli, nick=nick, ident=ident, host=host, realname=realname)

    ch = channel.add(chan, cli)
    val.channels[ch] = modes
    ch.users.add(val)
    for mode in modes:
        if mode not in ch.modes:
            ch.modes[mode] = set()
        ch.modes[mode].add(val)

    event = Event("who_result", {}, status=status, data=0, ip_address=None, server=server, hop_count=hop, idle_time=None, extended_who=False)
    event.dispatch(var, ch, val)

@hook("whospcrpl")
def extended_who_reply(cli, bot_server, bot_nick, data, chan, ident, ip_address, host, server, nick, status, hop, idle, account, realname):
    """Handle WHOX responses for servers that support it.

    An extended WHO (WHOX) is caracterised by a second parameter to the request
    That parameter must be '%' followed by at least one of 'tcuihsnfdlar'
    If the 't' specifier is present, the specifiers must be followed by a comma and at most 3 bytes
    This is the ordering if all parameters are present, but not all of them are required
    If a parameter depends on a specifier, it will be stated at the front
    If a specifier is not given, the parameter will be omitted in the reply

    Ordering and meaning of arguments for an extended WHO (WHOX) response:

    0  -   - The IRCClient instance (like everywhere else)
    1  -   - The server the requester (i.e. the bot) is on
    2  -   - The nickname of the requester (i.e. the bot)
    3  - t - The data sent alongside the request
    4  - c - The channel the request was made on
    5  - u - The ident of the user in this reply
    6  - i - The IP address of the user in this reply
    7  - h - The hostname of the user in this reply
    8  - s - The server the user in this reply is on
    9  - n - The nickname of the user in this reply
    10 - f - Status (H = Not away, G = Away, * = IRC operator, @ = Opped in the channel in 5, + = Voiced in the channel in 5)
    11 - d - The hop count
    12 - l - The idle time (or 0 for users on other servers)
    13 - a - The services account name (or 0 if none/not logged in)
    14 - r - The realname (gecos)

    This fires off the "who_result" event, and dispatches it with three
    arguments, the game state namespace, a Channel, and a User. Less
    important attributes can be accessed via the event.params namespace.

    """

    if account == "0":
        account = None

    hop = int(hop)
    idle = int(idle)

    data = int.from_bytes(3, data.encode(Features["CHARSET"]), "little")

    ch = None
    modes = {Features["PREFIX"].get(s) for s in status} - {None}

    if nick == bot_nick:
        user.Bot.nick = nick
        cli.ident = user.Bot.ident = ident
        cli.hostmask = user.Bot.host = host
        cli.real_name = user.Bot.realname = realname
        user.Bot.account = account

    try:
        val = user.get(nick, ident, host, realname, account, allow_bot=True)
    except KeyError:
        val = user.add(cli, nick=nick, ident=ident, host=host, realname=realname, account=account)

    ch = channel.add(chan, cli)
    val.channels[ch] = modes
    ch.users.add(val)
    for mode in modes:
        if mode not in ch.modes:
            ch.modes[mode] = set()
        ch.modes[mode].add(val)

    event = Event("who_result", {}, status=status, data=data, ip_address=ip_address, server=server, hop_count=hop, idle_time=idle, extended_who=True)
    event.dispatch(var, ch, val)

@hook("endofwho")
def end_who(cli, bot_server, bot_nick, target, rest):
    """Handle the end of WHO/WHOX responses from the server.

    Ordering and meaning of arguments for the end of a WHO/WHOX request:

    0 - The IRCClient instance (like everywhere else)
    1 - The server the requester (i.e. the bot) is on
    2 - The nickname of the requester (i.e. the bot)
    3 - The target the request was made against
    4 - A string containing some information; traditionally "End of /WHO list."

    This fires off the "who_end" event, and dispatches it with two
    arguments: The game state namespace and a str of the request that
    was originally sent.

    """

    Event("who_end", {}).dispatch(var, target)

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

### Channel and user MODE handling

@hook("channelmodeis")
def current_modes(cli, server, bot_nick, chan, mode, *targets):
    """Update the channel modes with the existing ones.

    Ordering and meaning of arguments for a bare MODE response:

    0 - The IRCClient instance (like everywhere else)
    1 - The server the requester (i.e. the bot) is on
    2 - The nickname of the requester (i.e. the bot)
    3 - The channel holding the modes
    4 - The modes of the channel
    * - The targets to the modes (if any)

    """

    ch = channel.add(chan, cli)
    ch.update_modes(server, mode, targets)

@hook("channelcreate")
def chan_created(cli, server, bot_nick, chan, timestamp):
    """Update the channel timestamp with the server's information.

    Ordering and meaning of arguments for a bare MODE response end:

    0 - The IRCClient instance (like everywhere else)
    1 - The server the requester (i.e. the bot) is on
    2 - The nickname of the requester (i.e. the bot)
    3 - The channel in question
    4 - The UNIX timestamp of when the channel was created

    We probably don't need to care about this at all, but it doesn't
    hurt to keep it around. If we ever need it, it will be there.

    """

    channel.add(chan, cli).timestamp = int(timestamp)

@hook("mode")
def mode_change(cli, rawnick, chan, mode, *targets):
    """Update the channel and user modes whenever a mode change occurs.

    Ordering and meaning of arguments for a MODE change:

    0 - The IRCClient instance (like everywhere else)
    1 - The raw nick of the mode setter/actor
    2 - The channel (target) of the mode change
    3 - The mode changes
    * - The targets of the modes (if any)

    This takes care of properly updating all relevant users and the
    channel modes to make sure we remain internally consistent.

    """

    actor = user.get(rawnick, allow_none=True, raw_nick=True)
    if chan == user.Bot.nick: # we only see user modes set to ourselves
        user.Bot.modes.update(mode)
        return

    target = channel.add(chan, cli)
    target.update_modes(rawnick, mode, targets)

    Event("mode_change", {}).dispatch(var, actor, target)


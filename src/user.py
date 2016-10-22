from src.context import IRCContext

from weakref import WeakSet
import re

Bot = None # bot instance

all_users = WeakSet()

_arg_msg = "(nick={0}, ident={1}, host={2}, realname={3}, account={4}, allow_bot={5})"

def get(nick=None, ident=None, host=None, realname=None, account=None, *, allow_multiple=False, allow_none=False, allow_bot=False, raw_nick=False):
    """Return the matching user(s) from the user list.

    This takes up to 5 positional arguments (nick, ident, host, realname,
    account) and may take up to four keyword-only arguments:

    - allow_multiple (defaulting to False) allows multiple matches,
      and returns a list, even if there's only one match;

    - allow_none (defaulting to False) allows no match at all, and
      returns None instead of raising an error; an empty list will be
      returned if this is used with allow_multiple;

    - allow_bot (defaulting to False) allows the bot to be matched and
      returned;

    - raw_nick (defaulting to False) means that the nick has not been
      yet parsed, and so ident and host will be None, and nick will be
      a raw nick of the form nick!ident@host.

    If allow_multiple is not set and multiple users match, a ValueError
    will be raised. If allow_none is not set and no users match, a KeyError
    will be raised.

    """

    if raw_nick:
        if ident is not None or host is not None:
            raise ValueError("ident and host need to be None if raw_nick is True")
        nick, ident, host = parse_rawnick(nick)

    potential = []
    users = set(all_users)
    if allow_bot:
        users.add(Bot)

    for user in users:
        if nick is not None and user.nick != nick:
            continue
        if ident is not None and user.ident != ident:
            continue
        if host is not None and user.host != host:
            continue
        if realname is not None and user.realname != realname:
            continue
        if account is not None and user.account != account:
            continue

        if not potential or allow_multiple:
            potential.append(user)
        else:
            raise ValueError("More than one user matches: " +
                             _arg_msg.format(nick, ident, host, realname, account, allow_bot))

    if not potential and not allow_none:
        raise KeyError(_arg_msg.format(nick, ident, host, realname, account, allow_bot))

    if allow_multiple:
        return potential

    if not potential: # allow_none
        return None

    return potential[0]

def add(cli, *, nick, ident=None, host=None, realname=None, account=None, channels=None, raw_nick=False):
    """Create a new user, add it to the user list and return it.

    This function takes up to 6 keyword-only arguments (and no positional
    arguments): nick, ident, host, realname, account and channels.
    With the exception of the first one, any parameter can be omitted.
    If a matching user already exists, a ValueError will be raised.

    The raw_nick keyword argument may be set if the nick has not yet
    been parsed. In that case, ident and host must both be None, and
    nick must be in the form nick!ident@host.

    """

    if raw_nick:
        if ident is not None or host is not None:
            raise ValueError("ident and host need to be None if raw_nick is True")
        nick, ident, host = parse_rawnick(nick)

    if exists(nick, ident, host, realname, account, allow_multiple=True, allow_bot=True):
        raise ValueError("User already exists: " + _arg_msg.format(nick, ident, host, realname, account, True))

    if channels is None:
        channels = {}
    else:
        channels = dict(channels)

    new = User(cli, nick, ident, host, realname, account, channels)
    all_users.add(new)
    return new

def exists(*args, allow_none=False, **kwargs):
    """Return True if a matching user exists.

    Positional and keyword arguments are the same as get(), with the
    exception that allow_none may not be used (a RuntimeError will be
    raised in that case).

    """

    if allow_none: # why would you even want to do that?
        raise RuntimeError("Cannot use allow_none=True with exists()")

    try:
        get(*args, **kwargs)
    except (KeyError, ValueError):
        return False

    return True

_raw_nick_pattern = re.compile(

    r"""
    \A
    (?P<nick>  [^!@\s]+ (?=!|$) )? !?
    (?P<ident> [^!@\s]+         )? @?
    (?P<host>  \S+ )?
    \Z
    """,

    re.VERBOSE

)

def parse_rawnick(rawnick, *, default=None):
    """Return a tuple of (nick, ident, host) from rawnick."""

    return _raw_nick_pattern.search(rawnick).groups(default)

def parse_rawnick_as_dict(rawnick, *, default=None):
    """Return a dict of {"nick": nick, "ident": ident, "host": host}."""

    return _raw_nick_pattern.search(rawnick).groupdict(default)

def lower(nick):
    if nick is None:
        return None

    mapping = {
        "[": "{",
        "]": "}",
        "\\": "|",
        "^": "~",
    }

    if Features["CASEMAPPING"] == "strict-rfc1459":
        mapping.pop("^")
    elif Features["CASEMAPPING"] == "ascii":
        mapping.clear()

    return nick.lower().translate(str.maketrans(mapping))

def equals(nick1, nick2):
    return lower(nick1) == lower(nick2)

class User(IRCContext):

    is_user = True

    def __init__(self, cli, nick, ident, host, realname, account, channels):
        super().__init__(nick, cli)
        self.nick = nick
        self.ident = ident
        self.host = host
        self.realname = realname
        self.account = account
        self.channels = channels

    def __str__(self):
        return "{self.__class__.__name__}: {self.nick}!{self.ident}@{self.host}#{self.realname}:{self.account}".format(self=self)

    def __repr__(self):
        return "{self.__class__.__name__}({self.nick}, {self.ident}, {self.host}, {self.realname}, {self.account}, {self.channels})".format(self=self)

    def get_send_type(self, *, is_notice=False, is_privmsg=False):
        if is_notice and not is_privmsg: # still to do
            return "NOTICE"
        return "PRIVMSG"

    @property
    def nick(self): # name should be the same as nick (for length calculation)
        return self.name

    @nick.setter
    def nick(self, nick):
        self.name = nick
        if self is Bot: # update the client's nickname as well
            self.client.nickname = nick

    @property
    def account(self): # automatically converts "0" and "*" to None
        return self._account

    @account.setter
    def account(self, account):
        if account in ("0", "*"):
            account = None
        self._account = account

    @property
    def rawnick(self):
        return "{self.nick}!{self.ident}@{self.host}".format(self=self)

    @rawnick.setter
    def rawnick(self, rawnick):
        self.nick, self.ident, self.host = parse_rawnick(rawnick)

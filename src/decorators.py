import fnmatch
import socket
import traceback
import types
from collections import defaultdict

from oyoyo.client import IRCClient

import botconfig
from src.utilities import *
from src import logger, errlog, events, channel, user
from src.messages import messages

adminlog = logger.logger("audit.log")

COMMANDS = defaultdict(list)
HOOKS = defaultdict(list)

# Error handler decorators

class handle_error:

    def __new__(cls, func):
        if isinstance(func, cls): # already decorated
            return func

        self = super().__new__(cls)
        self.func = func
        return self

    def __get__(self, instance, owner):
        if instance is not None:
            return types.MethodType(self, instance)
        return self

    def __call__(self, *args, **kwargs):
        try:
            return self.func(*args, **kwargs)
        except Exception:
            traceback.print_exc() # no matter what, we want it to print
            chan = channel.Main
            if botconfig.DEV_CHANNEL:
                chan = channel.get(botconfig.DEV_CHANNEL)
            if not botconfig.PASTEBIN_ERRORS or channel.Main is not chan:
                channel.Main.send(messages["error_log"])
            errlog(traceback.format_exc())
            if botconfig.PASTEBIN_ERRORS and botconfig.DEV_CHANNEL:
                pastebin_tb(chan, messages["error_log"], traceback.format_exc())

class cmd:
    def __init__(self, *cmds, flag=None, owner_only=False,
                 chan=True, pm=False, playing=False, silenced=False,
                 phases=(), roles=(), users=None):

        self.cmds = cmds
        self.flag = flag
        self.owner_only = owner_only
        self.chan = chan
        self.pm = pm
        self.playing = playing
        self.silenced = silenced
        self.phases = phases
        self.roles = roles
        self.users = users # iterable of users that can use the command at any time (should be a mutable object)
        self.func = None
        self.aftergame = False
        self.name = cmds[0]

        alias = False
        self.aliases = []
        for name in cmds:
            for func in COMMANDS[name]:
                if (func.owner_only != owner_only or
                    func.flag != flag):
                    raise ValueError("unmatching protection levels for " + func.name)

            COMMANDS[name].append(self)
            if alias:
                self.aliases.append(name)
            alias = True

    def __call__(self, func):
        if isinstance(func, cmd):
            func = func.func
        self.func = func
        self.__doc__ = self.func.__doc__
        return self

    @handle_error
    def caller(self, var, source, target, message):
        if not self.pm and not target.is_user:
            return # PM command, not allowed

        if not self.chan and not target.is_channel:
            return # channel command, not allowed

        if target.is_channel and target != channel.Main and not (self.flag or self.owner_only):
            if "" in self.cmds:
                return # don't have empty commands triggering in other channels
            for command in self.cmds:
                if command in botconfig.ALLOWED_ALT_CHANNELS_COMMANDS:
                    break
            else:
                return

        if "" in self.cmds:
            return self.func(var, source, target, message)

        if self.phases and var.PHASE not in self.phases:
            return

        if self.playing and (source not in list_players() or source in var.DISCONNECTED):
            return

        for role in self.roles:
            if nick in var.ROLES[role]:
                break
        else:
            if (self.users is not None and source not in self.users) or self.roles:
                return

        if self.silenced and source in var.SILENCED:
            reply(source, target, messages["silenced"])
            return

        if self.roles or (self.users is not None and source in self.users):
            return self.func(var, source, target, message) # don't check restrictions for role commands

        forced_owner_only = False
        if hasattr(botconfig, "OWNERS_ONLY_COMMANDS"):
            for command in self.cmds:
                if command in botconfig.OWNERS_ONLY_COMMANDS:
                    forced_owner_only = True
                    break

        if self.owner_only or forced_owner_only:
            if source.is_owner():
                adminlog(target.name, source.rawnick, self.name, message)
                return self.func(var, source, target, message)

            reply(source, target, messages["not_owner"])
            return

        flags = var.FLAGS[source.rawnick] + var.FLAGS_ACCS[source.account]
        if self.flag and source.is_admin():
            adminlog(target.name, source.rawnick, self.name, message)
            return self.func(var, source, target, message)

        denied_cmds = var.DENY[source.rawnick] | var.DENY_ACCS[source.account]
        for command in self.cmds:
            if command in denied_cmds:
                reply(source, target, messages["invalid_permissions"])
                return

        if self.flag:
            if self.flag in flags:
                adminlog(target.name, source.rawnick, self.name, message)
                return self.func(var, source, target, message)

            reply(source, target, messages["not_an_admin"])
            return

        return self.func(var, source, target, message)

class hook:
    def __init__(self, name, hookid=-1):
        self.name = name
        self.hookid = hookid
        self.func = None

        HOOKS[name].append(self)

    def __call__(self, func):
        if isinstance(func, hook):
            self.func = func.func
        else:
            self.func = func
        self.__doc__ = self.func.__doc__
        return self

    @handle_error
    def caller(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    @staticmethod
    def unhook(hookid):
        for each in list(HOOKS):
            for inner in list(HOOKS[each]):
                if inner.hookid == hookid:
                    HOOKS[each].remove(inner)
            if not HOOKS[each]:
                del HOOKS[each]

class event_listener:
    def __init__(self, event, priority=5):
        self.event = event
        self.priority = priority
        self.func = None

    def __call__(self, *args, **kwargs):
        if self.func is None:
            func = args[0]
            if isinstance(func, event_listener):
                func = func.func
            self.func = handle_error(func)
            events.add_listener(self.event, self.func, self.priority)
            self.__doc__ = self.func.__doc__
            return self
        else:
            return self.func(*args, **kwargs)

    def remove(self):
        events.remove_listener(self.event, self.func, self.priority)

# vim: set sw=4 expandtab:

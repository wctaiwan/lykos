import re
import random
import itertools
import math
from collections import defaultdict

from src.utilities import *
from src import users, channels, status, debuglog, errlog, plog
from src.functions import get_players, get_all_players
from src.decorators import command, event_listener
from src.containers import UserList, UserSet, UserDict, DefaultUserDict
from src.messages import messages
from src.status import try_misdirection, try_exchange

@event_listener("transition_night_end", priority=5)
def on_transition_night_end(evt, var):
    for blessed in get_all_players(("blessed villager",)):
        status.add_protection(var, blessed, blessed, "blessed villager")
        if var.NIGHT_COUNT == 1 or var.ALWAYS_PM_ROLE:
            to_send = "blessed_notify"
            if blessed.prefers_simple():
                to_send = "role_simple"
            blessed.send(messages[to_send].format("blessed villager"))

@event_listener("myrole")
def on_myrole(evt, var, user):
    if user in var.ROLES["blessed villager"]:
        evt.data["messages"].append(messages["blessed_simple"])

@event_listener("get_role_metadata")
def on_get_role_metadata(evt, var, kind):
    if kind == "role_categories":
        evt.data["blessed villager"] = {"Village"}

# vim: set sw=4 expandtab:

from src.context import IRCContext

Bot = None # bot instance

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

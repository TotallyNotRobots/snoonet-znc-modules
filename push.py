import inspect
import json
from collections import namedtuple
from operator import attrgetter

import requests
import znc

help_url = "https://snoonet.org/push"
API_URL = "https://api.pushbullet.com/v2/pushes"

Command = namedtuple("Command", "name func min_args max_args syntax help_msg include_cmd")


def command(name, min_args=0, max_args=None, syntax=None, help_msg=None, include_cmd=False):
    def _decorate(func):
        nonlocal help_msg, syntax
        try:
            func_doc = func.__doc__
        except AttributeError:
            func_doc = None
        if func_doc is None:
            func_doc = ""
        func_doc = inspect.cleandoc(func_doc).splitlines()
        if help_msg is None and func_doc:
            help_msg = func_doc.pop(0)

        if syntax is None and func_doc:
            syntax = func_doc.pop(0)

        try:
            handlers = func._cmd_handlers
        except AttributeError:
            handlers = []
            func._cmd_handlers = handlers
        handlers.append(Command(name, func, min_args, max_args, syntax, help_msg, include_cmd))
        return func

    return _decorate


class push(znc.Module):
    module_types = [znc.CModInfo.NetworkModule]
    description = "PushBullet notifications"
    if znc.VersionMajor == 1 and znc.VersionMinor >= 7:
        @staticmethod
        def convertMessageToParts(msg):
            return msg.GetNick(), msg.GetText(), msg.GetChan()

        def OnChanTextMessage(self, msg):
            self.check_contents(*self.convertMessageToParts(msg))

        def OnChanNoticeMessage(self, msg):
            self.check_contents(*self.convertMessageToParts(msg))

        def OnPrivTextMessage(self, msg):
            self.check_contents(*self.convertMessageToParts(msg))

        def OnPrivNoticeMessage(self, msg):
            current_server = self.GetNetwork().GetIRCServer()
            nick, text, chan = self.convertMessageToParts(msg)
            if nick.GetNick() != current_server:
                self.check_contents(nick, text, chan)

    else:
        def OnChanMsg(self, nick, channel, message):
            self.check_contents(nick, message, channel)

        def OnChanNotice(self, nick, channel, message):
            self.check_contents(nick, message, channel)

        def OnPrivMsg(self, nick, message):
            self.check_contents(nick, message)

        def OnPrivNotice(self, nick, message):
            current_server = self.GetNetwork().GetIRCServer()
            # Ignore any server notices
            if nick.GetNick() != str(current_server):
                self.check_contents(nick, message)

    def check_contents(self, nick, message, channel=None):
        if not self.is_enabled:
            return
        sender_nick = (nick.GetNick()).lower()
        if sender_nick not in self.ignore_list:
            if channel:
                msg = str(message).lower().split()
                highlighted = any(
                    self.should_highlight(word) for word in msg
                )
                if highlighted:
                    self.send_message(nick, message, channel)
            else:
                self.send_message(nick, message)

    def send_message(self, nick, message, channel=None):
        if channel:
            msg = "{chan} <{nick}> {msg}".format(chan=channel.GetName(), nick=nick.GetNick(), msg=message)
            title = "Highlight"
        else:
            msg = "<{nick}> {msg}".format(nick=nick.GetNick(), msg=message)
            title = "Private Message"

        if not self.is_private:
            title = msg
        self.notify(title, msg)

    def notify(self, title, body):
        if not self.token:
            return False
        data = dict(type="note", title=title, body=body)
        try:
            requests.post(API_URL, auth=(self.token, ""), data=data)
        except requests.RequestException:
            return False
        return True

    def should_highlight(self, word):
        if word in self.highlight_list:
            return True
        elif word.rstrip(":;,") in self.highlight_list:
            return True
        return False

    @property
    def is_enabled(self):
        if not self.enabled:
            return False
        if self.away_only:
            return self.GetNetwork().IsIRCAway()
        return True

    @property
    def enabled(self):
        return self.nv.get("state") == "on"

    @enabled.setter
    def enabled(self, new_state):
        self.nv["state"] = "on" if new_state else "off"

    @property
    def ignore_list(self):
        return tuple(json.loads(self.nv.get("ignore", "[]")))

    @ignore_list.setter
    def ignore_list(self, lst):
        self.nv["ignore"] = json.dumps(lst)

    @property
    def highlight_list(self):
        return tuple(json.loads(self.nv.get("highlight", "[]"))) + (self.current_nick,)

    @highlight_list.setter
    def highlight_list(self, lst):
        self.nv["highlight"] = json.dumps(lst)

    @property
    def is_private(self):
        return self.nv.get("private") == "yes"

    @is_private.setter
    def is_private(self, value):
        self.nv["private"] = "yes" if value else "no"

    @property
    def away_only(self):
        return self.nv.get("away_only") == "yes"

    @away_only.setter
    def away_only(self, value):
        self.nv["away_only"] = "yes" if value else "no"

    @property
    def token(self):
        return self.nv.get("token")

    @token.setter
    def token(self, new_token):
        self.nv["token"] = new_token

    @property
    def current_nick(self):
        return str(self.GetNetwork().GetCurNick()).lower()

    @command("enable")
    def cmd_enable(self):
        """Enables notifications"""
        if self.token:
            self.enabled = True
            return "Notifications \x02enabled\x02."
        return "You must set a token before enabling notifications."

    @command("disable")
    def cmd_disable(self):
        """Disables notifications"""
        self.enabled = False
        return "Notifications \x02disabled\x02."

    @command("set", 1, 2)
    def cmd_set(self, key, value=None):
        """Sets the 'token', 'away_only', or 'private' options
        <option> [value]"""
        key = key.lower()
        if key == "token":
            if self.enabled:
                return "You must disable notifications before changing your token."

            if value:
                self.token = value
                return "Token set successfully."
            else:
                self.token = ""
                return "Token cleared."
        elif key in ("away_only", "private"):
            if value in ("yes", "no"):
                self.nv[key] = value
                return "{opt} option set to \x02{setting}\x02".format(opt=key, setting=value)
            else:
                return "You must specify either 'yes' or 'no'."
        else:
            return "Invalid option. Options are 'token', 'away_only', and 'private'. See {}".format(help_url)

    @command("highlight", 1, 2, help_msg="Manages the highlight list", include_cmd=True)
    @command("ignore", 1, 2, help_msg="Manages the ignore list", include_cmd=True)
    def cmd_list_mgmt(self, list_name, action, arg=None):
        """{add|del|list} [value]"""
        cmd_list = json.loads(self.nv.get(list_name, "[]"))
        if action == "list":
            if cmd_list:
                return "{title} list: \x02{cmd_list}\x02".format(
                    title=list_name.title(), cmd_list=', '.join(cmd_list)
                )
            else:
                return "{name} list is empty.".format(name=list_name)
        elif action == "add":
            if not arg:
                return "You must specify a single word or nick to add."
            if arg.lower() not in cmd_list:
                cmd_list.append(arg.lower())
                self.nv[list_name] = json.dumps(cmd_list)
                return "\x02{arg}\x02 added to {list_name} list.".format(arg=arg, list_name=list_name)
            return "\x02{arg}\x02 already in {list_name} list.".format(arg=arg, list_name=list_name)
        elif action == "del":
            if not arg:
                return "You must specify a single word or nick to delete."

            if not cmd_list:
                return "{} list is empty.".format(list_name.title())

            if arg.lower() in cmd_list:
                cmd_list.remove(arg.lower())
                self.nv[list_name] = json.dumps(cmd_list)
                return "\x02{arg}\x02 deleted from {list_name} list.".format(arg=arg, list_name=list_name)

            return "\x02{arg}\x02 not in {list_name} list.".format(arg=arg, list_name=list_name)
        else:
            return "Invalid option. Options are 'list', add', and 'del'. See {}".format(help_url)

    @command("test")
    def cmd_test(self):
        """Sends a test message over pushbullet"""
        if self.token:
            self.notify("Test Message", "This is a test message.")
            return "Test message successfully sent."
        else:
            return "You must supply a token before you can test whether or not it works"

    @command("help")
    def cmd_help(self):
        """Returns help documentation for this module"""
        help_table = znc.CTable()
        help_table.AddColumn("Command")
        help_table.AddColumn("Arguments")
        help_table.AddColumn("Description")

        for cmd in sorted(self.cmd_handlers.values(), key=attrgetter("name")):
            help_table.AddRow()
            help_table.SetCell("Command", cmd.name)
            help_table.SetCell("Arguments", cmd.syntax or "")
            help_table.SetCell("Description", cmd.help_msg or "")

        return help_table, "You can also view this help at {}".format(help_url)

    @property
    def cmd_handlers(self):
        handlers = []
        for obj in self.__class__.__dict__.values():
            try:
                handlers.extend(obj._cmd_handlers)
            except AttributeError:
                pass
        return {handler.name: handler for handler in handlers}

    def OnModCommand(self, text):
        cmd, *args = text.strip().split()
        cmd = self.cmd_handlers.get(cmd.lower())
        if not cmd:
            self.PutModule("Invalid command. See {}".format(help_url))
            return
        if len(args) < cmd.min_args:
            self.PutModule("Invalid arguments for command")
            return
        args = list(args)
        max_args = cmd.max_args
        if max_args is None:
            max_args = cmd.min_args
        if len(args) > max_args:
            args[max_args] = " ".join(args[max_args:])
            del args[max_args + 1:]

        if cmd.include_cmd:
            args = [cmd.name] + args

        result = cmd.func(self, *args)
        if result:
            if isinstance(result, tuple):
                for part in result:
                    self.PutModule(part)
            else:
                self.PutModule(result)

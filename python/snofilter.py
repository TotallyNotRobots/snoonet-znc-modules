import znc
import re
import json
from collections import namedtuple

DEFAULT_SNOTICE_FORMAT = r"\*\*\* (?P<snotype>[^ ]+?): (?P<message>.*)"
DEFAULT_MSG_TYPE = "NOTICE"

__version__ = "0.0.1"
__author__ = "linuxdaemon"

Command = namedtuple('Command', 'name func syntax doc minargs')


class snofilter(znc.Module):
    description = "Filters server notices to configurable query/notice windows"
    module_types = [znc.CModInfo.NetworkModule]

    def OnLoad(self, args, message):
        self.snotice_re = self.nv.get('snotice_re', DEFAULT_SNOTICE_FORMAT)
        self.sno_settings = self.load_settings()
        self.commands = {}
        self.add_command("SetPattern", self.set_pattern, "<pattern>", "Set the regex used when parsing the server notices", 1)
        self.add_command("GetPattern", self.get_pattern, "", "Get the current regex used to parse server notices")
        self.add_command("AddRule", self.add_rule, "<type> <window> [msg_type]", "Will send a server notices of <type> to <window> as [msg_type] (default: notice)", 2)
        self.add_command("DelRule", self.del_rule, "<rulenum>", "Remove a server notice rule from the list", 1)
        self.add_command("ListRules", self.list_rules, "", "List all current server notice rules")
        self.add_command("Help", self.send_help, "", "List all commands supported by this module")
        return True

    def add_command(self, name, func, syntax, doc, minargs=0):
        self.commands[name.lower()] = Command(name, func, syntax, doc, minargs)

    def OnShutdown(self):
        self.save_settings()

    def load_settings(self):
        return json.loads(self.nv.get('rules', '[]'))

    def save_settings(self):
        self.nv['rules'] = json.dumps(self.sno_settings)

    def handle_snotice(self, snotype, message):
        network = self.GetNetwork()
        command = ":{window}!snofilter@znc.in {msg_type} {cur_nick} :{message}"
        sno_settings = [s for s in self.sno_settings if s['type'].lower() == snotype.lower()]
        for settings in (sno_settings or [{}]):
            fmt_command = command.format(window=settings.get('window', snotype.lower()),
                                         msg_type=settings.get('msg_type', DEFAULT_MSG_TYPE),
                                         cur_nick=network.GetCurNick(), message=message)
            self.PutUser(fmt_command)
    
    def OnPrivNotice(self, nick, message):
        server_name = self.GetNetwork().GetIRCServer()
        if str(server_name) == str(nick.GetNick()):
            match = re.match(self.snotice_re, str(message))
            if match:
                self.handle_snotice(match.group('snotype'), match.group('message'))
                return znc.HALTCORE
        return znc.CONTINUE

    def OnModCommand(self, line):
        cmd, _, args = line.partition(' ')
        cmd = cmd.lower()
        if cmd not in self.commands:
            self.PutModule("Unkown command!")
            return
        command = self.commands[cmd]
        if command.minargs > len(args.split()):
            self.PutModule("Invalid arguments")
            return
        command.func(args)
        
    def set_pattern(self, pattern):
        self.snotice_re = pattern
        self.nv['snotice_re'] = pattern

    def get_pattern(self, line):
        self.PutModule("Current Pattern: \"{}\"".format(self.snotice_re))

    def add_rule(self, line):
        # <type> <window> [msg_type]
        args = line.split()
        settings = {"type": args[0].lower(), "window": args[1]}
        if len(args) > 2:
            settings['msg_type'] = args[2].upper()
        self.sno_settings.append(settings)
        self.save_settings()
        self.PutModule("Added rule for {type} server notices".format(type=args[0]))

    def del_rule(self, line):
        num = int(line.split()[0])
        if num >= len(self.sno_settings):
            self.PutModule("Rule #{} not found".format(num))
        else:
            del self.sno_settings[num]
            self.save_settings()
            self.PutModule("Rule #{} removed".format(num))

    def list_rules(self, line):
        rule_tbl = znc.CTable()
        rule_tbl.AddColumn("Num")
        rule_tbl.AddColumn("Type")
        rule_tbl.AddColumn("Window")
        rule_tbl.AddColumn("Message Type")
        for i in range(len(self.sno_settings)):
            settings = self.sno_settings[i]
            rule_tbl.AddRow()
            rule_tbl.SetCell("Num", str(i))
            rule_tbl.SetCell("Type", settings['type'])
            rule_tbl.SetCell("Window", settings.get('window', DEFAULT_WINDOW))
            rule_tbl.SetCell("Message Type", settings.get('msg_type', ''))
        self.PutModule(rule_tbl)

    def send_help(self, line):
        help_tbl = znc.CTable()
        help_tbl.AddColumn("Command")
        help_tbl.AddColumn("Arguments")
        help_tbl.AddColumn("Description")
        for command in self.commands.values():
            help_tbl.AddRow()
            help_tbl.SetCell("Command", command.name)
            help_tbl.SetCell("Arguments", command.syntax)
            help_tbl.SetCell("Description", command.doc)
        self.PutModule(help_tbl)

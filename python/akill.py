import json
from copy import copy

import znc

# ['akill', 'nick', 'time', 'reason', 'optional']
#    [0]      [1]    [2]       [3]        [4]

DEFAULT_REASONS = {
    "netban": "{address}: {htime} network ban for evasion of a network ban. {trail}",
    "spam": "{address}: {htime} network ban for spam. {trail}",
    "given": "{text}",
    "evasion": "{address}: {htime} network ban for ban evasion in {reason}. {trail}",
}

DEFAULT_FORMAT = "AKILL ADD +{duration} {mask} {reason}"
MSG_FORMAT = "PRIVMSG OperServ :{cmd}"

DEFAULT_TRAIL = "Further violations of our network rules will result in an " \
                "increase in ban length and may become permanent. " \
                "https://snoonet.org/rules"


def convert_table(data, headers):
    table = znc.CTable()
    for header in headers:
        table.AddColumn(header)

    for row in data:
        table.AddRow()
        for i, value in enumerate(row):
            table.SetCell(headers[i], value)

    return table


class akill(znc.Module):
    description = "Shortcut commands for akill"
    module_types = [znc.CModInfo.NetworkModule]

    def OnLoad(self, args, msg):
        self.load_conf()
        return True

    @staticmethod
    def params_from_msg(msg):
        i = 0
        params = []
        while True:
            param = msg.GetParam(i)
            if param == '':
                break
            params.append(param)
            i += 1
        return params

    def parse_akill(self, nick, time, reason, address):
        address = ", ".join(address)
        reason = reason.lower()
        text = " ".join(address)
        address = ', '.join(address) or nick

        data = {
            "address": address,
            "htime": self.human_time(time),
            "nick": nick,
            "text": text,
            "reason": reason,
            "trail": self.trail,
        }

        if reason[0] == "#":
            reason = "evasion"
        elif reason == "evasion":
            self.PutModNotice("You must specify a channel as the reason when banning for evasion.")
            return znc.HALT

        if reason in self.reasons:
            fmt = self.reasons[reason]
            try:
                out = fmt.format_map(data)
            except LookupError as e:
                self.PutModNotice("Missing required parameter: {}".format(e))
            else:
                self.do_akill(nick, time, out)
        else:
            self.send_usage()

        return znc.HALT
    if znc.VersionMajor == 1 and znc.VersionMinor >= 7:
        def OnUserRawMessage(self, msg):
            if msg.GetCommand().upper() != "AKILL":
                return znc.CONTINUE
            params = self.params_from_msg(msg)
            if len(params) < 3:
                # too few args, send usage
                self.PutModNotice("/akill requires at least three arguments")
                self.send_usage()
                return znc.CONTINUE

            nick, time, reason, *address = params

            return self.parse_akill(nick, time, reason, address)

    if znc.VersionMajor == 1 and znc.VersionMinor < 7:
        def OnUserRaw(self, linecs):
            line = linecs.s.split()
            cmd = line[0].lower()
            if cmd != "akill":
                return znc.CONTINUE

            if len(line) < 4:
                # too short, respond with error as a notice
                self.send_usage()
                return znc.CONTINUE

            _, nick, time, reason, *address = line
            return self.parse_akill(nick, time, reason, address)

    def OnModCommand(self, text):
        cmd, _, args = str(text).partition(' ')
        cmd = cmd.lower()

        out = ""

        if cmd == "help":
            out = self.cmd_help()

        elif cmd == "listreasons":
            out = self.list_reasons()

        elif cmd == "setreason":
            out = self.add_reason(args)

        elif cmd == "delreason":
            out = self.del_reason(args)

        elif cmd == "settrail":
            out = self.set_trail(args)

        elif cmd == "setcmd":
            out = self.set_cmd(args)

        elif cmd == "setformat":
            out = self.set_format(args)

        else:
            out = "Unknown command. See Help for more information"

        if out:
            self.PutModule(out)

    def cmd_help(self):
        headers = ["Command", "Arguments", "Description"]
        table = (
            ("Help", "", "Displays the help for this module"),
            ("ListReasons", "", "Lists all currently configured reasons"),
            ("SetReason", "<name> <format>", "Sets the format for the specified reason"),
            ("DelReason", "<name>", "Removes a reason from the list"),
            ("SetTrail", "<trail>", "Sets the trailing text to be appended to akill reasons"),
            ("SetCmd", "<format>", "Set the format for the command to send (default: {})".format(DEFAULT_FORMAT)),
            ("SetFormat", "<format>",
             "Set the format for the raw line to send to the server (default: {})".format(MSG_FORMAT)),
        )

        return convert_table(table, headers)

    def list_reasons(self):
        headers = ["Name", "Format"]
        return convert_table(self.reasons.items(), headers)

    def add_reason(self, args):
        name, _, fmt = args.partition(' ')
        if not name:
            return "Missing required parameter: name"

        if not fmt:
            return "Missing required parameter: format"

        name = name.lower()
        old = self.reasons.get(name)
        self.reasons[name] = fmt
        self.save_conf()

        if old is not None:
            return "Format set. Old format was \"{}\"".format(old)

        return "Format set."

    def del_reason(self, args):
        name = args.strip().lower()

        if not name:
            return "Missing required parameter: name"

        if name not in self.reasons:
            return "Unknown reason."

        del self.reasons[name]
        self.save_conf()
        return "Reason deleted."

    def set_trail(self, args):
        self.trail = args
        self.save_conf()
        return "Trail set."

    def set_cmd(self, args):
        self.echo_format = args
        self.save_conf()
        return "Set command."

    def set_format(self, args):
        self.akill_format = args
        self.save_conf()
        return "Set raw format."

    def do_akill(self, nick, time, reason):
        cmd = self.echo_format.format(duration=time, mask=nick, reason=reason)
        self.PutModNotice(cmd)
        self.PutIRC(self.akill_format.format(cmd=cmd))

    def send_usage(self):
        self.PutModNotice("Usage: /akill <target> <duration (default unit: days)> <reason> [nicks to address]")

    def load_conf(self):
        reasons = self.nv.get("reasons")

        if reasons is None:
            self.reasons = copy(DEFAULT_REASONS)
        else:
            self.reasons = json.loads(reasons)

        self.echo_format = self.nv.get("echo_format", DEFAULT_FORMAT)
        self.akill_format = self.nv.get("akill_format", MSG_FORMAT)

        self.trail = self.nv.get("trail", DEFAULT_TRAIL)

    def save_conf(self):
        self.nv["reasons"] = json.dumps(self.reasons)
        self.nv["echo_format"] = self.echo_format
        self.nv["akill_format"] = self.akill_format
        self.nv["trail"] = self.trail

    @staticmethod
    def human_time(time: str):
        timechrs = {
            "m": "minute",
            "h": "hour",
            "d": "day",
            "w": "week",
            "y": "year",
        }
        parts = [""]
        for char in time:
            if char in timechrs:
                parts[-1] += " " + timechrs[char]
                parts.append("")
            else:
                parts[-1] += char

        parts[:] = filter(None, parts)

        if ' ' not in parts[0]:
            parts[0] += " day"

        return ', '.join(parts)

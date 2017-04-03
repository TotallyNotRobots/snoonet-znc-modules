import znc

# ['akill', 'nick', 'time', 'reason', 'optional']
#    [0]      [1]    [2]       [3]        [4]


class akill(znc.Module):
    description = "Shortcut commands for akill"
    module_types = [znc.CModInfo.NetworkModule]

    def __init__(self):
        self.reasons = ["netban", "spam", "given"]

    def OnUserRaw(self, linecs):
        line = linecs.s.split()
        if line[0] != "PING":
            self.PutModNotice(str(line))
        if line[0] == "akill":
            if len(line) < 3:
                # too short, respond with error as a notice
                self.PutModNotice("Usage: /akill nick/mask time(In days) reason [nick to address]")
                return znc.HALT

            elif line[3][0] == "#" or line[3] in self.reasons:
                if len(line) > 4:
                    nick, time, reason, address = line[1], line[2], line[3].lower(), " ".join(line[4:])
                    if line[3][0] == "#":
                        self.evasion(time, nick, reason, address)
                    elif reason == "netban":
                        self.netban(time, nick, address)

                    elif reason == "spam":
                        self.spam(time, nick, address)
                    elif reason == "given":
                        self.ownmsg(time, nick, address)

                elif len(line) == 4:
                    nick, time, reason = line[1], line[2], line[3].lower()
                    if line[3][0] == "#":
                        self.evasion(time, nick, reason, nick)
                    elif reason == "netban":
                        self.netban(time, nick, nick)
                    elif reason == "spam":
                        self.spam(time, nick, nick)
                    elif reason == "given":
                        self.PutModNotice("given requires a reason to be specified")
                    else:
                        self.PutModNotice("Unknown option, valid options are #channel, netban, spam and given (set the "
                                          "entire message")
            return znc.HALT

    def evasion(self, time, nick, chan, address):
        self.PutModNotice(
            "PRIVMSG OperServ :akill add +{time}d {nick} {address}: {time} day network ban for ban "
            "evasion in {channel}. Further violations of our network rules will result in an increase "
            "in ban length and may become permanent. https://snoonet.org/rules".format(
                time=time, nick=nick, address=address, channel=chan
            )
        )

    def netban(self, time, nick, address):
        self.PutModNotice(
            "PRIVMSG OperServ :akill add +{time}d {nick} {address}: {time} day network ban for evasion "
            "of a network ban. Further violations of our network rules will result in an increase "
            "in ban length and may become permanent. https://snoonet.org/rules".format(
                time=time, nick=nick, address=address
            )
        )

    def spam(self, time, nick, address):
        self.PutModNotice(
            "PRIVMSG OperServ :akill add +{time}d {nick} {address}: {time} day network ban for spam."
            " Further violations of our network rules will result in an increase "
            "in ban length and may become permanent. https://snoonet.org/rules".format(
                time=time, nick=nick, address=address
            )
        )

    def ownmsg(self, time, nick, reason):
        self.PutModNotice("PRIVMSG OperServ :akill add +{time}d {nick} {reason} ".format(
            time=time, nick=nick, reason=reason
        ))

import znc


# ['akill', 'nick', 'time', 'reason', 'optional']
#    [0]      [1]    [2]       [3]        [4]


class akill(znc.Module):
    description = "Shortcut commands for akill"
    module_types = [znc.CModInfo.NetworkModule]
    reasons = ["netban", "spam", "given"]
    akill_format = "PRIVMSG OperServ :AKILL ADD +{duration} {mask} {reason}"

    def OnUserRaw(self, linecs):
        line = linecs.s.split()
        if line[0] == "akill":
            if len(line) < 4:
                # too short, respond with error as a notice
                self.send_usage()
                return znc.HALT

            elif line[3][0] == "#" or line[3] in self.reasons:
                if len(line) > 4:
                    _, nick, time, reason, *address = line
                    reason = reason.lower()
                    address = " ".join(address)
                    if line[3][0] == "#":
                        self.evasion(time, nick, reason, address)
                    elif reason == "netban":
                        self.netban(time, nick, address)
                    elif reason == "spam":
                        self.spam(time, nick, address)
                    elif reason == "given":
                        self.do_akill(nick, time, address)

                else:
                    nick, time, reason = line[1], line[2], line[3].lower()
                    if line[3][0] == "#":
                        self.evasion(time, nick, reason, nick)
                    elif reason == "netban":
                        self.netban(time, nick, nick)
                    elif reason == "spam":
                        self.spam(time, nick, nick)
                    elif reason == "given":
                        self.PutModNotice(
                            "given requires a reason to be specified")
                    else:
                        self.PutModNotice("Unknown option, valid options are "
                                          "#channel, netban, spam and "
                                          "given (set the entire message")
            else:
                self.send_usage()
            return znc.HALT

    def evasion(self, time, nick, chan, address):
        reason = "{address}: {time} day network ban for ban evasion in " \
                 "{channel}. Further violations of our network rules will " \
                 "result in an increase in ban length and may become " \
                 "permanent. https://snoonet.org/rules".format(address=address,
                                                               time=time,
                                                               channel=chan)
        self.do_akill(nick, time, reason)

    def netban(self, time, nick, address):
        reason = "{address}: {time} day network ban for evasion of a " \
                 "network ban. Further violations of our network rules will " \
                 "result in an increase in ban length and may become " \
                 "permanent. https://snoonet.org/rules".format(address=address,
                                                               time=time)
        self.do_akill(nick, time, reason)

    def spam(self, time, nick, address):
        reason = "{address}: {time} day network ban for spam. Further " \
                 "violations of our network rules will result in an " \
                 "increase in ban length and may become permanent. " \
                 "https://snoonet.org/rules".format(address=address, time=time)
        self.do_akill(nick, time, reason)

    def do_akill(self, nick, time, reason):
        self.PutIRC(
            self.akill_format.format(duration=str(time) + 'd',
                                     mask=nick,
                                     reason=reason)
        )

    def send_usage(self):
        self.PutModNotice("Usage: /akill nick/mask time(In days) "
                          "reason(Valid reasons are a channel name, spam, "
                          "netban and given. You specify the full message" 
                          "with given) [nick to address]")

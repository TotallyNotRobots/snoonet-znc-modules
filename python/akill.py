import znc


# ['akill', 'nick', 'time', 'reason', 'optional']
#    [0]      [1]    [2]       [3]        [4]


class akill(znc.Module):
    description = "Shortcut commands for akill"
    module_types = [znc.CModInfo.NetworkModule]
    reasons = ["netban", "spam", "given"]
    akill_format = "PRIVMSG OperServ :AKILL ADD +{duration} {mask} {reason}"
    echo_format = "AKILL ADD +{duration} {mask} {reason}"
    end_text = " Further violations of our network rules will result in an " \
               "increase in ban length and may become permanent. " \
               "https://snoonet.org/rules"

    def OnUserRaw(self, linecs):
        line = linecs.s.split()
        if line[0].lower() == "akill":
            if len(line) < 4:
                # too short, respond with error as a notice
                self.send_usage()
                return znc.HALT

            elif line[3][0] == "#" or line[3] in self.reasons:
                _, nick, time, reason, *address = line
                reason = reason.lower()
                address = " ".join(address)

                if line[3][0] == "#":
                    self.evasion(time, nick, reason, address or nick)
                elif reason == "netban":
                    self.netban(time, nick, address or nick)
                elif reason == "spam":
                    self.spam(time, nick, address or nick)
                elif reason == "given":
                    if address:
                        self.do_akill(nick, time, address)
                    else:
                        self.PutModNotice(
                            "given requires a reason to be specified")
                else:
                    self.send_usage()
            else:
                self.send_usage()
            return znc.HALT

    def evasion(self, time, nick, chan, address):
        reason = "{address}: {htime}network ban for ban evasion in " \
                 "{channel}.".format(
                    address=address, htime=self.human_time(time), channel=chan)
        self.do_akill(nick, time, reason + self.end_text)

    def netban(self, time, nick, address):
        reason = "{address}: {htime}network ban for evasion of a " \
                 "network ban.".format(
                    address=address, htime=self.human_time(time))
        self.do_akill(nick, time, reason + self.end_text)

    def spam(self, time, nick, address):
        reason = "{address}: {htime}network ban for spam. ".format(
                    address=address, htime=self.human_time(time))

        self.do_akill(nick, time, reason + self.end_text)

    def do_akill(self, nick, time, reason):
        self.PutModNotice(
            self.echo_format.format(duration=time, mask=nick, reason=reason)
        )

        self.PutIRC(
            self.akill_format.format(duration=time, mask=nick, reason=reason)
        )

    def send_usage(self):
        self.PutModNotice("Usage: /akill nick/mask time(defaults to days) "
                          "reason(Valid reasons are a channel name, spam, "
                          "netban and given. You specify the full message" 
                          "with given) [nick to address]")

    @staticmethod
    def human_time(time: str):
        timechrs = {
            "m": " minute ",
            "h": " hour ",
            "d": " day ",
            "w": " week ",
            "y": " year "
        }
        formatted = False
        e_time = ""
        for char in time:
            if char in timechrs:
                e_time += timechrs[char]
                formatted = True
            else:
                e_time += char

        if not formatted:
            e_time += " day "
        return e_time

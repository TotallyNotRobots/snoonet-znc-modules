import time
from collections import defaultdict
from fnmatch import fnmatch

import znc


# VER: 1.7 - added the ability to set opchans,
# which get status updates like the user does


class timeout_timer(znc.Timer):
    def RunJob(self):
        self.GetModule().do_timeouts()


class masshl(znc.Module):
    description = "monitoring of mass highlights and automatic action"
    module_types = [znc.CModInfo.NetworkModule]

    vexempts = ["op", "hop", "voice"]  # Valid exempt list

    def OnLoad(self, args, msg):
        self.PutModule("masshl loaded")
        self.nickcount = defaultdict(lambda: defaultdict(dict))
        # checking if this is our first run and if so, setting defaults
        if not self.nv.get("firstrun"):
            self.nvset("chans", [""])
            self.nvset("exempts", ["op", "hop", "voice"])
            self.nvset("mexempts", [""])
            self.nvsetint("count", 10)
            self.nv["commands"] = "MODE {chan} +b {mask}\r\nKICK {chan} " \
                                  "{nick} :Do not Mass highlight in {chan}"
            self.nvset("debug", ["no"])
            self.nvsetint("timeout", 60)
            self.nvset("firstrun", ["no"])
            self.nvset("opchans", [""])
            self.nvset("nickignore", [""])

        # Run list cleanup every 30 minutes
        self.CreateTimer(timeout_timer, interval=1800, cycles=0, description="Cleans up the ping data from masshl.py")
        return True

    def do_timeouts(self):
        timeout = self.nvget("timeout")
        nicks_to_remove = []
        for nick, chans in self.nickcount.items():
            chans_to_remove = []
            for name, data in chans.items():
                if not data or (time.time() - data.get('lping', 0)) >= timeout:
                    chans_to_remove.append(name)

            for chan in chans_to_remove:
                del chans[chan]

            if not chans:
                nicks_to_remove.append(nick)

        for nick in nicks_to_remove:
            del self.nickcount[nick]

    def OnChanMsg(self, inick, ichan, msg):
        chan = ichan.GetName().lower()
        if chan in self.nvget("chans"):
            # gets the actual string of the message and lowers it
            bmsg = msg.s.lower()
            nick = inick.GetNick()
            # List of nicks in the channel
            nicks = [nick.GetNick().casefold() for nick in ichan.GetNicks().values()]

            # checks the message contents vs the list of nicks
            checkednicks = {nick for nick in nicks if nick in bmsg}
            ignored_nicks = set(self.nvget("nickignore"))
            checkednicks.difference_update(ignored_nicks)
            count = len(checkednicks)
            # Check the current count against the configured max, if its the
            # same or bigger, send configured commands

            if count != 0 and self.nvget("debug"):
                self.PutModule("checkednicks is: {}".format(checkednicks))

            if count >= self.nvgetint("count"):
                self.tryban(inick, ichan, count)
            elif count <= 9 and count != 0:
                # checking if we've seen this nick in this channel before,
                # if not, check if they match anything in the mask exempt list,
                #  if not, initialise their var and set it to 1
                if self.checkmexempts(inick):
                    return znc.CONTINUE

                if chan not in self.nickcount[nick]:
                    self.nickcount[nick][chan] = {"count": 0, "lping": time.time()}

                # check the time against the configured timeout, and delete
                # the user if its more than the timeout
                timeout = self.nvgetint("timeout")
                if (time.time() - self.nickcount[nick][chan]["lping"]) >= timeout:
                    self.PutModule(
                        "timeout ({time})  {nick} {chan}".format(time=timeout, nick=nick, chan=chan)
                    )
                    self.nickcount[nick][chan]["count"] = 0

                self.nickcount[nick][chan]["count"] += count
                if self.nvget("debug"):
                    self.PutModule(
                        "{} seen        {nick} {chan}".format(
                            self.nickcount[nick][chan]["count"],
                            nick=nick,
                            chan=chan
                        )
                    )

                max_count = self.nvgetint("count")
                if chan in self.nickcount[nick]:
                    current_count = self.nickcount[nick][chan]["count"]
                    # if they hit the set count, try to ban them
                    if current_count >= max_count:
                        self.tryban(inick, ichan, current_count)
                        del self.nickcount[nick][chan]
                    elif (current_count / max_count) >= 0.75:
                        self.sendtoops(
                            chan,
                            "{nick} is nearing threshold in {chan}. count is {count}, threshold is {thr}".format(
                                nick=nick, chan=chan, count=current_count, thr=max_count
                            )
                        )

            if count == 0 and chan in self.nickcount[nick]:
                del self.nickcount[nick][chan]
                if self.nvget("debug"):
                    self.PutModule("cleared       {nick} {chan}".format(nick=nick, chan=chan))

            return znc.CONTINUE

    def is_exempt(self, chan_user):
        # Check the other user's status
        if chan_user.HasPerm(ord(znc.CChan.Op)) and "op" in self.nvget("exempts"):
            return True, "op"
        elif chan_user.HasPerm(ord(znc.CChan.HalfOp)) and "hop" in self.nvget("exempts"):
            return True, "hop"
        elif chan_user.HasPerm(ord(znc.CChan.Voice)) and "voice" in self.nvget("exempts"):
            return True, "voice"
        else:
            # Check configured exempts
            for exempt_mask in self.nvget("exempts"):
                if fnmatch(chan_user.GetHostMask().casefold(), exempt_mask.casefold()):
                    return True, "matches {mask}".format(mask=exempt_mask)

    def tryban(self, inick, chan, count):
        chan_name = chan.GetName()
        inick_nick = inick.GetNick()  # TODO find a better name for this variable

        # check if user has permission to ban in the channel
        if chan.HasPerm(ord(znc.CChan.Op)) or \
                chan.HasPerm(ord(znc.CChan.HalfOp)) or \
                chan.HasPerm(ord(znc.CChan.Admin)):
            is_exempt, exempt_type = self.is_exempt(inick)
            if is_exempt:
                self.PutModule(
                    "MHL from {nick} in {chan}. Count was {count}. User is exempt ({exempt_type})".format(
                        nick=inick_nick, chan=chan_name, count=count, exempt_type=exempt_type
                    )
                )

                self.sendtoops(
                    chan_name,
                    "MHL from {nick} in {chan}. Count was {count}. User is exempt ({exempt_type})".format(
                        nick=inick_nick, chan=chan_name, count=count, exempt_type=exempt_type
                    )
                )
                return znc.CONTINUE

            banmask = "*!*@" + inick.GetHost()

            self.PutModule(
                "MHL from {nick} in {chan}. Count was {count}. Ban sent".format(
                    nick=inick_nick, chan=chan_name, count=count
                )
            )

            self.sendtoops(
                chan_name,
                "MHL from {nick} in {chan}. Count was {count}. Ban sent".format(
                    nick=inick_nick, chan=chan_name, count=count
                )
            )

            self.PutIRC(
                self.nv["commands"].format(nick=inick_nick, chan=chan_name, mask=banmask, count=count)
            )
        else:
            self.PutModule(
                "MHL from {nick} in {chan}. Count was {count}. We're not opped, no action taken".format(
                    nick=inick_nick, chan=chan_name, count=count
                )
            )

    def sendtoops(self, chan, msg):
        for opchanstr in self.nvget("opchans"):
            if chan.lower() in opchanstr.split(":"):
                self.PutIRC(
                    "PRIVMSG {opchan} :***MASSHL {msg}".format(opchan=opchanstr.split(":")[1], msg=msg)
                )

    def checkmexempts(self, nick):
        if not self.nvget("mexempts"):
            return False

        for exempt in self.nvget("mexempts"):
            if fnmatch(nick.GetHostMask().lower(), exempt.lower()):
                if self.nvget("debug"):
                    self.PutModule("fnmatch       ({}, {})".format(
                        nick.GetHostMask().lower(), exempt.lower()))
                return True
        return False

    # actions get included in scanning
    def OnChanAction(self, inick, ichan, msg):
        self.OnChanMsg(inick, ichan, msg)

    def OnNick(self, onick, newnick, vchans):
        oldnick = onick.GetNick()
        if oldnick in self.nickcount:
            del self.nickcount[oldnick]
            if self.nvget("debug"):
                self.PutModule("ncleared      {nnick} {onick}".format(nnick=newnick, onick=oldnick))

        return znc.CONTINUE

    def OnPart(self, inick, ichan, pmsg):
        if ichan.GetName() in self.nvget("chans"):
            pnick = inick.GetNick()
            pchan = ichan.GetName()

            if pnick in self.nickcount:
                if pchan in self.nickcount[pnick]:
                    del self.nickcount[pnick][pchan]
                    if self.nvget("debug"):
                        self.PutModule(
                            "pcleared      {nick} {chan}".format(nick=pnick, chan=pchan)
                        )

        return znc.CONTINUE

    def OnKick(self, opnick, knick, ichan, kmsg):
        if ichan.GetName() in self.nvget("chans"):
            kchan = ichan.GetName()

            if knick in self.nickcount:
                if kchan in self.nickcount[knick]:
                    del self.nickcount[knick][kchan]
                    if self.nvget("debug"):
                        self.PutModule("kcleared      {nick} {chan}".format(nick=knick, chan=kchan))
        return znc.CONTINUE

    def OnQuit(self, inick, qmsg, vchans):
        qnick = inick.GetNick()
        if qnick in self.nickcount:
            del self.nickcount[qnick]
            if self.nvget("debug"):
                self.PutModule("qcleared      {nick}".format(nick=qnick))
        return znc.CONTINUE

    def OnIRCDisconnected(self):
        self.nickcount.clear()
        return znc.CONTINUE

    def OnUserPart(self, channel, message):
        if channel in self.nvget("chans"):
            self.PutModule("In chans")
            for nick in self.nickcount:
                self.PutModule("f1 {}".format(nick))
                self.PutModule(str(self.nickcount))
                if channel.s in self.nickcount[nick]:
                    self.PutModule("matched")
                    del self.nickcount[nick][channel.s]
                    self.PutModule("deleted")
                    if self.nickcount[nick] == {}:
                        del self.nickcount[nick]
                        self.PutModule("cleared empty nick")

    def OnModCommand(self, command):
        cmd = command.split()
        if cmd[0] == "addchan":
            if cmd[1] not in self.nvget("chans"):
                self.nvappend("chans", cmd[1].lower())
                self.PutModule("{} added to enforced channels".format(cmd[1]))
            else:
                self.PutModule("{cmd} is already in the enforced channel list".format(cmd=cmd[1]))
            return znc.CONTINUE

        elif cmd[0] == "delchan":
            try:
                self.nvremove("chans", cmd[1].lower())
                self.PutModule("{cmd} removed from enforced channel list".format(cmd=cmd[1]))
            except ValueError:
                self.PutModule("Channel not found in enforced channel list")

        elif cmd[0] == "lchan":
            if self.nvget("chans"):
                self.PutModule("Currently enforced channels: {chans}".format(chans=" ".join(self.nvget("chans"))))
            else:
                self.PutModule("The enforced channel list is empty")
            return znc.CONTINUE

        elif cmd[0] == "clchan":
            self.nvset("chans", "")
            self.PutModule("Enforced channel list cleared")
            return znc.CONTINUE

        elif cmd[0] == "setcount":
            self.nvset("count", [cmd[1]])
            self.PutModule("Trigger count set to {count}".format(count=cmd[1]))
            return znc.CONTINUE

        elif cmd[0] == "getcount":
            try:
                self.PutModule("Current trigger is at {count}. Default is 10"
                               .format(count=self.nvgetint("count")))
            except IndexError:
                self.nvset("count", ["10"])
                self.PutModule("Current trigger is at {count}. Default is 10"
                               .format(count=self.nvgetint("count")))
            return znc.CONTINUE

        elif cmd[0] == "help":
            self.help_cmd()
            return znc.CONTINUE

        elif cmd[0] == "addexempt":
            if cmd[1] in self.vexempts:
                if cmd[1] in self.nvget("exempts"):
                    self.PutModule("{cmd} is already in the exempt list"
                                   .format(cmd=cmd[1]))
                else:
                    self.nvappend("exempts", cmd[1])
                    self.PutModule("{cmd} added to exempt list".format(
                        cmd=cmd[1]))

            else:
                self.PutModule("{cmd} is not a valid exempt, valid exempts "
                               "are: {vexempts}".format(cmd=cmd[1],
                                                        vexempts=" ".join(
                                                            self.vexempts)))
            return znc.CONTINUE

        elif cmd[0] == "delexempt":
            try:
                self.nvremove("exempts", cmd[1])
                self.PutModule("{cmd} removed from exempt list".format(
                    cmd=cmd[1]))
            except ValueError:
                if cmd[1] in self.vexempts:
                    self.PutModule("{cmd} not found in except list".format(
                        cmd=cmd[1]))
                else:
                    self.PutModule("{cmd} is not a valid exempt, valid "
                                   "exempts are: {vexempts}".format(cmd=cmd[1],
                                                                    vexempts=" ".join(self.vexempts)))
            return znc.CONTINUE

        elif cmd[0] == "lexempt":
            if self.nvget("exempts"):
                self.PutModule("Current exempt list is: {list}. Default is op "
                               "hop voice"
                               .format(list=" ".join(self.nvget("exempts"))))
            else:
                self.PutModule("Current exempt list is empty. Default is op "
                               "hop voice")
            return znc.CONTINUE

        elif cmd[0] == "clexempt":
            self.nvset("exempts", [""])
            self.PutModule("exempt list cleared")

        elif cmd[0] == "addmexempt":
            self.nvappend("mexempts", cmd[1])
            self.PutModule("{cmd} added to exempted mask list".format(
                cmd=cmd[1]))
            return znc.CONTINUE

        elif cmd[0] == "delmexempt":
            try:
                self.nvremove("mexempts", cmd[1])
                self.PutModule("{cmd} removed from mask exempt list".format(
                    cmd=cmd[1]))
            except ValueError:
                self.PutModule("{cmd} not found in mask exempt list".format(
                    cmd=cmd[1]))

        elif cmd[0] == "lmexempt":
            self.PutModule("Current mask exempt list is: {list}".format(
                list=" ".join(self.nvget("mexempts"))))

        elif cmd[0] == "clmexempt":
            self.nvset("mexempts", [""])
            self.PutModule("Mask exempt list has been cleared")

        elif cmd[0] == "reset":
            self.nvset("firstrun", "")
            self.OnLoad(None, None)

        elif cmd[0] == "addcmd":
            arg = " ".join(cmd[1:])
            if not self.nv.get("commands", ""):
                self.nv["commands"] = arg
                self.PutModule(str(self.nv["commands"]))
                self.PutModule("{} added to command list".format(arg))
            else:
                temp = self.nv["commands"].split("\r\n")
                temp.append(arg)
                self.nv[self.makeCString("commands")] = "\r\n".join(temp)
                self.PutModule("{} added to command list".format(arg))

        elif cmd[0] == "delcmd":
            if not self.nv.get("commands", ""):
                self.PutModule("Command list is empty, defaults are ...")
            else:
                arg = " ".join(cmd[1:])
                temp = self.nv["commands"].split("\r\n")
                temp.remove(arg)
                self.nv["commands"] = "\r\n".join(temp)
                self.PutModule("{} removed from command list".format(str(arg)))

        elif cmd[0] == "clcmd":
            self.nvset("commands", "")
            self.PutModule("Command list cleared")

        elif cmd[0] == "lcmd":
            self.PutModule("Current command list is:  " +
                           str(self.nv["commands"].split("\r\n")))

        elif cmd[0] == "timeout":
            if len(cmd) >= 2:
                try:
                    self.nvsetint("timeout", int(cmd[1]))
                    self.PutModule("Timeout for multi line pings set "
                                   "to {} seconds".format(cmd[1]))
                except ValueError:
                    self.PutModule("{} is not a valid number".format(cmd[1]))
            else:
                self.PutModule("Current timeout is {} seconds. default is "
                               "60 seconds".format(self.nvgetint("timeout")))

        elif cmd[0] == "debug":
            try:
                self.nvset("debug", [cmd[1]])
                self.PutModule("debug set to {}".format(cmd[1]))
            except ValueError:
                self.PutModule("an argument is required")

        elif cmd[0] == "opchanadd":
            if len(cmd) < 2:
                self.PutModule("Arguments are required in the format "
                               "\"opchanadd channel opchan\"")
            else:
                self.nvappend("opchans", ":".join(cmd[1:]))
                self.PutModule("Added to op chan list")

        elif cmd[0] == "opchandel":
            if len(cmd) < 2:
                self.PutModule("Arguments are required in the format "
                               "\"opchandel channel opchan\"")
            else:
                self.nvremove("opchans", ":".join(cmd[1:]))
                self.PutModule("Removed from op chan list, note that this does"
                               " not stop channel enforcement")

        elif cmd[0] == "opchanlist":
            if self.nvget("opchans"):
                for chanstr in self.nvget("opchans"):
                    opchanl = chanstr.split(":")
                    self.PutModule("{} : {} |".format(opchanl[0], opchanl[1]))
            else:
                self.PutModule("No op chans currently set")

        elif cmd[0] == "addnickignore":
            if len(cmd) < 2:
                pass
            else:
                self.nvappend("nickignore", cmd[1])
                self.PutModule("{} added to ignored nicks".format(cmd[1]))

        elif cmd[0] == "delnickignore":
            if len(command) < 2:
                self.putModule("I need an argument")
            else:
                self.nvremove("nickignore", cmd[1])
                self.putmodule("{} removed from ignored nicks".format(cmd[1]))

        elif cmd[0] == "lnickignore":
            self.PutModule(str(self.nvget("nickignore")))


        else:
            self.PutModule("Unknown command, try help")
            return znc.CONTINUE

    def help_cmd(self):
        help_table = znc.CTable()
        help_table.AddColumn("Command")
        help_table.AddColumn("Arguments")
        help_table.AddColumn("Description")
        help_table.AddRow()
        help_table.SetCell("Command", "addchan")
        help_table.SetCell("Arguments", "Channel Name")
        help_table.SetCell("Description", "Adds a channel to the enforced "
                                          "channel list")
        help_table.AddRow()
        help_table.SetCell("Command", "delchan")
        help_table.SetCell("Arguments", "Channel Name")
        help_table.SetCell("Description", "Removes a channel from the "
                                          "enforced channel list")
        help_table.AddRow()
        help_table.SetCell("Command", "lchan")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Lists all channels in the enforced"
                                          " channel list")
        help_table.AddRow()
        help_table.SetCell("Command", "clchan")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Clears the enforced channel list")
        help_table.AddRow()
        help_table.SetCell("Command", "setcount")
        help_table.SetCell("Arguments", "Number")
        help_table.SetCell("Description", "Sets the number of highlights that "
                                          "triggers action, by default, this "
                                          "is 10")
        help_table.AddRow()
        help_table.SetCell("Command", "getcount")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "gets the current number of "
                                          "highlights required to trigger "
                                          "action")
        help_table.AddRow()
        help_table.SetCell("Command", "addexempt")
        help_table.SetCell("Arguments", "{}".format(" ".join(self.vexempts)))
        help_table.SetCell("Description", "Adds to the list of exempted modes,"
                                          " if you have the set mode and "
                                          "mass highlight, it will be logged "
                                          "but no action will take place")
        help_table.AddRow()
        help_table.SetCell("Command", "delexempt")
        help_table.SetCell("Arguments", "{}".format(" ".join(self.vexempts)))
        help_table.SetCell("Description", "Removes an exempt from the list")
        help_table.AddRow()
        help_table.SetCell("Command", "lexempt")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Lists the current exempt list")
        help_table.AddRow()
        help_table.SetCell("Command", "clexempt")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Clears the exempt list, the default"
                                          " is op hop voice")
        help_table.AddRow()
        help_table.SetCell("Command", "addmexempt")
        help_table.SetCell("Arguments", "mask")
        help_table.SetCell("Description", "Adds a mask that is exempt from "
                                          "action, in the format "
                                          "nick!user@host, wildcards are "
                                          "accepted")
        help_table.AddRow()
        help_table.SetCell("Command", "delmexempt")
        help_table.SetCell("Arguments", "mask")
        help_table.SetCell("Description", "Removes a mask from the mask "
                                          "exempt list")
        help_table.AddRow()
        help_table.SetCell("Command", "lmexempt")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Lists the current mask exempts")
        help_table.AddRow()
        help_table.SetCell("Command", "clmexempt")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Clears the mask exempt list")
        help_table.AddRow()
        help_table.SetCell("Command", "reset")
        help_table.SetCell("arguments", "None")
        help_table.SetCell("Description", "Resets everything to default values")
        help_table.AddRow()
        help_table.SetCell("Command", "addcmd")
        help_table.SetCell("Arguments", "raw line")
        help_table.SetCell("Description", "Adds a raw line to be sent when the"
                                          " script is triggered. you can use "
                                          "{nick} for the nickname, {chan} for"
                                          " the channel that triggered"
                                          "a response, and {mask} for the "
                                          "nick's mask in the format *!*@host")
        help_table.AddRow()
        help_table.SetCell("Command", "delcmd")
        help_table.SetCell("Arguments", "raw line")
        help_table.SetCell("Description", "Removes a line from the command "
                                          "list")
        help_table.AddRow()
        help_table.SetCell("Command", "lcmd")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Lists all the current commands sent"
                                          " when the script is triggered")
        help_table.AddRow()
        help_table.SetCell("Command", "clcmd")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Clears the command list")
        help_table.AddRow()
        help_table.SetCell("Command", "timeout")
        help_table.SetCell("Arguments", "number or nothing")
        help_table.SetCell("Description", "If not given an argument, returns "
                                          "the current multi line timeout, "
                                          "that is,the amount of time before "
                                          "someone is cleared from the list "
                                          "of pings")
        self.PutModule(help_table)

    # below are functions for working with stored data, as I want lists and I
    # can only store strings
    def makeCString(self, string):
        cstring = znc.String()
        cstring.s = string
        return cstring.s

    def nvget(self, key):
        if key in self.nv:
            if self.nv[self.makeCString(key)] == ["yes"]:
                return True
            elif self.nv[self.makeCString(key)] == ["no"]:
                return False
            return self.nv[self.makeCString(key)].split()
        else:  # If the requested key
            # doesn't exist, initiate it
            # and return
            self.nv[self.makeCString(key)] = ""
            return [""]

    def nvgetint(self, key):
        if key in self.nv:
            return int(self.nv[self.makeCString(key)])
        else:
            return 0

    def nvsetint(self, key, data):
        self.nv[self.makeCString(key)] = str(data)

    def nvset(self, key, data):
        self.nv[self.makeCString(key)] = " ".join(data)

    def nvremove(self, key, data):
        temp = self.nvget(key)
        temp.remove(data)
        self.nvset(key, temp)

    def nvappend(self, key, data):
        temp = self.nvget(key)
        temp.append(data)
        self.nvset(key, temp)

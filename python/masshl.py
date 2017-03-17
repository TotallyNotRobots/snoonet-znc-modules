import znc
from fnmatch import fnmatch
import time
import math
# VER: 1.7 - added the ability to set opchans, which get status updates like the user does

# TODO: Add a list validate function that runs hourly, checks timeouts etc.


class masshl(znc.Module):
    description = "monitoring of mass highlights and automatic action"
    module_types = [znc.CModInfo.NetworkModule]

    vexempts = ["op", "hop", "voice"]   # Valid exempt list

    def OnLoad(self, args, msg):
        self.PutModule("masshl loaded")
        self.nickcount = {}
        if not self.nv.get("firstrun"):     # checking if this is our first run and if so, setting defaults
            self.nvset("chans", [""])
            self.nvset("exempts", ["op", "hop", "voice"])
            self.nvset("mexempts", [""])
            self.nvsetint("count", 10)
            self.nv["commands"] = "MODE {chan} +b {mask}\r\nKICK {chan} {nick} :Do not Mass highlight in {chan}"
            self.nvset("debug", ["no"])
            self.nvsetint("timeout", 60)
            self.nvset("firstrun", ["no"])
            self.nvset("opchans", [""])
        return True

    def OnChanMsg(self, inick, ichan, msg):
        if ichan.GetName() in self.nvget("chans"):
            bmsg = msg.s.lower()        # gets the actual string of the message and lowers it
            nick = inick.GetNick()
            chan = ichan.GetName()
            nicks = list(map(lambda n: n.GetNick().lower(), ichan.GetNicks().values()))   # List of nicks in the channel

            # checks the message contents vs the list of nicks
            checkednicks = set(filter(lambda n: n in bmsg, nicks))
            count = len(checkednicks)
            # Check the current count against the configured max, if its the same or bigger, send configured commands

            if count >= self.nvgetint("count"):
                self.tryban(inick, ichan, count)

            elif count <= 9 and count != 0:
                # checking if we've seen this nick in this channel before, if not,
                # check if they match anything in the mask exempt list, if not, initialise their var and set it to 1
                if not self.nickcount.get(nick):
                    if self.nvget("mexempts") and self.checkmexempts(inick):
                        return znc.CONTINUE
                    else:
                        self.nickcount[nick] = {chan: {"count": count, "lping": time.time()}}
                        if self.nvget("debug"):
                            self.PutModule("1 seen        {nick}".format(nick=(nick + " " + chan)))

                elif chan not in self.nickcount[nick]:
                    if self.nvget("mexempts") and self.checkmexempts(inick):
                        return znc.CONTINUE
                    else:
                        self.nickcount[nick][chan] = {"count": count, "lping": time.time()}
                        if self.nvget("debug"):
                            self.PutModule("1 seen      {nick}".format(nick=(nick + " " + chan)))

                # if we have seen them, increment their count
                elif self.nickcount[nick][chan]:
                    # check the time against the configured timeout, and delete the user if its more than the timeout
                    if (time.time() - self.nickcount[nick][chan]["lping"]) >= self.nvgetint("timeout"):
                        self.PutModule("timeout ({time})  {nick}".format(
                            time=str(self.nvgetint("timeout")), nick=(nick + " " + chan)))
                        del self.nickcount[nick][chan]
                    elif not self.checkmexempts(inick):
                        self.nickcount[nick][chan]["count"] += 1
                        if self.nvget("debug"):
                            self.PutModule(
                                "{} seen        {nick}".format(self.nickcount[nick][chan]["count"],
                                                                     nick=(nick + " " + chan)))
                    if nick in self.nickcount:
                        if chan in self.nickcount[nick]:
                            # if they hit the set count, try to ban them
                            if self.nickcount[nick][chan]["count"] >= self.nvgetint("count"):
                                self.tryban(inick, ichan, self.nickcount[nick][chan]["count"])
                                del self.nickcount[nick][chan]
                            elif self.nickcount[nick][chan]["count"] == math.floor((self.nvgetint("count")/4)*3):
                                self.sendtoops(chan,
                                               "{nick} is nearing threshold in {chan}. count is {count}, threshold is {thr}".format(
                                                   nick=nick, chan=chan, count=str(self.nickcount[nick][chan]["count"]),
                                               thr=str(self.nvgetint("count"))))

            if count == 0 and nick in self.nickcount:
                if chan in self.nickcount[nick]:
                    del self.nickcount[nick][chan]
                    if self.nvget("debug"):
                        self.PutModule("cleared       {nick}".format(nick=(nick + " " + chan)))

            return znc.CONTINUE

    def tryban(self, inick, chan, count):

        # check if user has permission to ban in the channel
        if chan.HasPerm(ord(znc.CChan.Op)) or chan.HasPerm(ord(znc.CChan.HalfOp)) \
                or chan.HasPerm(ord(znc.CChan.Admin)):

            # checking if the incoming user has op and whether or not we exempt ops
            if inick.HasPerm(ord(znc.CChan.Op)) and "op" in self.nvget("exempts"):
                self.PutModule("MHL from {nick} in {chan}. Count was {count}. User is exempt (op)"
                               .format(nick=inick.GetNick(), chan=chan.GetName(), count=str(count)))
                self.sendtoops(chan.GetName(), "MHL from {nick} in {chan}. Count was {count}. User is exempt (op)"
                               .format(nick=inick.GetNick(), chan=chan.GetName(), count=str(count)))
                return znc.CONTINUE

            elif inick.HasPerm(ord(znc.CChan.HalfOp)) and "hop" in self.nvget("exempts"):
                self.PutModule("MHL from {nick} in {chan}. Count was {count}. User is exempt (hop)"
                               .format(nick=inick.GetNick(), chan=chan.GetName(), count=str(count)))
                self.sendtoops(chan.GetName(), "MHL from {nick} in {chan}. Count was {count}. User is exempt (hop)"
                               .format(nick=inick.GetNick(), chan=chan.GetName(), count=str(count)))
                return znc.CONTINUE

            elif inick.HasPerm(ord(znc.CChan.Voice)) and "voice" in self.nvget("exempts"):
                self.PutModule("MHL from {nick} in {chan}. Count was {count}. User is exempt (voice)"
                               .format(nick=inick.GetNick(), chan=chan.GetName(), count=str(count)))
                self.sendtoops(chan.GetName(), "MHL from {nick} in {chan}. Count was {count}. User is exempt (voice)"
                               .format(nick=inick.GetNick(), chan=chan.GetName(), count=str(count)))
                return znc.CONTINUE

            else:
                # checking each mask exempt against the mask exempt list
                for emask in self.nvget("mexempts"):
                    if fnmatch(inick.GetHostMask().lower(), emask.lower()):
                        self.PutModule(
                            "MHL from {nick} in {chan}. Count was {count}. User is exempt (matches {mask})"
                            .format(nick=inick.GetNick(), chan=chan.GetName(), count=str(count)
                                    , mask=emask))
                        self.sendtoops(chan.GetName(),
                            "MHL from {nick} in {chan}. Count was {count}. User is exempt (matches {mask})".format(
                            nick=inick.GetNick(), chan=chan.GetName(), count=str(count), mask=emask))
                        return znc.CONTINUE

                banmask = "*!*@" + inick.GetHost()

                self.PutModule("MHL from {nick} in {chan}. Count was {count}. Ban sent"
                               .format(nick=inick.GetNick(), chan=chan.GetName(), count=str(count)))

                self.sendtoops(chan.GetName(), "MHL from {nick} in {chan}. Count was {count}. Ban sent".format(
                    nick=inick.GetNick(), chan=chan.GetName(), count=str(count)))

                self.PutIRC(self.nv["commands"].format(nick=inick.GetNick(), chan=chan.GetName(), mask=banmask,
                                                       count=str(count)))
        else:
            self.PutModule("MHL from {nick} in {chan}. Count was {count}. We're not opped, no action taken"
                           .format(nick=inick.GetNick(), chan=chan.GetName(), count=str(count)))

    def sendtoops(self, chan, msg):
        self.PutModule("sending to opchan")
        for opchanstr in self.nvget("opchans"):
            self.PutModule("going over list")
            if chan in opchanstr.split(":"):
                self.PutModule("match found")
                self.PutIRC("PRIVMSG {opchan} :***MASSHL {msg}".format(opchan=opchanstr.split(":")[1], msg=msg))

    def checkmexempts(self, nick):
        ecount = 0
        for exempt in self.nvget("mexempts"):
            if fnmatch(nick.GetHostMask().lower(), exempt.lower()):
                if self.nvget("debug"):
                    self.PutModule("fnmatch       ({}, {})".format(nick.GetHostMask().lower(), exempt.lower()))
                return True
            else:
                ecount += 1
                if ecount >= len(self.nvget("mexempts")):
                    return False

    # actions get included in scanning
    def OnChanAction(self, inick, ichan, msg):
        self.OnChanMsg(inick, ichan, msg)

    def OnNick(self, onick, newnick, vchans):
        oldnick = onick.GetNick()
        if oldnick in self.nickcount:
            del self.nickcount[oldnick]
            if self.nvget("debug"):
                self.PutModule("ncleared      {nnick} {onick}".format(nnick=newnick.s, onick=oldnick))
        return znc.CONTINUE

    def OnPart(self, inick, ichan, pmsg):
        if ichan.GetName() in self.nvget("chans"):
            pnick = inick.GetNick()
            pchan = ichan.GetName()

            if pnick in self.nickcount:
                if pchan in self.nickcount[pnick]:
                    del self.nickcount[pnick][pchan]
                    if self.nvget("debug"):
                        self.PutModule("pcleared      {nick}".format(nick=(pnick + " " + pchan)))
        return znc.CONTINUE

    def OnKick(self, opnick, knick, ichan, kmsg):
        if ichan.GetName() in self.nvget("chans"):
            kchan = ichan.GetName()

            if knick in self.nickcount:
                if kchan in self.nickcount[knick]:
                    del self.nickcount[knick][kchan]
                    if self.nvget("debug"):
                        self.PutModule("kcleared      {nick}".format(nick=(knick + " " + kchan)))
        return znc.CONTINUE

    def OnQuit(self, inick, qmsg, vchans):
        qnick = inick.GetNick()
        if qnick in self.nickcount:
            del self.nickcount[qnick]
            if self.nvget("debug"):
                self.PutModule("qcleared      {nick}".format(nick=(qnick)))
        return znc.CONTINUE

    def OnIRCDisconnected(self):
        self.nickcount = {}
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
        commands = ["addchan", "delchan", "lchan", "clchan", "setcount", "getcount", "addexempt", "delexempt", "lexempt"
                    , "clexempt", "addmexempt", "delmexempt", "lmexempt", "clmexempt", "reset", "help",
                    "addcmd", "delcmd", "lcmd", "clcmd", "debug", "timeout", "opchanadd", "opchanlist", "opchandel"]
        if cmd[0] in commands:
            if cmd[0] == "addchan":
                if cmd[1] not in self.nvget("chans"):
                    self.nvappend("chans", cmd[1])
                    self.PutModule("{} added to enforced channels".format(cmd[1]))
                else:
                    self.PutModule("{cmd} is already in the enforced channel list".format(cmd=cmd[1]))
                return znc.CONTINUE

            elif cmd[0] == "delchan":
                try:
                    self.nvremove("chans", cmd[1])
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
                    self.PutModule("Current trigger is at {count}. Default is 10".format(count=self.nvgetint("count")))
                except IndexError:
                    self.nvset("count", ["10"])
                    self.PutModule("Current trigger is at {count}. Default is 10".format(count=self.nvgetint("count")))
                return znc.CONTINUE

            elif cmd[0] == "help":
                self.help_cmd()
                return znc.CONTINUE

            elif cmd[0] == "addexempt":
                if cmd[1] in self.vexempts:
                    if cmd[1] in self.nvget("exempts"):
                        self.PutModule("{cmd} is already in the exempt list".format(cmd=cmd[1]))
                    else:
                        self.nvappend("exempts", cmd[1])
                        self.PutModule("{cmd} added to exempt list".format(cmd=cmd[1]))

                else:
                    self.PutModule("{cmd} is not a valid exempt, valid exempts are: {vexempts}"
                                   .format(cmd=cmd[1], vexempts=" ".join(self.vexempts)))
                return znc.CONTINUE

            elif cmd[0] == "delexempt":
                try:
                    self.nvremove("exempts", cmd[1])
                    self.PutModule("{cmd} removed from exempt list".format(cmd=cmd[1]))
                except ValueError:
                    if cmd[1] in self.vexempts:
                        self.PutModule("{cmd} not found in except list".format(cmd=cmd[1]))
                    else:
                        self.PutModule("{cmd} is not a valid exempt, valid exempts are: {vexempts}"
                                       .format(cmd=cmd[1], vexempts=" ".join(self.vexempts)))
                return znc.CONTINUE

            elif cmd[0] == "lexempt":
                if self.nvget("exempts"):
                    self.PutModule("Current exempt list is: {list}. Default is op hop voice"
                                   .format(list=" ".join(self.nvget("exempts"))))
                else:
                    self.PutModule("Current exempt list is empty. Default is op hop voice")
                return znc.CONTINUE

            elif cmd[0] == "clexempt":
                self.nvset("exempts", [""])
                self.PutModule("exempt list cleared")

            elif cmd[0] == "addmexempt":
                self.nvappend("mexempts", cmd[1])
                self.PutModule("{cmd} added to exempted mask list".format(cmd=cmd[1]))
                return znc.CONTINUE

            elif cmd[0] == "delmexempt":
                try:
                    self.nvremove("mexempts", cmd[1])
                    self.PutModule("{cmd} removed from mask exempt list".format(cmd=cmd[1]))
                except ValueError:
                    self.PutModule("{cmd} not found in mask exempt list".format(cmd=cmd[1]))

            elif cmd[0] == "lmexempt":
                self.PutModule("Current mask exempt list is: {list}".format(list=" ".join(self.nvget("mexempts"))))

            elif cmd[0] == "clmexempt":
                self.nvset("mexempts", [""])
                self.PutModule("Mask exempt list has been cleared")

            elif cmd[0] == "reset":
                # self.nv.clear()
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
                self.PutModule("Current command list is:  " + str(self.nv["commands"].split("\r\n")))

            elif cmd[0] == "timeout":
                if len(cmd) >= 2:
                    try:
                        self.nvsetint("timeout", int(cmd[1]))
                        self.PutModule("Timeout for multi line pings set to {} seconds".format(cmd[1]))
                    except ValueError:
                        self.PutModule("{} is not a valid number".format(cmd[1]))
                else:
                    self.PutModule("Current timeout is {} seconds. default is 60 seconds"
                                   .format(self.nvgetint("timeout")))

            elif cmd[0] == "debug":
                try:
                    self.nvset("debug", [cmd[1]])
                    self.PutModule("debug set to {}".format(cmd[1]))
                except ValueError:
                    self.PutModule("an argument is required")

            elif cmd[0] == "opchanadd":
                if len(cmd) < 2:
                    self.PutModule("Arguments are required in the format \"opchanadd channel opchan\"")
                else:
                    self.nvappend("opchans", ":".join(cmd[1:]))
                    self.PutModule("Added to op chan list")

            elif cmd[0] == "opchandel":
                if len(cmd) < 2:
                    self.PutModule("Arguments are required in the format \"opchandel channel opchan\"")
                else:
                    self.nvremove("opchans", ":".join(cmd[1:]))
                    self.PutModule("Removed from op chan list, note that this does not stop channel enforcement")

            elif cmd[0] == "opchanlist":
                if self.nvget("opchans"):
                    for chanstr in self.nvget("opchans"):
                        opchanl = chanstr.split(":")
                        self.PutModule("{} : {} |".format(opchanl[0], opchanl[1]))
                else:
                    self.PutModule("No op chans currently set")


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
        help_table.SetCell("Description", "Adds a channel to the enforced channel list")
        help_table.AddRow()
        help_table.SetCell("Command", "delchan")
        help_table.SetCell("Arguments", "Channel Name")
        help_table.SetCell("Description", "Removes a channel from the enforced channel list")
        help_table.AddRow()
        help_table.SetCell("Command", "lchan")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Lists all channels in the enforced channel list")
        help_table.AddRow()
        help_table.SetCell("Command", "clchan")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Clears the enforced channel list")
        help_table.AddRow()
        help_table.SetCell("Command", "setcount")
        help_table.SetCell("Arguments", "Number")
        help_table.SetCell("Description", "Sets the number of highlights that triggers action, by default, this is 10")
        help_table.AddRow()
        help_table.SetCell("Command", "getcount")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "gets the current number of highlights required to trigger action")
        help_table.AddRow()
        help_table.SetCell("Command", "addexempt")
        help_table.SetCell("Arguments", "{}".format(" ".join(self.vexempts)))
        help_table.SetCell("Description", "Adds to the list of exempted modes, if you have the set mode and "
                                          "mass highlight, it will be logged but no action will take place")
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
        help_table.SetCell("Description", "Clears the exempt list, the default is op hop voice")
        help_table.AddRow()
        help_table.SetCell("Command", "addmexempt")
        help_table.SetCell("Arguments", "mask")
        help_table.SetCell("Description", "Adds a mask that is exempt from action, in the format nick!user@host,"
                                          " wildcards are accepted")
        help_table.AddRow()
        help_table.SetCell("Command", "delmexempt")
        help_table.SetCell("Arguments", "mask")
        help_table.SetCell("Description", "Removes a mask from the mask exempt list")
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
        help_table.SetCell("Description", "Adds a raw line to be sent when the script is triggered."
                                          " you can use {nick} for the nickname, {chan} for the channel that triggered"
                                          "a response, and {mask} for the nick's mask in the format *!*@host")
        help_table.AddRow()
        help_table.SetCell("Command", "delcmd")
        help_table.SetCell("Arguments", "raw line")
        help_table.SetCell("Description", "Removes a line from the command list")
        help_table.AddRow()
        help_table.SetCell("Command", "lcmd")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Lists all the current commands sent when the script is triggered")
        help_table.AddRow()
        help_table.SetCell("Command", "clcmd")
        help_table.SetCell("Arguments", "None")
        help_table.SetCell("Description", "Clears the command list")
        help_table.AddRow()
        help_table.SetCell("Command", "timeout")
        help_table.SetCell("Arguments", "number or nothing")
        help_table.SetCell("Description", "If not given an argument, returns the current multi line timeout, that is,"
                                          "the amount of time before someone is cleared from the list of pings")
        self.PutModule(help_table)

    # below are functions for working with stored data, as I want lists and I can only store strings
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
        else:                                    # If the requested key doesn't exist, initiate it and return
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

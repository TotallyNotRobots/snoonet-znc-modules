import znc

network = "Snoonet"
channel = "##bnc"
part = "PART " + channel

class forcechan(znc.Module):
    module_types = [znc.CModInfo.GlobalModule]
    description = "Forces users to remain in ##bnc"

    def OnLoad(self, args, message):
        return True

    def OnUserPart(self, channel, message):
        if channel == forcedchan:
            return znc.HALTCORE

    def OnSendToIRC(self, line):
        if part in str(line):
            self.forceChan()
            return znc.HALTCORE

    def forceChan(self):
        users = znc.CZNC.Get().GetUserMap()
        for user in users.items():

            net = user[1].FindNetwork(network)

            if net:
                chan = net.FindChan(channel)
                if not chan:
                    net.AddChan(channel, True)

    def OnModCommand(self, command):
        if self.GetUser().IsAdmin():
            if command.split()[0] == "forcechan":
                self.forceChan()
                self.PutModule("All users on network " + network + " forced into channel " + channel)
        else:
            self.PutModule("Access denied.")

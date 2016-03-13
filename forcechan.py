import znc

network = "Snoonet"
channel = "##bnc"
part = "PART " + channel


class forcechan(znc.Module):

    module_types = [znc.CModInfo.GlobalModule]
    description = "Forces users to remain in the configured channel"

    def OnLoad(self, args, message):
        return True

    def OnUserPart(self, chan, message):
        if channel == chan:
            return znc.HALTCORE

    def OnSendToIRC(self, line):
        if part in str(line):
            self.force_chan()
            return znc.HALTCORE

    def force_chan(self):
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
                self.force_chan()
                self.PutModule("All users on network " + network +
                               " forced into channel " + channel)
        else:
            self.PutModule("Access denied.")

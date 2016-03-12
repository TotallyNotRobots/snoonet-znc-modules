import znc

class checknetwork(znc.Module):
    module_types = [znc.CModInfo.GlobalModule]
    description = "Checks that a specified network for each user exists"

    def CheckNetwork(self, network):
        users = znc.CZNC.Get().GetUserMap()
        for user in users.items():

            net = user[1].FindNetwork(network)

            if not net:
                self.PutModule(user[0] + " network " + network +  " not found")

    def OnModCommand(self, command):
        if command.split()[0] == "checknetwork":
            self.CheckNetwork(command.split()[1])

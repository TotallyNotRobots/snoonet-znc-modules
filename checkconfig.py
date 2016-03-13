import znc

class checkconfig(znc.Module):
    module_types = [znc.CModInfo.GlobalModule]
    description = "Checks that a module is loaded for a user"

    def check_network(self, network):
        users = znc.CZNC.Get().GetUserMap()
        count = 0
        for user in users.items():

            net = user[1].FindNetwork(network)

            if not net:
                self.PutModule("AddNetwork " + user[0] + " " + network)
                count += 1

        self.PutModule("Network check complete for network " + network + " (" + str(count) + " missing)")

    def check_chan(self, network, channel):
        users = znc.CZNC.Get().GetUserMap()
        count = 0
        for user in users.items():

            net = user[1].FindNetwork(network)

            if net:
                chan = net.FindChan(channel)
                if not chan:
                    self.PutModule("AddChan " + user[0] + " " + network + " " + channel)
                    count += 1

        self.PutModule("Channel check complete for channel " + channel + " in network " + network + " (" + str(count) + " missing)")

    def check_user_module(self, module):
        users = znc.CZNC.Get().GetUserMap()
        count = 0
        for user in users.items():

            loaded_user_mods = []
            for mod in user[1].GetModules():
                loaded_user_mods.append(mod.GetModName())

            if module not in loaded_user_mods:
                self.PutModule("LoadModule " + user[0] + " " + module)
                count += 1

        self.PutModule("User module check complete for module " + module + " (" + str(count) + " missing)")

    def check_network_module(self, network, module):
        users = znc.CZNC.Get().GetUserMap()
        count = 0
        for user in users.items():

            net = user[1].FindNetwork(network)

            if net:
                loaded_net_mods = []
                for mod in net.GetModules():
                    loaded_net_mods.append(mod.GetModName())

                if module not in loaded_net_mods:
                    self.PutModule("LoadNetModule " + user[0] + " " + network + " " + module)
                    count += 1

        self.PutModule("Network module check complete for module " + module + " in network " + network + " (" + str(count) + " missing)")

    def OnModCommand(self, command):
        if self.GetUser().IsAdmin():
            if command.split()[0] == "checknetwork":
                self.check_network(command.split()[1])
            elif command.split()[0] == "checkchan":
                self.check_chan(command.split()[1], command.split()[2])
            elif command.split()[0] == "checkusermod":
                self.check_user_module(command.split()[1])
            elif command.split()[0] == "checknetmod":
                self.check_network_module(command.split()[1], command.split()[2])
        else:
            self.PutModule("Access denied.")

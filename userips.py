import znc

class userips(znc.Module):
    module_types = [znc.CModInfo.GlobalModule]
    description = "Shows IP addresses of connected users"

    def WebRequiresAdmin(self):
        return True

    def GetWebMenuTitle(self):
        return "User IPs"

    def OnWebRequest(self, sock, page, tmpl):

        users = znc.CZNC.Get().GetUserMap()

        for user in users.items():
            row = tmpl.AddRow("UserLoop")
            row["User"] = user[0]

            net = user[1].FindNetwork("Snoonet")
            try:
                clients = net.GetClients()
                out = ''
                for client in clients:
                    out += client.GetRemoteIP() + ' '

                row["IP"] = out
            except AttributeError:
                row["IP"] = "Network Not Found"

        return True

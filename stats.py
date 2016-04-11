import znc
import collections


class stats(znc.Module):

    module_types = [znc.CModInfo.GlobalModule]
    description = "Shows ZNC statistics"

    def WebRequiresAdmin(self):
        return True

    def GetWebMenuTitle(self):
        return "Statistics"

    def OnWebRequest(self, sock, page, tmpl):

        stats = collections.OrderedDict()
        stats['Users'] = 0
        stats['Online'] = 0
        stats['Offline'] = 0
        stats['Connections'] = 0
        stats['Networks'] = 0
        stats['Channels'] = 0

        users = znc.CZNC.Get().GetUserMap()

        for user in users.items():
            stats['Users'] += 1

            user_clients = user[1].GetAllClients()
            if user_clients:
                stats['Online'] += 1
            else:
                 stats['Offline'] += 1
            for client in user_clients:
                stats['Connections'] += 1

            nets = user[1].GetNetworks()
            for net in nets:
                stats['Networks'] += 1

                chans = net.GetChans()
                for chan in chans:
                    stats['Channels'] += 1


        for k,v in stats.items():
            row = tmpl.AddRow("StatsLoop")
            row["Statistic"] = str(k)
            row["Value"] = str(v)

        return True

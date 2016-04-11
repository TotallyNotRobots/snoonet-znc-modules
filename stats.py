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
        stats['User Count'] = 0
        stats['Online Count'] = 0
        stats['Offline Count'] = 0
        stats['Connection Count'] = 0

        users = znc.CZNC.Get().GetUserMap()

        for user in users.items():
            stats['User Count'] += 1

            user_clients = user[1].GetAllClients()
            if user_clients:
                stats['Online Count'] += 1
            else:
                 stats['Offline Count'] += 1
            for client in user_clients:
                stats['Connection Count'] += 1

        for k,v in stats.items():
            row = tmpl.AddRow("StatsLoop")
            row["Statistic"] = str(k)
            row["Value"] = str(v)

        return True

import znc

__version__ = "0.1.1"
__author__ = "linuxdaemon"
__last_update_author__ = "A_D"


class irccloud(znc.Module):
    description = "IRCCloud login"
    module_types = [znc.CModInfo.GlobalModule]
    if znc.VersionMajor == 1 and znc.VersionMinor >= 7:
        def OnSendToClientMessage(self, msg):
            client = msg.GetClient()
            if client.GetUser():
                return znc.CONTINUE

            if msg.GetCommand() == "464":
                client.PutClient(":server 001 {} :Hello, World! Now with ZNC 1.7+ support!".format(client.GetNick()))
                return znc.HALT

            return znc.CONTINUE
    else:
        def OnSendToClient(self, line, client):
            if client.GetUser():
                return znc.CONTINUE
            parts = str(line).split()
            cmd = parts.pop(0)

            if cmd.startswith(":"):
                cmd = parts.pop(0)

            if cmd == "464":
                # Send our own 001 to trick irccloud in to sending the perform
                client.PutClient(":server 001 {} :Hello, World!".format(client.GetNick()))
                return znc.HALT

            return znc.CONTINUE

import znc

__version__ = "0.1.0"
__author__ = "linuxdaemon"


class irccloud(znc.Module):
    description = "IRCCloud login"
    module_types = [znc.CModInfo.GlobalModule]

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

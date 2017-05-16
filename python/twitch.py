import znc

class twitch(znc.Module):
    description = "Adds support for Twitch.tv's custom ircv3 CAPs"
    module_types = [znc.CModInfo.NetworkModule]

    def __init__(self):
        self.caps = ["twitch.tv/membership"]

    def OnServerCapAvailable(self, cap):
        return str(cap).lower() in self.caps


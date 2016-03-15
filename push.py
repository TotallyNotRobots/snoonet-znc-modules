import znc
import requests

help_url = "https://snoonet.org/push"

class push(znc.Module):

    module_types = [znc.CModInfo.NetworkModule]
    description = "PushBullet module for BNC"

    def OnLoad(self, args, message):
        return True

    def OnChanMsg(self, nick, channel, message):
        if any(word in message.s for word in self.nv['highlight'].split(',')) or self.GetNetwork().GetIRCNick().GetNick() in message.s:
            self.check_send(channel, nick, message)

    def OnChanNotice(self, nick, channel, message):
        if any(word in message.s for word in self.nv['highlight'].split(',')) or self.GetNetwork().GetIRCNick().GetNick() in message.s:
            self.check_send(channel, nick, message)

    def OnPrivMsg(self, nick, message):
        self.check_send(None, nick, message)

    def OnPrivNotice(self, nick, message):
        self.check_send(None, nick, message)

    def check_send(self, channel, nick, message):
        if self.nv['token']:
            if not self.nv['away_only'] or self.nv['away_only'] == "no":
                self.send_message(channel, nick, message)
            elif self.nv['away_only'] == "yes":
                away = True
                for client in self.GetNetwork().GetClients():
                    if not client.IsAway():
                        away =  False
                        break
                if away:
                    self.send_message(channel, nick, message)

    def send_message(self, channel, nick, message):
        if channel:
            msg = channel.GetName() + " <" + nick.GetNick() + "> " + message.s
        else:
            msg = "<" + nick.GetNick() + "> " + message.s

        data = dict(type='note', title=msg, body=msg)
        requests.post('https://api.pushbullet.com/v2/pushes', auth = (self.nv['token'],''), data = data)

    def OnModCommand(self, command):
        if command.split()[0] == "set":
            try:
                if command.split()[1] == "token":
                    try:
                        self.nv['token'] = command.split()[2]
                        self.PutModule("Token set successfully.")
                    except:
                        self.nv['token'] = ''
                        self.PutModule("Token cleared.")
                elif command.split()[1] == "away_only":
                    try:
                        if command.split()[2] == "yes" or command.split()[2] == "no":
                            self.nv['away_only'] = command.split()[2]
                            self.PutModule("Away option set successfully.")
                        else:
                            self.PutModule("You must speficy either \'yes\' or \'no\'.")
                    except:
                        self.PutModule("You must speficy either \'yes\' or \'no\'.")
                else:
                    self.PutModule("Invalid option. Options are 'token' and 'away_only'. See " + help_url)
            except:
                self.PutModule("You must specify a configuration option. See " + help_url)
        elif command.split()[0] == "highlight":
                if command.split()[1] == "list":
                    try:
                        if self.nv['highlight']:
                            self.PutModule("Highlight list: " + self.nv['highlight'])
                        else:
                            self.PutModule("Highlight list empty.")
                    except:
                        self.PutModule("Highlight list empty.")
                elif command.split()[1] == "add":
                    try:
                        list = self.nv['highlight'].split(',')
                        if command.split()[2] not in list:
                            list.append(command.split()[2])
                            joined = ','.join(list)
                            self.nv['highlight'] = joined
                            self.PutModule(command.split()[2] + " added to highlight list.")
                        else:
                            self.PutModule(command.split()[2] + " already in highlight list.")
                    except:
                        try:
                            self.nv['highlight'] = command.split()[2]
                            self.PutModule(command.split()[2] + " added to highlight list.")
                        except:
                            self.PutModule("You must specify a single highlight word to add.")
                elif command.split()[1] == "del":
                    try:
                        if self.nv['highlight']:
                            list = self.nv['highlight'].split(',')
                            if command.split()[2] in list:
                                list.remove(command.split()[2])
                                joined = ','.join(list)
                                self.nv['highlight'] = joined
                                self.PutModule(command.split()[2] + " deleted from highlight list.")
                            else:
                                self.PutModule(command.split()[2] + " not in highlight list.")
                        else:
                            self.PutModule("Highlight list empty.")
                    except:
                        try:
                            if not command.split()[2]:
                                self.PutModule("You must specify a single highlight word to delete.")
                            else:
                                self.PutModule("Highlight list empty.")
                        except:
                            self.PutModule("You must specify a single highlight word to delete.")
                else:
                    self.PutModule("Invalid option. Options are 'add' and 'del'. See " + help_url)
        elif command.split()[0] == "test":
            data = dict(type='note', title="Test Message", body="This is a test message.")
            requests.post('https://api.pushbullet.com/v2/pushes', auth = (self.nv['token'],''), data = data)
            self.PutModule("Test message successfully sent.")
        else:
            self.PutModule("Invalid command. See " + help_url)

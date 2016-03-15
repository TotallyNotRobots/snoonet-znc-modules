import znc
import requests

help_url = "https://snoonet.org/push"

class push(znc.Module):

    module_types = [znc.CModInfo.NetworkModule]
    description = "PushBullet notifications"

    def OnLoad(self, args, message):
        return True

    def OnChanMsg(self, nick, channel, message):
        user_nick = self.GetNetwork().GetIRCNick().GetNick()
        msg = (message.s).lower()
        try:
            if (nick.GetNick()).lower() in map(str.lower, (self.nv['ignore']).split(',')):
                pass
            elif any(word.lower() in msg for word in (self.nv['highlight']).split(',')) or user_nick.lower() in msg:
                self.check_send(channel, nick, message)
        except:
            try:
                if any(word.lower() in msg for word in (self.nv['highlight']).split(',')) or user_nick.lower() in msg:
                    self.check_send(channel, nick, message)
            except:
                if user_nick.lower() in msg:
                    self.check_send(channel, nick, message)

    def OnChanNotice(self, nick, channel, message):
        user_nick = self.GetNetwork().GetIRCNick().GetNick()
        msg = (message.s).lower()
        try:
            if (nick.GetNick()).lower() in map(str.lower, (self.nv['ignore']).split(',')):
                pass
            elif any(word.lower() in msg for word in (self.nv['highlight']).split(',')) or user_nick.lower() in msg:
                self.check_send(channel, nick, message)
        except:
            try:
                if any(word.lower() in msg for word in (self.nv['highlight']).split(',')) or user_nick.lower() in msg:
                    self.check_send(channel, nick, message)
            except:
                if user_nick.lower() in msg:
                    self.check_send(channel, nick, message)

    def OnPrivMsg(self, nick, message):
        try:
            if (nick.GetNick()).lower() in map(str.lower, (self.nv['ignore']).split(',')):
                pass
        except:
            self.check_send(None, nick, message)

    def OnPrivNotice(self, nick, message):
        try:
            if not (nick.GetNick()).lower() in map(str.lower, (self.nv['ignore']).split(',')):
                self.check_send(None, nick, message)
        except:
            self.check_send(None, nick, message)

    def check_send(self, channel, nick, message):
        try:
            if self.nv['state'] == "on":
                try:
                    if self.nv['away'] == yes:
                        away = True
                        for client in self.GetNetwork().GetClients():
                            if not client.IsAway():
                                away =  False
                                break
                        if away:
                            self.send_message(channel, nick, message)
                except:
                    self.send_message(channel, nick, message)
        except:
            self.PutModule("Exception.")

    def send_message(self, channel, nick, message):
        ttl = ''
        if channel:
            msg = channel.GetName() + " <" + nick.GetNick() + "> " + message.s
            ttl = 'Highlight'
        else:
            msg = "<" + nick.GetNick() + "> " + message.s
            ttl = 'Private Message'

        try:
            if self.nv['private'] == 'no':
                ttl = msg
        except:
            pass

        data = dict(type = 'note', title = ttl, body = msg)
        requests.post('https://api.pushbullet.com/v2/pushes', auth = (self.nv['token'],''), data = data)

    def OnModCommand(self, command):
        if command.split()[0] == "enable" or command.split()[0] == "disable":
            if command.split()[0] == "enable":
                try:
                    if self.nv['token']:
                        self.nv['state'] = "on"
                        self.PutModule("Notifications enabled.")
                    else:
                        self.PutModule("You must set a token before enabling notifications.")
                except:
                    self.PutModule("You must set a token before enabling notifications.")
            elif command.split()[0] == "disable":
                self.nv['state'] = "off"
                self.PutModule("Notifications disabled.")

        elif command.split()[0] == "set":
            try:
                if command.split()[1] == "token":
                    try:
                        if self.nv['state'] == 'on':
                            self.PutModule("You must disable notifications before changing your token.")
                        else:
                            try:
                                self.nv['token'] = command.split()[2]
                                self.PutModule("Token set successfully.")
                            except:
                                self.nv['token'] = ''
                                self.PutModule("Token cleared.")
                    except:
                        try:
                            self.nv['token'] = command.split()[2]
                            self.PutModule("Token set successfully.")
                        except:
                            self.nv['token'] = ''
                            self.PutModule("Token cleared.")

                elif command.split()[1] == "away_only" or command.split()[1] == "private":
                    try:
                        if command.split()[2] == "yes" or command.split()[2] == "no":
                            self.nv[command.split()[1]] = command.split()[2]
                            self.PutModule(command.split()[1] + " option set to " + command.split()[2])
                        else:
                            self.PutModule("You must speciy either \'yes\' or \'no\'.")
                    except:
                        self.PutModule("You must specify either \'yes\' or \'no\'.")
                else:
                    self.PutModule("Invalid option. Options are 'token' and 'away_only'. See " + help_url)
            except:
                self.PutModule("You must specify a configuration option. See " + help_url)

        elif command.split()[0] == "highlight" or command.split()[0] == "ignore":
                cmd = command.split()[0]
                if command.split()[1] == "list":
                    try:
                        if self.nv[cmd]:
                            self.PutModule(cmd.title() + " list: " + (self.nv[cmd])[1:])
                        else:
                            self.PutModule(cmd.title() + " list empty.")
                    except:
                        self.PutModule(cmd.title() + " list empty.")
                elif command.split()[1] == "add":
                    try:
                        list = self.nv[cmd].split(',')
                        if command.split()[2] not in list:
                            list.append((command.split()[2]).lower())
                            joined = ','.join(list)
                            self.nv[cmd] = joined
                            self.PutModule(command.split()[2] + " added to " + cmd + " list.")
                        else:
                            self.PutModule(command.split()[2] + " already in " + cmd + " list.")
                    except:
                        try:
                            self.nv[cmd] = (command.split()[2]).lower()
                            self.PutModule(command.split()[2] + " added to " + cmd + " list.")
                        except:
                            self.PutModule("You must specify a single word or nick to add.")
                elif command.split()[1] == "del":
                    try:
                        if self.nv[cmd]:
                            list = self.nv[cmd].split(',')
                            if (command.split()[2]).lower() in list:
                                list.remove((command.split()[2]).lower())
                                joined = ','.join(list)
                                self.nv[cmd] = joined
                                self.PutModule(command.split()[2] + " deleted from " + cmd + " list.")
                            else:
                                self.PutModule(command.split()[2] + " not in " + cmd + " list.")
                        else:
                            self.PutModule(cmd.title() + " list empty.")
                    except:
                        try:
                            if not command.split()[2]:
                                self.PutModule("You must specify a single word or nick to delete.")
                            else:
                                self.PutModule(cmd.title() + " list empty.")
                        except:
                            self.PutModule("You must specify a single word or nick to delete.")
                else:
                    self.PutModule("Invalid option. Options are 'list', 'add', and 'del'. See " + help_url)

        elif command.split()[0] == "test":
            data = dict(type='note', title="Test Message", body="This is a test message.")
            requests.post('https://api.pushbullet.com/v2/pushes', auth = (self.nv['token'],''), data = data)
            self.PutModule("Test message successfully sent.")

        elif command.split()[0] == "help":
            self.PutModule("Instructions can be found at " + help_url)

        else:
            self.PutModule("Invalid command. See " + help_url)

import znc
import requests
import json

help_url = "https://snoonet.org/push"


class push(znc.Module):

    module_types = [znc.CModInfo.NetworkModule]
    description = "PushBullet notifications"

    def OnLoad(self, args, message):
        return True

    def OnChanMsg(self, nick, channel, message):
        self.check_send(channel, nick, message)

    def OnChanNotice(self, nick, channel, message):
        self.check_send(channel, nick, message)

    def OnPrivMsg(self, nick, message):
        self.check_send(None, nick, message)

    def OnPrivNotice(self, nick, message):
        current_server = self.GetNetwork().GetIRCServer()
        if not nick.GetNick() == str(current_server):
            self.check_send(None, nick, message)

    def check_send(self, channel, nick, message):
        if self.nv.get("state") == "on":
            if self.nv.get("away_only") == "yes":
                if self.GetNetwork().IsIRCAway():
                    self.check_contents(channel, nick, message)
            else:
                self.check_contents(channel, nick, message)

    def check_contents(self, channel, nick, message):

        my_nick = str(self.GetNetwork().GetCurNick()).lower()
        sender_nick = (nick.GetNick()).lower()
        ignored = False
        highlighted = False

        for ignored_user in json.loads(self.nv.get('ignore', "")):
            if sender_nick == ignored_user:
                ignored = True
                break

        if channel:
            msg = str(message).lower().split()

            if not ignored:
                for word in msg:
                    if word == my_nick:
                        highlighted = True
                        break
                    else:
                        for highlight_word in json.loads(
                                self.nv.get('highlight', "")):

                            if highlight_word == word:
                                highlighted = True

            if highlighted and not ignored:
                self.send_message(channel, nick, message)

        else:
            if not ignored:
                self.send_message(None, nick, message)

    def send_message(self, channel, nick, message):
        ttl = ''
        if channel:
            msg = channel.GetName() + " <" + nick.GetNick() + "> " + message.s
            ttl = 'Highlight'
        else:
            msg = "<" + nick.GetNick() + "> " + message.s
            ttl = 'Private Message'

        if self.nv.get('private', "") == 'no':
            ttl = msg

        data = dict(type='note', title=ttl, body=msg)
        requests.post('https://api.pushbullet.com/v2/pushes',
                      auth=(self.nv.get('token'), ''), data=data)

    def OnModCommand(self, command):
        split_command = command.split()
        top_level_cmd = split_command[0]
        if len(command) > 2:
            cmd_option = split_command[1]
        if len(command) > 3:
            cmd_setting = split_command[2]

        if top_level_cmd == "enable":
            if self.nv.get('token'):
                self.nv['state'] = "on"
                self.PutModule("Notifications \x02enabled\x02.")
            else:
                self.PutModule("You must set a token before enabling "
                               "notifications.")

        elif top_level_cmd == "disable":
            self.nv['state'] = "off"
            self.PutModule("Notifications \x02disabled\x02.")

        elif top_level_cmd == "set":
            if len(command) > 2:
                if command.split()[1] == "token":

                    if self.nv.get('state', "") == 'on':
                        self.PutModule("You must disable notifications "
                                       "before changing your token.")
                    else:
                        if len(command) > 3:
                            self.nv['token'] = command.split()[2]
                            self.PutModule("Token set successfully.")

                        else:
                            self.nv['token'] = ''
                            self.PutModule("Token cleared.")

                elif command.split()[1] == "away_only" or \
                        command.split()[1] == "private":

                    try:
                        if command.split()[2] == "yes" or \
                                        command.split()[2] == "no":

                            self.nv[command.split()[1]] = command.split()[2]
                            self.PutModule(command.split()[1] +
                                           " option set to \x02" +
                                           command.split()[2] + "\x02")

                        else:
                            self.PutModule("You must specify either 'yes' "
                                           "or 'no'.")

                    except:
                        self.PutModule("You must specify either 'yes' or "
                                       "'no'.")

                else:
                    self.PutModule("Invalid option. Options are 'token' and "
                                   "'away_only'. See " + help_url)

            else:
                self.PutModule("You must specify a configuration option. See "
                               + help_url)

        elif top_level_cmd == "highlight" \
                or command.split()[0] == "ignore":

                cmd = command.split()[0]
                if command.split()[1] == "list":
                    try:
                        if json.loads(self.nv.get(cmd)):
                            self.PutModule(cmd.title() + " list: \x02" +
                                           ', '.join(json.loads(self.nv[cmd]))
                                           + "\x02")
                        else:
                            self.PutModule(cmd.title() + " list empty.")
                    except:
                        self.PutModule(cmd.title() + " list empty.")

                elif command.split()[1] == "add":
                    try:
                        list = json.loads(self.nv[cmd])

                        if (command.split()[2]).lower() not in list:
                            list.append((command.split()[2]).lower())
                            self.nv[cmd] = json.dumps(list)
                            self.PutModule("\x02" + command.split()[2]
                                           + "\x02 added to " + cmd + " list.")

                        else:
                            self.PutModule("\x02" + command.split()[2] +
                                           "\x02 already in " + cmd + " list.")
                    except:
                        try:
                            list = [(command.split()[2]).lower()]
                            self.nv[cmd] = json.dumps(list)
                            self.PutModule("\x02" + command.split()[2] +
                                           "\x02 added to " + cmd + " list.")
                        except:
                            self.PutModule("You must specify a single "
                                           "word or nick to add.")

                elif command.split()[1] == "del":
                    try:
                        if self.nv[cmd]:
                            list = json.loads(self.nv[cmd])

                            if (command.split()[2]).lower() in list:
                                list.remove((command.split()[2]).lower())
                                self.nv[cmd] = json.dumps(list)
                                self.PutModule("\x02" + command.split()[2] +
                                               "\x02 deleted from " +
                                               cmd + " list.")
                            else:
                                self.PutModule("\x02" + command.split()[2] +
                                               "\x02 not in " + cmd + " list.")
                        else:
                            self.PutModule(cmd.title() + " list empty.")
                    except:
                        try:
                            if not command.split()[2]:
                                self.PutModule("You must specify a single "
                                               "word or nick to delete.")
                            else:
                                self.PutModule(cmd.title() + " list empty.")
                        except:
                            self.PutModule("You must specify a single word "
                                           "or nick to delete.")

                else:
                    self.PutModule("Invalid option. Options are 'list', "
                                   "'add', and 'del'. See " + help_url)

        elif top_level_cmd == "test":
            data = dict(type='note', title="Test Message",
                        body="This is a test message.")
            requests.post('https://api.pushbullet.com/v2/pushes',
                          auth=(self.nv['token'], ''), data=data)

            self.PutModule("Test message successfully sent.")

        elif top_level_cmd == "help":
            self.PutModule("Instructions can be found at " + help_url)

        else:
            self.PutModule("Invalid command. See " + help_url)

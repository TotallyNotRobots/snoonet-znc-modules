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
        if nick.GetNick() != str(current_server):
            self.check_send(None, nick, message)

    def check_send(self, channel, nick, message):
        if self.nv.get("state") == "on" and (self.nv.get("away_only") != "yes" or self.GetNetwork().IsIRCAway()):
            self.check_contents(channel, nick, message)

    def check_contents(self, channel, nick, message):
        my_nick = str(self.GetNetwork().GetCurNick()).lower()
        sender_nick = (nick.GetNick()).lower()
        ignored = any(sender_nick == ignored_user for ignored_user in json.loads(self.nv.get('ignore', "[]")))
        highlighted = False
        highlight_words = json.loads(self.nv.get('highlight', "[]"))

        if channel:
            msg = str(message).lower().split()
            if not ignored:
                for word in msg:
                    if word == my_nick or word in highlight_words:
                        highlighted = True
                        break

            if highlighted and not ignored:
                self.send_message(channel, nick, message)
        else:
            if not ignored:
                self.send_message(None, nick, message)

    def send_message(self, channel, nick, message):
        if channel:
            msg = channel.GetName() + " <" + nick.GetNick() + "> " + message.s
            ttl = 'Highlight'
        else:
            msg = "<" + nick.GetNick() + "> " + message.s
            ttl = 'Private Message'

        if self.nv.get('private') == 'no':
            ttl = msg

        data = dict(type='note', title=ttl, body=msg)
        requests.post('https://api.pushbullet.com/v2/pushes',
                      auth=(self.nv.get('token'), ''), data=data)

    def OnModCommand(self, command):
        split_command = command.split()
        top_level_cmd = split_command[0]
        cmd_option = None
        cmd_setting = None

        if len(split_command) >= 2:
            cmd_option = split_command[1]
            if len(split_command) >= 3:
                cmd_setting = split_command[2]

        if top_level_cmd == "enable":
            if self.nv.get('token'):
                self.nv['state'] = "on"
                self.PutModule("Notifications \x02enabled\x02.")

            else:
                self.PutModule("You must set a token before enabling notifications.")

        elif top_level_cmd == "disable":
            self.nv['state'] = "off"
            self.PutModule("Notifications \x02disabled\x02.")

        elif top_level_cmd == "set":
            if cmd_option == "token":

                if self.nv.get('state') == 'on':
                    self.PutModule("You must disable notifications before changing your token.")

                else:
                    if cmd_setting:
                        self.nv['token'] = cmd_setting
                        self.PutModule("Token set successfully.")

                    else:
                        self.nv['token'] = ''
                        self.PutModule("Token cleared.")

            elif cmd_option in ("away_only", "private"):

                if cmd_setting in ("yes", "no"):
                    self.nv[cmd_option] = cmd_setting
                    self.PutModule(cmd_option + " option set to \x02" + cmd_setting + "\x02")

                else:
                    self.PutModule("You must specify either 'yes' or 'no'.")
            else:
                self.PutModule("Invalid option. Options are 'token' and 'away_only'. See " + help_url)

        elif top_level_cmd in ("highlight", "ignore"):
            cmd_list = json.loads(self.nv.get(top_level_cmd, "[]"))
            if cmd_option == "list":
                if cmd_list:
                    self.PutModule(top_level_cmd.title() + " list: \x02" + ', '.join(cmd_list) + "\x02")

                else:
                    self.PutModule(top_level_cmd.title() + " list empty.")

            elif cmd_option == "add":
                if cmd_setting:

                    if cmd_setting.lower() not in cmd_list:
                        cmd_list.append(cmd_setting.lower())
                        self.nv[top_level_cmd] = json.dumps(cmd_list)
                        self.PutModule("\x02" + cmd_setting + "\x02 added to " + top_level_cmd + " list.")

                    else:
                        self.PutModule("\x02" + cmd_setting + "\x02 already in " + top_level_cmd + " list.")
                else:
                    self.PutModule("You must specify a single word or nick to add.")

            elif cmd_option == "del":
                if cmd_setting:
                    if cmd_list:
                        option_list = json.loads(self.nv[top_level_cmd])
                        if cmd_setting.lower() in option_list:
                            option_list.remove(cmd_setting.lower())
                            self.nv[top_level_cmd] = json.dumps(option_list)
                            self.PutModule("\x02" + cmd_setting + "\x02 deleted from " + top_level_cmd + " list.")

                        else:
                            self.PutModule("\x02" + cmd_setting + "\x02 not in " + top_level_cmd + " list.")
                    else:
                        self.PutModule(top_level_cmd.title() + " list empty.")
                else:
                    self.PutModule("You must specify a single word or nick to delete.")
            else:
                self.PutModule("Invalid option. Options are 'list', add', and 'del'. See " + help_url)

        elif top_level_cmd == "test":
            token = self.nv.get("token")
            if token:
                data = dict(type='note', title="Test Message", body="This is a test message.")
                requests.post('https://api.pushbullet.com/v2/pushes', auth=(token, ''), data=data)
                self.PutModule("Test message successfully sent.")
            else:
                self.PutModule("You must supply a token before you can test whether or not it works")

        elif top_level_cmd == "help":
            self.PutModule("Instructions can be found at " + help_url)

        else:
            self.PutModule("Invalid command. See " + help_url)

import json
import os
import sys
import time
from datetime import timedelta

import znc

dirs = znc.CZNC.Get().GetModules().GetModDirs()

# Make sure to prioritize the current directory for imports
for path, _ in dirs:
    path = os.path.abspath(path)
    if path in sys.path:
        sys.path.remove(path)

    sys.path.insert(0, path)

from snoomodule import command, SnooModule


class expire_timer(znc.Timer):
    def RunJob(self):
        self.GetModule().do_expire()


TIME_MULTIPLIERS = {
    'y': timedelta(days=365),
    'w': timedelta(days=7),
    'd': timedelta(days=1),
    'h': timedelta(hours=1),
    'm': timedelta(minutes=1),
    's': timedelta(seconds=1),
}


def parse_duration(s):
    subtotal = 0
    total = 0
    for c in s:
        if c.isdigit():
            subtotal *= 10
            subtotal += int(c)
        elif c in TIME_MULTIPLIERS:
            total += subtotal * TIME_MULTIPLIERS[c].total_seconds()
            subtotal = 0
        else:
            return 0

    # Assume any trailing value to be seconds
    return int(total + subtotal)


def parse_bool_flag(text, default=None):
    text = text.strip().lower()
    if not text and default is not None:
        text = default

    if text in ("true", "on", "yes", "y", "1"):
        return True
    elif text in ("false", "off", "no", "n", "0"):
        return False

    return None


class autoexpire(SnooModule):
    module_types = [znc.CModInfo.GlobalModule]
    description = "Expires an account after a certain amount of inactivity"

    def OnLoad(self, args, message):
        args = str(args).split()
        expiry = "30d"
        expire_cycle = "1h"
        if args:
            expiry = args.pop(0)

        if args:
            expire_cycle = args.pop(0)

        self.expiry = parse_duration(expiry)

        self._noexpire = None
        self._activity = None

        self.CreateTimer(
            expire_timer, interval=parse_duration(expire_cycle), cycles=0, description="Expires user accounts"
        )

        return True

    def OnClientDisconnect(self):
        user = self.GetUser()
        self.activity[user.GetUserName()] = time.time()
        self.save_nv()

    def OnDeleteUser(self, user):
        name = user.GetUserName()
        save = False
        try:
            del self.activity[name]
        except KeyError:
            pass
        else:
            save = True

        if name in self.noexpire:
            self.noexpire.remove(name)
            save = True

        if save:
            self.save_nv()

        return znc.CONTINUE

    @command("noexpire", 2, admin=True)
    def cmd_noexpire(self, username, state):
        """Configures the NoExpire flag for a user
        <user> <state>"""
        flag = parse_bool_flag(state)
        if flag is None:
            return "Invalid state '{}'".format(state)

        user = self.znc_core.FindUser(username)

        if user:
            self.set_noexpire(user.GetUserName(), flag)
            if flag:
                return "NoExpire = true"
            else:
                return "NoExpire = false"
        else:
            return "User \"{}\" not found".format(username)

    def do_expire(self):
        if self.expiry <= 0:
            return

        users = self.znc_core.GetUserMap()
        now = time.time()
        for name, user in users.items():
            if user.IsBeingDeleted() or user.IsUserAttached() or user.IsAdmin() or name in self.noexpire:
                continue

            active = self.get_last_active(name)
            if (now - active) > self.expiry:
                self.expire_user(user)

    def get_last_active(self, name):
        try:
            return self.activity[name]
        except KeyError:
            now = time.time()
            self.activity[name] = now
            self.save_nv()
            return now

    def set_noexpire(self, user, value):
        if value:
            if user not in self.noexpire:
                self.noexpire.append(user)
                self.save_nv()
        else:
            if user in self.noexpire:
                self.noexpire.remove(user)
                self.save_nv()

    def save_nv(self):
        self.nv["noexpire"] = json.dumps(self.noexpire)
        self.nv["activity"] = json.dumps(self.activity)

    def expire_user(self, user):
        name = user.GetUserName()
        # self.znc_core.Broadcast("Expiring user {}".format(name))
        self.znc_core.DeleteUser(name)

    @property
    def noexpire(self):
        if self._noexpire is None:
            self._noexpire = json.loads(self.nv.get("noexpire", "[]"))

        return self._noexpire

    @property
    def activity(self):
        if self._activity is None:
            self._activity = json.loads(self.nv.get("activity", "{}"))

        return self._activity

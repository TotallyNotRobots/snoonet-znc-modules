# Snoonet ZNC Modules

- [Setup](#setup)
- [AutoExpire](#autoexpire)
- [CheckConfig](#checkconfig)
- [ForceChan](#forcechan)
- [Push](#push)
- [UserIPs](#userips)

---

### Setup

#### About

Modules are global ZNC modules written Python (requires [modpython](http://wiki.znc.in/Modpython)) that checks that a module is loaded for all users.

#### Installing

Place `module.py` in `~/.znc/modules`. `userips.py` also requires the `userips` folder in the same location.

#### Loading

All modules are written in Python (requires [modpython](http://wiki.znc.in/Modpython)). Modules can be loaded with `/znc loadmod <module>`

#### Accessing

All commands should be sent to `*checkconfig` as a private message

---


## AutoExpire

Automatically deletes users' accounts that have been inactive for more than the configured time.
Ignores ZNC admins, online users, and anyone with the NoExpire flag set to true.

### Commands

`noexpire <user> <state>` - Sets the noexpire flag on a user

### Arguments

`[expire_time] [expire_cycle]`
- `expire_time` is the amount of time a user's account can be inactive before being deleted (default: `30d`). Set `expire_time` to `0` to disable expiry.
- `expire_cycle` is how often to check for expired users (default: `1h`). All times are specified in `NyNwNdNmNs` format (eg. `1y2d3h` = 1 year, 2 days, 3 hours, `90d` = 90 days, `2w` = 2 weeks, `5m` = 5 minutes)


## CheckConfig

Checks that various options are configured for all users.

### Usage

`checknetwork <network>` will output all users who do not have the specified network configured

`checkchan <network> <channel>` will output all users who do not have the specified channel in the given network

`checkusermod <module>` will output `*controlpanel LoadModule` command for all users who do not have the module enabled

`checknetmod <module> <network>` will output `*controlpanel LoadNetModule` for all users who do not have the module enabled on the specified network

---

## ForceChan

Prevents a user from parting a channel.

### Usage

`/msg *forcechan forcechan` will force users into the preconfigured channel

---

## Push

Sends push notifications to users on mention or PM via PushBullet

### Usage

See [Snoonet BNC Push Notifications](https://snoonet.org/push) for instructions and setup

---

## UserIPs

Provides a web-interface for viewing IP addresses of connected users

### Usage

The module can be accessed from the ZNC webadmin by going to `User IPs` under `Global Modules`

# Snoonet ZNC Modules

- [Setup](#setup)
- [CheckMod](#checkmod)
- [CheckNetwork](#checknetwork)
- [ForceChan](#forcechan)
- [UserIPs](#userips)

---

### Setup

#### About

Modules are global ZNC modules written Python (requires [modpython](http://wiki.znc.in/Modpython)) that checks that a module is loaded for all users.

#### Installing

Place `module.py` in `~/.znc/modules`. `userips.py` also requires the `userips` folder in the same location.

#### Loading

All modules are written in Python (requires [modpython](http://wiki.znc.in/Modpython)). Modules can be loaded with `/znc loadmod <module>`

---

## CheckMod

Checks that a module is loaded for all users or a network for all users.

### Usage

`/msg *checkmod checkusermod <module>` will output `*controlpanel LoadModule` command for all users who do not have the module enabled

`/msg *checkmod checknetmod <module> <network>` will output `*controlpanel LoadNetModule` for all users who do not have the module enabled on the specified network

---

## CheckNetwork

Checks that a network is configured for all users.

### Usage

`/msg *checknetwork <module>` will output all users who do not have the specified network configured

---

## ForceChan

Prevents a user from parting a channel.

### Usage

`/msg *forcechan forcechan` will force users into the preconfigured channel

---

## UserIPs

Provides a web-interface for viewing IP addresses of connected users

### Usage

The module can be accessed from the ZNC webadmin by going to `User IPs` under `Global Modules`

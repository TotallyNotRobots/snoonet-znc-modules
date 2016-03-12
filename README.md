# Snoonet ZNC Modules

## CheckMod

`checkmod` is a global ZNC module written Python (requires [modpython](http://wiki.znc.in/Modpython)) that checks that a module is loaded for all users.

### Installing

Place `checkmod.py` in `~/.znc/modules`.

### Loading

`checkmod.py` requires that `modpython` be loaded first in either the webadmin or with `/znc loadmod modpython`. `checkmod` can then be loaded the same way.

### Usage

`/msg *checkmod checkusermod <module>` will output load command for all users who do not have the module enabled
`/msg *checkmod checknetmod <module> <network>` will output load command for all users who do not have the module enabled on the given network

## ForceChan

`forcechan` is a global ZNC module written Python (requires [modpython](http://wiki.znc.in/Modpython)) that prevents a user from parting a channel.

### Installing

Place `forcechan.py` in `~/.znc/modules`.

### Loading

`forcechan` requires that `modpython` be loaded first in either the webadmin or with `/znc loadmod modpython`. `forcechan` can then be loaded the same way.

### Usage

`/msg *forcechan forcechan` will force users into the preconfigured channel

## UserIPs

`User IPs` is a global ZNC module written in both C++ (requires GCC 4.7+) and Python (requires [modpython](http://wiki.znc.in/Modpython)).

### Installing

Place either `userips.cpp` or `userips.py` in `~/.znc/modules`, along with the `userips` folder. The C++ version must be built from source, using `znc-buidmod userips.cpp`. Python modules do not require compilation.

### Loading

The both the C++ and Python modules can be loaded as a global module in the webadmin panel. Loading the Python version requires `modpython` be loaded first.

Modules can also be loaded from within an IRC connection established to ZNC using `/znc loadmod userips`

### Accessing

The module can be accessed from the ZNC webadmin by going to `User IPs` under `Global Modules`

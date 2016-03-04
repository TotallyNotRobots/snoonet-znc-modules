## ZNC IP View

`IP View` is a global ZNC module written in both C++ and Python (requires [modpython](http://wiki.znc.in/Modpython)).

### Installing

Place either `userips.cpp` or `userips.py` in `~/.znc/modules`, along with the `userips` folder. The C++ version must be built from source, using `znc-buidmod userips.cpp`. Python modules do not require compilation.

### Loading

The both the C++ and Python modules can be loaded as a global module in the webadmin panel. Loading the Python version requires `modpython` be loaded first.

Modules can also be loaded from within an IRC connection established to ZNC using `/znc loadmod userips`

### Accessing

The module can be accessed from the ZNC webadmin by going to `User IPs` under `Global Modules`

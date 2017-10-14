"""
Base class for Snoonet ZNC modules

Adds various utility functions
"""

import inspect
from collections import namedtuple
from operator import attrgetter

import znc

Command = namedtuple("Command", "name func min_args max_args syntax help_msg include_cmd admin")


def command(name, min_args=0, max_args=None, syntax=None, help_msg=None, include_cmd=False, admin=False):
    def _decorate(func):
        nonlocal help_msg, syntax
        try:
            func_doc = func.__doc__
        except AttributeError:
            func_doc = None

        if func_doc is None:
            func_doc = ""

        func_doc = inspect.cleandoc(func_doc).splitlines()
        if help_msg is None and func_doc:
            help_msg = func_doc.pop(0)

        if syntax is None and func_doc:
            syntax = func_doc.pop(0)

        try:
            handlers = func._cmd_handlers
        except AttributeError:
            handlers = []
            func._cmd_handlers = handlers

        handlers.append(Command(name, func, min_args, max_args, syntax, help_msg, include_cmd, admin))
        return func

    return _decorate


class SnooModule(znc.Module):
    def __init__(self):
        super().__init__()
        self.cmd_handlers = self.find_cmds()

    @classmethod
    def find_cmds(cls):
        handlers = []
        classes = {cls, *cls.__bases__}
        funcs = [obj for c in classes for obj in c.__dict__.values() if callable(obj)]
        for obj in funcs:
            try:
                handlers.extend(obj._cmd_handlers)
            except AttributeError:
                pass

        return {handler.name: handler for handler in handlers}

    @command("help")
    def cmd_help(self):
        """Returns help documentation for this module"""
        help_table = znc.CTable()
        help_table.AddColumn("Command")
        help_table.AddColumn("Arguments")
        help_table.AddColumn("Description")

        for cmd in sorted(self.cmd_handlers.values(), key=attrgetter("name")):
            help_table.AddRow()
            help_table.SetCell("Command", cmd.name)
            help_table.SetCell("Arguments", cmd.syntax or "")
            help_table.SetCell("Description", cmd.help_msg or "")

        return help_table

    def OnModCommand(self, text):
        cmd, *args = text.strip().split()
        cmd = self.cmd_handlers.get(cmd.lower())
        if not cmd:
            self.PutModule("Unknown command")
            return

        user = self.GetUser()

        if cmd.admin and not user.IsAdmin():
            self.PutModule("Permission denied")

        if len(args) < cmd.min_args:
            self.PutModule("Invalid arguments for command")
            return

        args = list(args)
        max_args = cmd.max_args
        if max_args is None:
            max_args = cmd.min_args

        if max_args == 0:
            args = []

        if len(args) > max_args:
            args[max_args] = " ".join(args[max_args:])
            del args[max_args + 1:]

        if cmd.include_cmd:
            args = [cmd.name] + args

        result = cmd.func(self, *args)
        if result:
            if isinstance(result, tuple):
                for part in result:
                    self.PutModule(part)
            else:
                self.PutModule(result)

    @property
    def znc_core(self):
        return znc.CZNC.Get()

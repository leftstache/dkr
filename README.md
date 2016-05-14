# dkr

Extensible Docker CLI Client

## To Use

`dkr --help` for use.

## To Install

TODO: make pip installable

## To Extend

Add any .py file to `~/.dkr/commands/`. It should have the following functions:

* `command()`: returns a `str` or `list` of `str`. The name of the subcommand(s).
* `help_summary(str)`: takes a `str` returns a `str`. The returned string is what is displayed for the given command in `--help`.
* `import_command(docker_client, args, state)`: Takes the docker-py docker client and a subparser for argparse.ArgumentParser for the command. The state is a simple dictionary that remains persistent between running the dkr command. You can use this to track state, e.g. to remember what the last container was used so you can provide a shortcut.   
    `args.set_defaults(func=somefunc)` should be called. `somefunc` will be invoked when your particular command is run from the CLI. It should accept the same three arguments as import_command.
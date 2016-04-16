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
* `import_command(docker_client, args)`: Takes the docker-py docker client and a subparser for argparse.ArgumentParser for the command. 
    `args.set_defaults(func=somefunc)` should be called. `somefunc` will be invoked when your particular command is run from the CLI. It should accept the same two arguments as import_command.
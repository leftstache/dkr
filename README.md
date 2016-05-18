# dkr

Extensible Docker CLI Client

## To Use

`dkr --help` for use.

## To Install

```bash
pip install dkr
```

## To Extend

Add any .py file to `~/.dkr/commands/`. It should have the following functions:

* `command()`: returns a `str` or `list` of `str`. The name of the subcommand(s).
* `help_summary(str)`: takes a `str` returns a `str`. The returned string is what is displayed for the given command in `--help`.
* `import_command(docker_client, args, state)`: Takes the docker-py docker client and a subparser for argparse.ArgumentParser for the command. The state is a simple dictionary that remains persistent between running the dkr command. You can use this to track state, e.g. to remember what the last container was used so you can provide a shortcut.   
    `args.set_defaults(func=somefunc)` should be called. `somefunc` will be invoked when your particular command is run from the CLI. It should accept the same three arguments as import_command.
    

## Create Options

The `dkr create` command has the `--option` (`-o`) flag that can be specified multiple times. The format is explained below.
This can be used to specify any docker create arg, using the naming conventions used by [docker-py](http://docker-py.readthedocs.io/en/latest/api/#create_container)
 
 
## Create Options Format
 
These arguments get expanded to a dict. For example:
 
 ```bash
 dkr create -o key=value image_name
 ```
 
 Is expanded to:
 
 ```python
 {
    "key": "value"
 }
 ```
 
 This also handles nested values:
 
 ```bash
 dkr create -o nested.key=value image_name
 ```
 
 Is expanded to:
 
 ```python
 {
    "nested": {
        "key": "value"
    }
 }
 ```
 
 You can also specify raw json values:
 
 ```bash
 dkr create -o nested.key:=true image_name
 ```
 
 Is expanded to:
 
 ```python
 {
    "nested": {
        "key": True
    }
 }
 ```
 
 And:
 
 ```bash
 dkr create -o "nested.key:=[true, false, 0]" image_name
 ```
 
 Is expanded to:
 
 ```python
 {
    "nested": {
        "key": [True, False, 0]
    }
 }
 ```
 
 You can use multiple options:
 
 ```bash
 dkr create -o "nested.key:=[true, false, 0]" -o "nested.key2=value" image_name
 ```
 
 Is expanded to:
 
 ```python
 {
    "nested": {
        "key": [True, False, 0],
        "key2": "value"
    }
 }
 ```
 
 You can test this yourself by running `dkr_core/cmd_to_json.py` with naked arguments. i.e. no `-o`:
 
 ```bash
 python3 dkr_core/cmd_to_json.py "nested.key:=[true, false, 0]" "nested.key2=value"
 ```
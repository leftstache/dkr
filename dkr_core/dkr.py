import json
import os
import importlib
import importlib.util
import docker
import argparse
import sys
import os.path


def load_modules(extensions_dir: str) -> dict:
    result = {}

    if os.path.isdir(extensions_dir):
        directories = os.listdir(extensions_dir)
        for file in directories:
            if file.endswith(".py"):
                module_name = file[:-3]
                spec = importlib.util.spec_from_file_location(module_name, os.path.join(extensions_dir, file))
                imported_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(imported_module)

                if hasattr(imported_module, 'command'):
                    command_name = imported_module.command()
                    if isinstance(command_name, list):
                        for name in command_name:
                            result[name] = imported_module
                    elif isinstance(command_name, str):
                        result[command_name] = imported_module
                else:
                    result[module_name] = imported_module
    return result


def load_state(state_file):
    if os.path.isfile(state_file):
        state_file = os.path.join(state_file)
        with open(state_file, 'r') as json_data:
            loaded_json = json.load(json_data)
    else:
        loaded_json = {}

    return loaded_json


def save_state(state, state_file):
    if not os.path.isdir(os.path.dirname(state_file)):
        os.makedirs(state_file)

    with open(state_file, 'w') as file:
        json.dump(state, file, indent=2)


def main():
    state_file = os.path.join(os.path.expanduser("~"), ".dkr", "state.json")
    state = load_state(state_file)

    try:
        docker_client = docker.from_env(assert_hostname=False)

        script_directory = os.path.dirname(os.path.realpath(__file__))
        project_directory = os.path.dirname(script_directory)
        built_in_modules = load_modules(os.path.join(project_directory, "commands"))

        user_module_dir = os.path.join(os.path.expanduser("~"), ".dkr", "commands")
        user_modules = load_modules(user_module_dir)

        modules = {}
        modules.update(built_in_modules)
        modules.update(user_modules)

        arg_parser = argparse.ArgumentParser(description="Extensible Docker CLI Client")
        subparsers = arg_parser.add_subparsers(title="Commands", metavar="COMMAND")
        for name, module in modules.items():
            if hasattr(module, 'import_command'):
                subparser = subparsers.add_parser(name, help=module.help_summary(name) if hasattr(module, 'help_summary') else "Does something wonderful!")
                module.import_command(docker_client, subparser, state)

        parsed_args = arg_parser.parse_args()

        if 'func' in parsed_args:
            parsed_args.func(docker_client, parsed_args, state)
        else:
            print("No valid command specified. `{} -h` for help.".format(sys.argv[0]))

    finally:
        save_state(state, state_file)

import os
import importlib
import importlib.util
import docker
import argparse
import sys


def load_modules(extensions_dir: str) -> dict:
    result = {}
    directories = os.listdir(extensions_dir)
    for file in directories:
        if file.endswith(".py"):
            module_name = file[:-3]
            spec = importlib.util.spec_from_file_location(module_name, os.path.join(extensions_dir, file))
            imported_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(imported_module)
            result[module_name] = imported_module

    return result


def main():
    docker_client = docker.from_env(assert_hostname=False)
    script_directory = os.path.dirname(os.path.realpath(__file__))
    project_directory = os.path.dirname(script_directory)
    built_in_modules = load_modules(os.path.join(project_directory, "modules"))
    user_modules = load_modules("/Users/joeljohnson/.dkr")

    modules = {}
    modules.update(built_in_modules)
    modules.update(user_modules)

    arg_parser = argparse.ArgumentParser(description="Extensible Docker CLI Client")
    subparsers = arg_parser.add_subparsers(title="Commands")
    for name, module in modules.items():
        if hasattr(module, 'import_command'):
            subparser = subparsers.add_parser(name, help=module.help_summary() if hasattr(module, 'help_summary') else "Does something wonderful!")
            module.import_command(docker_client, subparser)

    parsed_args = arg_parser.parse_args()

    if 'func' in parsed_args:
        parsed_args.func(docker_client, parsed_args)
    else:
        print("No valid command specified. `{} -h` for help.".format(sys.argv[0]))

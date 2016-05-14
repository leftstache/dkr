import docker
import sys
from pprint import pprint
from tabulate import tabulate
import json
from datetime import datetime
import pretty
import re
import yaml

from dkr_core import cmd_to_json


def command() -> list:
    return ['container', 'c']


def help_summary(name: str) -> str:
    if name == 'c':
        return 'Alias for "container"'
    return "Various commands for containers"


def import_command(docker_client: docker.Client, args, state: dict):
    args.set_defaults(func=default)
    subparsers = args.add_subparsers(title="Container Commands")

    list_cmd = subparsers.add_parser('list', help="Lists containers")
    list_cmd.add_argument('-a', '--all', action='store_true', help='Include non-running containers')
    list_cmd.add_argument('-q', '--quiet', action='store_true', help='Only print IDs')
    list_cmd.add_argument('--json', action='store_true', help='Render all as json')
    list_cmd.add_argument('--pprint', action='store_true', help='Dump contents using python\'s pprint function')
    list_cmd.set_defaults(func=list_containers)

    inspect_cmd = subparsers.add_parser('inspect', help="Inspects the detail of an container")
    inspect_cmd.add_argument('container', help="The name or ID of the Container")
    inspect_cmd.add_argument('--json', action='store_true', help='Render all as json')
    inspect_cmd.add_argument('--pprint', action='store_true', help='Dump contents using python\'s pprint function')
    inspect_cmd.set_defaults(func=inspect_container)

    create_cmd = subparsers.add_parser('create', help="Create a new container")
    create_cmd.add_argument('--id', action='store_true', help="Display the ID of the created name instead of the name")
    # create_cmd.add_argument('-p', '--publish', nargs='*', help="Publish a container's port(s) to the host")
    create_cmd.add_argument('-o', '--option', action='append', help="Include a docker create option. See https://github.com/leftstache/dkr/blob/master/README.md for more information.")
    create_cmd.add_argument('--name', help="The name of the container")
    create_cmd.add_argument('image', help="The image to create the container from")
    create_cmd.add_argument('cmd', nargs="*", help="The command to run")
    create_cmd.set_defaults(func=create_container)


def default(client: docker.Client, args, state: dict):
    print("No valid command specified. `{} container -h` for help.".format(sys.argv[0]))


def list_containers(client: docker.Client, args, state: dict):
    containers = client.containers(all=args.all, quiet=args.quiet)

    if args.pprint:
        pprint(containers)
        return

    if args.json:
        print(json.dumps(containers, indent=4, sort_keys=True))
        return

    table = []
    if args.quiet:
        headers = ()
    else:
        headers = ["ID", "NAME", "IMAGE", "CMD", "CREATED", "STATUS", "PORTS"]

    for container in containers:
        row = []
        table.append(row)

        if args.quiet:
            row.append(container['Id'])
            continue

        row.append(container['Id'][:12])
        row.append(container['Names'][0][1:])
        row.append(container['Image'])
        row.append(container['Command'])

        created_seconds = container['Created']
        created_date = datetime.fromtimestamp(created_seconds)
        row.append(re.sub(r"\.[0-9]+", '', pretty.date(created_date, short=True)))

        row.append(container['Status'])

        ports = ""
        if 'Ports' in container:
            ports = ', '.join([_port_string(p) for p in container['Ports']])
        row.append(ports)

    print(tabulate(table, headers=headers, tablefmt="plain"))


def inspect_container(docker_client: docker.Client, args, state: dict):
    if args.container == '-':
        args.container = state['last_container']

    container = docker_client.inspect_container(args.container)

    state['last_container'] = container['Id']

    if args.pprint:
        pprint(container)
        return

    if args.json:
        print(json.dumps(container, indent=4))
        return

    print(yaml.dump(container, default_flow_style=False))


def create_container(docker_client: docker.Client, args, state: dict):
    image = args.image
    if image == '-':
        image = state['last_image']
    state['last_image'] = image

    cmd = args.cmd if args.cmd else None
    name = args.name if args.name else None

    docker_args = {}

    if 'option' in args:
        user_docker_options = cmd_to_json.parse_options(args.option)
        if user_docker_options:
            docker_args.update(user_docker_options)

    docker_args['image'] = image
    docker_args['command'] = cmd
    docker_args['name'] = name

    if 'host_config' in docker_args:
        docker_args['host_config'] = docker_client.create_host_config(**docker_args['host_config'])

    container = docker_client.create_container(**docker_args)

    state['last_container'] = container['Id']

    if container['Warnings']:
        print("WARNING:", container['Warnings'], file=sys.stderr)

    if args.id:
        print(container['Id'])
    else:
        container = docker_client.inspect_container(container)
        print(container['Name'][1:])


def _port_string(port_obj: dict) -> str:
    ip = "{}:".format(port_obj['IP']) if 'IP' in port_obj else ''
    private_port = port_obj['PrivatePort'] if 'PrivatePort' in port_obj else ''
    public_port = port_obj['PublicPort'] if 'PublicPort' in port_obj else ''
    port_type = "/{}".format(port_obj['Type']) if 'Type' in port_obj else ''

    if private_port and public_port:
        return "{}{}->{}{}".format(ip, public_port, private_port, port_type)

    if private_port:
        return "{}{}{}".format(ip, private_port, port_type)

    return ""

import docker
import sys
from pprint import pprint
from tabulate import tabulate
import json
from datetime import datetime
import pretty
import re


def command() -> list:
    return ['container', 'c']


def help_summary(name: str) -> str:
    if name == 'c':
        return 'Alias for "container"'
    return "Various commands for containers"


def import_command(docker_client: docker.Client, args):
    args.set_defaults(func=default)
    subparsers = args.add_subparsers(title="Container Commands")

    list_cmd = subparsers.add_parser('list', help="Lists containers")
    list_cmd.add_argument('-a', '--all', action='store_true', help='Include non-running containers')
    list_cmd.add_argument('-q', '--quiet', action='store_true', help='Only print IDs')
    list_cmd.add_argument('--json', action='store_true', help='Render all as json')
    list_cmd.add_argument('--pprint', action='store_true', help='Dump contents using python\'s pprint function')
    list_cmd.set_defaults(func=list_containers)


def default(client: docker.Client, args):
    print("No valid command specified. `{} container -h` for help.".format(sys.argv[0]))


def list_containers(client: docker.Client, args):
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

import docker
import docker.errors
import sys
from pprint import pprint
from tabulate import tabulate
import json
from datetime import datetime
import pretty
import re
import yaml

from dkr_core import errors
from dkr_core import cmd_to_json


class Port:
    def __init__(self, ip: str=None, host_port: int=None, guest_port: int=None, proto: str="tcp"):
        self.ip = ip
        self.host_port = host_port
        self.guest_port = guest_port
        self.proto = proto


class Volume:
    def __init__(self, volume_name: str, guest_mount_point: str, mode: str='rw'):
        self.volume_name = volume_name
        self.guest_mount_point = guest_mount_point
        self.mode = mode


def command() -> list:
    return ['container', 'c']


def help_summary(name: str) -> str:
    if name == 'c':
        return 'Alias for "container"'
    return "Various commands for containers"


def import_command(docker_client: docker.Client, args, state: dict):
    args.set_defaults(func=default)
    subparsers = args.add_subparsers(title="Container Commands", metavar="COMMAND")

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
    create_cmd.set_defaults(func=create_container)

    run_cmd = subparsers.add_parser('run', help="Create a new container and start it")
    run_cmd.set_defaults(func=run_container)

    for cmd in [create_cmd, run_cmd]:
        cmd.add_argument('--id', action='store_true', help="Display the ID of the created name instead of the name")
        # cmd.add_argument('-p', '--publish', nargs='*', help="Publish a container's port(s) to the host")
        option_help_msg = "Include a docker create option. " \
                          "See https://github.com/leftstache/dkr/blob/master/README.md for more information."
        cmd.add_argument('-o', '--option', action='append', help=option_help_msg)
        cmd.add_argument('--name', help="The name of the container")
        cmd.add_argument('-p', '--publish', action='append', help="Publish a container's port(s) to the host")
        cmd.add_argument('-v', '--volume', action='append', help="Bind mount a volume")
        cmd.add_argument('-e', '--env', action='append', help="Set environment variables")
        cmd.add_argument('image', help="The image to create the container from")
        cmd.add_argument('cmd', nargs="*", help="The command to run")

    start_cmd = subparsers.add_parser('start', help="Start an existing container")
    start_cmd.add_argument('container', nargs="+", help="The container to start")
    start_cmd.set_defaults(func=start_container)

    stop_cmd = subparsers.add_parser('stop', help="Stops a running container")

    if 'default_stop_time' not in state:
        state['default_stop_time'] = 3600

    stop_cmd_help = "The amount of time to wait, in seconds, before killing the container. " \
                    "Default: {}".format(state['default_stop_time'])
    stop_cmd.add_argument('-t', '--timeout', default=state['default_stop_time'], help=stop_cmd_help)
    stop_cmd.add_argument('container', nargs="+", help="The container to stop")
    stop_cmd.set_defaults(func=stop_container)

    rm_cmd = subparsers.add_parser('rm', help="Removes a stopped container")
    rm_cmd.add_argument('-f', '--force', action='store_true', default=False,
                        help='Force the removal of a running container (uses SIGKILL)')
    rm_cmd.add_argument('-l', '--link', action='store_true', default=False,
                        help='Remove the specified link')
    rm_cmd.add_argument('-v', '--volumes', action='store_true', default=False,
                        help='Remove the volumes associated with the container')
    rm_cmd.add_argument('container', nargs="+", help="The container to remove")
    rm_cmd.set_defaults(func=rm_container)


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
        args.container = get_last_container(state)

    container = docker_client.inspect_container(args.container)

    state['last_container'] = container['Id']

    if args.pprint:
        pprint(container)
        return

    if args.json:
        print(json.dumps(container, indent=4))
        return

    print(yaml.dump(container, default_flow_style=False))


def bind_volumes(volumes: list, docker_args: dict):
    volumes_cleaned = [split_volume(volume) for volume in volumes]
    docker_args['volumes'] = [volume.guest_mount_point for volume in volumes_cleaned]

    volume_host_config = {}
    for volume in volumes_cleaned:
        volume_host_config[volume.volume_name] = {
            'bind': volume.guest_mount_point,
            'mode': volume.mode
        }

    if 'host_config' not in docker_args:
        docker_args['host_config'] = {}
    docker_args['host_config']['binds'] = volume_host_config


def bind_ports(ports: list, docker_args: dict):
    ports_cleaned = [split_port(port) for port in ports]
    guest_ports = [format_guest_port(port) for port in ports_cleaned]
    host_config_ports = format_host_port(ports_cleaned)

    if 'host_config' not in docker_args:
        docker_args['host_config'] = {}

    docker_args['ports'] = guest_ports
    docker_args['host_config']['port_bindings'] = host_config_ports


def format_host_port(ports: list) -> dict:
    result = {}
    for port in ports:
        key = port.guest_port
        if port.proto:
            key = "{}/{}".format(port.guest_port, port.proto)

        value = port.host_port
        if port.ip:
            value = (port.ip, value)

        result[key] = value

    return result


def format_guest_port(port: Port):
    guest_port = port.guest_port
    if port.proto != 'tcp':
        return guest_port, port.proto
    return guest_port


def split_volume(volume: str) -> Volume:
    split = volume.split(":")
    if len(split) == 3:
        volume_name = split[0]
        guest_mount_point = split[1]
        mode = split[2]
    elif len(split) == 2:
        volume_name = split[0]
        guest_mount_point = split[1]
        mode = 'rw'
    else:
        raise errors.DkrException("Volume parameter must have 2 or 3 parts: NAME:PATH[:MODE]", errors.INVALID_INPUT)

    return Volume(volume_name, guest_mount_point, mode)


def split_port(port: str) -> Port:
    split = port.split(":")

    ip = None
    host_port = None
    guest_port = None
    proto = "tcp"

    if len(split) == 3 and '.' in split[0]:
        ip = split[0]
        host_port = split[1]
        guest_port = split[2]
    elif len(split) == 2 and '.' in split[0]:
        ip = split[0]
        guest_port = split[1]
    elif len(split) == 2:
        host_port = split[0]
        guest_port = split[1]
    elif len(split) == 1:
        guest_port = split[0]

    if guest_port and '/' in guest_port:
        split = guest_port.split('/')
        guest_port = split[0]
        proto = split[1]

    return Port(ip, int(host_port), int(guest_port), proto)


def create_container(docker_client: docker.Client, args, state: dict):
    image = args.image
    if image == '-':
        image = state['last_image']
    state['last_image'] = image

    cmd = args.cmd if args.cmd else None
    name = args.name if args.name else None

    ports = args.publish
    volumes = args.volume
    environment_variables = args.env

    docker_args = {}

    if 'option' in args:
        user_docker_options = cmd_to_json.parse_options(args.option)
        if user_docker_options:
            docker_args.update(user_docker_options)

    if volumes:
        bind_volumes(volumes, docker_args)

    if ports:
        bind_ports(ports, docker_args)

    if 'host_config' in docker_args:
        docker_args['host_config'] = docker_client.create_host_config(**docker_args['host_config'])

    # Do these last so that the -o options don't override them
    docker_args['image'] = image
    docker_args['command'] = cmd
    docker_args['name'] = name

    container = docker_client.create_container(**docker_args)

    state['last_container'] = container['Id']

    if container['Warnings']:
        print("WARNING:", container['Warnings'], file=sys.stderr)

    if args.id:
        print(container['Id'])
    else:
        container = docker_client.inspect_container(container)
        print(container['Name'][1:])


def start_container(docker_client: docker.Client, args, state: dict):
    containers = args.container

    started = start_containers(containers, docker_client, state, print_update=True)
    state['last_container'] = started[-1]


def start_containers(containers, docker_client, state, print_update=False) -> list:
    result = []
    for container in containers:
        if container == '-':
            container = get_last_container(state)
        docker_client.start(container)
        if print_update:
            print(container)
        result.append(container)
    return result


def run_container(docker_client: docker.Client, args, state: dict):
    create_container(docker_client, args, state)
    start_containers([get_last_container(state)], docker_client, state, print_update=False)


def stop_container(docker_client: docker.Client, args, state: dict):
    containers = args.container

    error = 0

    for container in containers:
        if container == '-':
            container = get_last_container(state)
        try:
            docker_client.stop(container, timeout=args.timeout)
            print(container)
        except docker.errors.APIError as e:
            status_code = e.response.status_code
            if status_code < 500:
                print(e.response.content.decode('utf-8').strip(), file=sys.stderr)
                error = errors.INVALID_INPUT
            else:
                print(e.response.content.decode('utf-8').strip(), file=sys.stderr)
                if error == 0:
                    error = errors.DOCKER_ERROR
        except docker.errors.DockerException as e:
            print(e.explanation.decode('utf-8').strip(), file=sys.stderr)
            if error == 0:
                error = errors.DOCKER_ERROR

    state['last_container'] = containers[-1]

    if error > 0:
        raise errors.DkrException("There was an error", error)


def rm_container(docker_client: docker.Client, args, state: dict):
    containers = args.container

    error = 0

    for container in containers:
        if container == '-':
            container = get_last_container(state)
        try:
            docker_client.remove_container(container, link=args.link, v=args.volumes, force=args.force)
            print(container)
        except docker.errors.NotFound:
            pass
        except docker.errors.APIError as e:
            status_code = e.response.status_code
            if status_code < 500:
                print(e.response.content.decode('utf-8').strip(), file=sys.stderr)
                error = errors.INVALID_INPUT
            else:
                print(e.response.content.decode('utf-8').strip(), file=sys.stderr)
                if error == 0:
                    error = errors.DOCKER_ERROR
        except docker.errors.DockerException as e:
            print(e.explanation.decode('utf-8').strip(), file=sys.stderr)
            if error == 0:
                error = errors.DOCKER_ERROR

    if error > 0:
        raise errors.DkrException("There was an error", error)

    if 'last_container' in state:
        state.pop('last_container')


def get_last_container(state):
    if 'last_container' not in state:
        raise errors.DkrException('No container to reference for "-"', errors.INVALID_INPUT)
    return state['last_container']


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

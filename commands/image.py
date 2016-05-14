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


def command() -> list:
    return ['image', 'i']


def help_summary(name: str) -> str:
    if name == 'i':
        return 'Alias for "image"'
    return "Various commands for images"


# noinspection PyUnusedLocal
def import_command(docker_client: docker.Client, args, state: dict):
    args.set_defaults(func=default)
    subparsers = args.add_subparsers(title="Container Commands", metavar="COMMAND")

    list_cmd = subparsers.add_parser('list', help="Lists images")
    list_cmd.add_argument('-a', '--all', action='store_true', help='Include all layers')
    list_cmd.add_argument('-q', '--quiet', action='store_true', help='Only print IDs')
    list_cmd.add_argument('--json', action='store_true', help='Render all as json')
    list_cmd.add_argument('--pprint', action='store_true', help='Dump contents using python\'s pprint function')
    list_cmd.set_defaults(func=list_images)

    inspect_cmd = subparsers.add_parser('inspect', help="Inspects the detail of an image")
    inspect_cmd.add_argument('image', help="The name or ID of the Image")
    inspect_cmd.add_argument('--json', action='store_true', help='Render all as json')
    inspect_cmd.add_argument('--pprint', action='store_true', help='Dump contents using python\'s pprint function')
    inspect_cmd.set_defaults(func=inspect_image)

    pull_cmd = subparsers.add_parser('pull', help="Pulls an image")
    pull_cmd.add_argument('image', help="The name of the image to pull")
    pull_cmd.add_argument('-a', '--all-tags', action='store_true', help='Download all tagged images in the repository')
    pull_cmd.set_defaults(func=pull_image)

    rm_cmd = subparsers.add_parser('rm', help="Removes an image")
    rm_cmd.add_argument('image', nargs="+", help="The name of the image to remove")
    rm_cmd.add_argument('-f', '--force', action='store_true', help='Force removal of the image')
    rm_cmd.add_argument('--no-prune', action='store_true', help='Do not delete untagged parents')
    rm_cmd.set_defaults(func=rm_image)


# noinspection PyUnusedLocal
def default(client: docker.Client, args, state: dict):
    print("No valid command specified. `{} image -h` for help.".format(sys.argv[0]), file=sys.stderr)


def list_images(client: docker.Client, args, state: dict):
    images = client.images(all=args.all)

    if args.pprint:
        pprint(images)
        return

    if args.json:
        print(json.dumps(images, indent=4, sort_keys=True))
        return

    table = []
    if args.quiet:
        headers = ()
    else:
        headers = ["ID", "REPO", "TAG", "CREATED", "SIZE", "VIRTUAL SIZE"]

    for image in images:
        full_id = image['Id']
        if full_id.startswith("sha256:"):
            full_id = full_id[7:]

        if args.quiet:
            row = []
            table.append(row)
            row.append(full_id)
            continue

        tags = image['RepoTags']

        for tag in tags:
            row = []
            table.append(row)

            row.append(full_id[:12])
            split = tag.split(":")
            row.append(split[0])
            row.append(split[1])

            created_seconds = image['Created']
            created_date = datetime.fromtimestamp(created_seconds)
            row.append(re.sub(r"\.[0-9]+", '', pretty.date(created_date, short=True)))

            row.append(_sizeof_fmt(image['Size']))
            row.append(_sizeof_fmt(image['VirtualSize']))

    print(tabulate(table, headers=headers, tablefmt="plain"))


def inspect_image(docker_client: docker.Client, args, state: dict):
    if args.image == '-':
        args.image = state['last_image']
    image = docker_client.inspect_image(args.image)

    state['last_image'] = image['RepoTags'][0]

    if args.pprint:
        pprint(image)
        return

    if args.json:
        print(json.dumps(image, indent=4))
        return

    print(yaml.dump(image, default_flow_style=False))


def pull_image(docker_client: docker.Client, args, state: dict):
    if args.image == '-':
        args.image = state['last_image']

    CURSOR_UP_ONE = '\x1b[1A'
    ERASE_LINE = '\x1b[2K'

    image = args.image

    if not args.all_tags and ":" not in image:
        image = "{}:latest".format(image)

    state['last_image'] = image

    print("Pulling {}".format(image))
    pull_status_gen = docker_client.pull(image, stream=True)

    previous_layer = ""
    for pull_status in pull_status_gen:
        pull_statuses = pull_status.decode('utf8').strip().split("\r\n")

        for ps in pull_statuses:
            pull_obj = json.loads(ps)

            this_id = pull_obj['id'] if 'id' in pull_obj else ""
            if previous_layer == this_id:
                print(CURSOR_UP_ONE + ERASE_LINE + CURSOR_UP_ONE)

            if 'status' in pull_obj:
                if 'progress' in pull_obj:
                    print("{} {} {}".format(pull_obj['status'], this_id, pull_obj['progress']))
                else:
                    print("{} {}".format(pull_obj['status'], this_id))
                previous_layer = this_id
            else:
                if 'error' in pull_obj:
                    print("Error while pulling: {}".format(pull_obj['error']))
                else:
                    print("derp? {}".format(json.dumps(pull_obj)))


def rm_image(docker_client: docker.Client, args, state: dict):
    images = args.image

    for image in images:
        if image == '-':
            image = state['last_image']

        if ":" not in image:
            image = "{}:latest".format(image)

        try:
            docker_client.remove_image(image, force=args.force, noprune=args.no_prune)
            print("Removed image {}".format(image))
        except docker.errors.NotFound as e:
            print(e.explanation.decode('utf8'), file=sys.stderr)


def _sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1000.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1000.0
    return "%.1f %s%s" % (num, 'Yi', suffix)
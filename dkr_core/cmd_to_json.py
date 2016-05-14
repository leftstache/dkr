import json
import sys

import dkr_core.errors


def parse_options(options: list):
    result = {}
    if options:
        for option in options:
            split = option.split(sep="=", maxsplit=1)

            name = str(split[0])
            value = str(split[1])

            if name.endswith(":"):
                name = name[0:-1]
                try:
                    value = json.loads(value)
                except json.decoder.JSONDecodeError:
                    raise dkr_core.errors.DkrException("Invalid json value: {}".format(value), dkr_core.errors.INVALID_INPUT)

            current_map = result
            name_split = name.split('.')
            nested_keys = name_split[0:-1]
            key = name_split[-1]
            for portion in nested_keys:
                if portion not in current_map:
                    current_map[portion] = {}
                current_map = current_map[portion]
            current_map[key] = value

    return result


if __name__ == "__main__":
    try:
        print(parse_options(sys.argv[1:]))
    except dkr_core.errors.DkrException as e:
        print(e.message, file=sys.stderr)
        sys.exit(e.exit_code)

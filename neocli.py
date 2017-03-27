#!/usr/bin/env python3
import sys
import argparse
import json
import logging
import socket
from neohub import NeoHub, NeoDevice

logging.basicConfig(level=logging.DEBUG)

def ok(what):
    if what:
        return 0
    else:
        print(repr(what))
        return 1

def main(neo, cmd, args):
    if cmd == "call":
        print(json.dumps(neo.call(json.loads(args[0])), sort_keys=True, indent=2))
        return 0

    if cmd == "stat":
        print(json.dumps(neo.update()[args[0]], sort_keys=True, indent=2))
        return 0

    if cmd == "switch_on":
        return neo.neoplugs()[args[0]].switch_on()

    if cmd == "switch_off":
        return neo.neoplugs()[args[0]].switch_off()

    if cmd == "script":
        p = neo.neoplugs()["F1 Hall Plug"]
        print(repr(p))
        p.switch_off()
        print(repr(p))
        p.switch_on()
        print(repr(p))

    if cmd == "rename_zone":
        return ok(neo.zone_title(args[0], args[1]))

    if cmd == "remove_zone":
        return ok(neo.remove_zone(args[0]))

    if cmd == "frost_on":
        return ok(neo.frost_on(args[0]))

    if cmd == "frost_off":
        return ok(neo.frost_off(args[0]))

    if cmd == "list":
        for name in neo.neostats():
            ns = neo.neostats()[name]
            print(repr(ns))
        print("")
        for name in neo.neoplugs():
            ns = neo.neoplugs()[name]
            print(repr(ns))
        return 0

    if cmd == "list-stats":
        for name in neo.neostats():
            ns = neo.neostats()[name]
            print(repr(ns))
        return 0

    if cmd == "list-plugs":
        for name in neo.neoplugs():
            ns = neo.neoplugs()[name]
            print(repr(ns))
        return 0

    return 1



if __name__ == '__main__':
    neo = NeoHub("10.0.0.197", 4242)
    # print(neo.set_temperature("Kitchen", 22))
    cmd = sys.argv[1]
    args = sys.argv[2:]
    sys.exit(main(neo, cmd, args))

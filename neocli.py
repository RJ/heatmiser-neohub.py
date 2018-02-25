#!/usr/bin/env python3
import asyncio
import sys
import argparse
import json
import logging
import socket
import os
from neohub import NeoHub, NeoDevice


logging.basicConfig(level=logging.DEBUG)


def ok(what):
    if what:
        return 0
    else:
        print(repr(what))
        return 1

async def main(neo, cmd, args):
    await neo.async_setup()

    if cmd == "call":
        print(json.dumps(await neo.call(json.loads(args[0])), sort_keys=True, indent=2))
        return 0

    if cmd == "stat":
        print(json.dumps(await neo.update()[args[0]], sort_keys=True, indent=2))
        return 0

    if cmd == "switch_on":
        return await neo.neoplugs()[args[0]].switch_on()

    if cmd == "switch_off":
        return await neo.neoplugs()[args[0]].switch_off()

    if cmd == "script":
        p = neo.neoplugs()["F1 Hall Plug"]
        print(repr(p))
        await p.switch_off()
        print(repr(p))
        await p.switch_on()
        print(repr(p))

    if cmd == "rename_zone":
        return ok(await neo.zone_title(args[0], args[1]))

    if cmd == "remove_zone":
        return ok(await neo.remove_zone(args[0]))

    if cmd == "frost_on":
        return ok(await neo.frost_on(args[0]))

    if cmd == "frost_off":
        return ok(await neo.frost_off(args[0]))

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
    host = os.environ.get("NEOHUB_IP")
    if host is None:
        print("Please set the NEOHUB_IP environment variable")
        print("eg: NEOHUB_IP=\"192.168.0.123\" %s ..." % sys.argv[0])
        sys.exit(1)

    loop = asyncio.get_event_loop()
    neo = NeoHub(host, 4242)

    cmd = sys.argv[1]
    args = sys.argv[2:]
    retval = loop.run_until_complete(main(neo, cmd, args))
    loop.close()
    sys.exit(retval)



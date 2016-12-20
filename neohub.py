#!/usr/bin/env python3
import sys
import argparse
import json
import logging
import socket

logging.basicConfig(level=logging.DEBUG)

def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj


def json_compare(j1, j2):
    return ordered(j1) == ordered(j2)


class Neostat(object):
    """Represents one Neostat thermostat.

    Method naming convention:

    .is_<feature>  - boolean to check if feature is enabled
    .set_<feature> - set feature value
    .<feature>     - get current value
 
    Notes:
    
    self.data is the merged dict from INFO and ENGINEERS_DATA for this device
    
    Mutates, such as set_frost_on, upon success, poke an updated value into
    self.data, rather than do another INFO/ENGINEERS_DATA query to the hub.
    """
    def __init__(self, hub, data):
        self.hub = hub
        self.name = data["device"]
        self.data = data

    def current_temperature(self):
        """Gets current temperature as measured at the thermostat"""
        return float(self.data["CURRENT_TEMPERATURE"])

    def currently_heating(self):
        """Is the thermostat currently heating the room"""
        return self.data["HEATING"]

    def is_frosted(self):
        """is the stat is currently in frost mode"""
        return self.data["STANDBY"]

    def frost_temperature(self):
        """returns the frost temperature, regardless of if frost mode is on"""
        return self.data["FROST TEMPERATURE"]

    def set_frost_temperature(self, temp):
        """sets the frost (minimum allowable) temperature"""
        if self.hub.set_frost(self.name, temp):
            self.data["FROST TEMPERATURE"] = temp
            return True
        else:
            return False

    def set_frost_on(self):
        """enable frost mode"""
        if self.hub.frost_on(self.name):
            self.data["STANDBY"] = True
            return True
        else:
            return False

    def set_frost_off(self):
        """disable frost mode"""
        if self.hub.frost_off(self.name):
            self.data["STANDBY"] = False
            return True
        else:
            return False

    def is_temperature_held(self):
        """Returns whether a hold temperature is in effect
        
        The temperature hold function allows you to manually override the
        current operating program and set a different temperature for a desired
        period."""
        return self.data["TEMP_HOLD"]

    def hold_temperature(self):
        """Gets the current hold temperature
        
        The temperature hold function allows you to manually override the
        current operating program and set a different temperature for a desired
        period."""
        return self.data["HOLD_TEMPERATURE"]



    def set_temperature(self):
        """Gets the so-called SET_TEMPERATURE

        This temperature is maintained only until the next programmed comfort
        level. At this time, the thermostat will revert back to the programmed
        levels
        """
        return float(self.data["CURRENT_SET_TEMPERATURE"])

    def set_set_temperature(self, temp):
        """Sets the so-called SET_TEMPERATURE

        This temperature is maintained only until the next programmed comfort
        level. At this time, the thermostat will revert back to the programmed
        levels
        """
        if self.hub.set_temp(self.name, temp):
            self.data["CURRENT_SET_TEMPERATURE"] = temp
            return True
    





class Neohub(object):

    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._sock = None
        self._devices = {}
        self._connected = False
        self.initial_zone_load()
        self.update()

    def ensure_connected(self):
        if self._connected:
            return True

        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(10)
            self._sock.connect((self._host, self._port))
            # logging.info("socket connected")
            self._connected = True
        except socket.timeout:
            logging.warn("socket timeout")
            self._connected = False
            self._sock.close()

    def initial_zone_load(self):
        zones = self.get_zones()
        for name in zones:
            self._devices[name] = {"id": zones[name]}

    def call(self, j, expecting=None):
        self.ensure_connected()
        self._sock.send(bytearray(json.dumps(j) + "\0\r", "utf-8"))
        response = ""
        # read everything that's available (we dont do pipelining for now)
        while True:
            try:
                buf = self._sock.recv(4096)
                if len(buf) == 0:
                    break
                response += str(buf, "utf-8")
                if "\0" in response:
                    response = response.rstrip("\0")
                    break

            except socket.timeout:
                logging.warning("Error reading from socket")
                break

        # logging.debug("RECV: %s", response)
        try:
            jobj = json.loads(response)
            # if no expected response, parse as JSON and return
            if expecting is None:
                return jobj
            else:
                # doing a simple ordered json compare, not just a string ==,
                # because a neohub update could subtly change the response
                # without breaking spec.
                if json_compare(jobj, expecting):
                    return True
                else:
                    logging.warning("Unexpected response from '%s'\nExpected: %s\nReceived: %s", json.dumps(j), repr(expecting), response)
                    return

        except json.JSONDecodeError:
            logging.warning("JSON decode error: %s", response)
            return None


    ## with expecting, we return true if all is ok.
    ## otherwise we should probably raise the specific error so it can be
    ## sent to the UI. (TODO)
    
    ## "device" can be a single device name, or list thereof, eg: "Kitchen"
    ##          or a list of device names, eg: ["Kitchen", "Bedroom 2"]
    ##          or a group name, eg: "First Floor"

    def set_away_mode(self, device, onoff):
        if onoff:
            return self.set_away_mode_on(device)
        else:
            return self.set_away_mode_off(device)

    # AWAY_ON
    # Possible results
    # {"result":"away on"}
    # {"error":"Could not complete away on"}
    # {"error":"Invalid argument to AWAY_OFF, should be a valid device or
    #           array of valid devices"}
    def set_away_mode_on(self, device):
        q = {"AWAY_ON": device}
        return self.call(q, expecting={"result": "away on"})

    # AWAY_OFF
    # Possible results
    # {"result":"away off"}
    # {"error":"Could not complete away off"}
    # {"error":"Invalid argument to AWAY_OFF, should be a valid device or
    #           array of valid devices"}
    def set_away_mode_off(self, device):
        q = {"AWAY_OFF": device}
        return self.call(q, expecting={"result": "away off"})

    # BOOST_OFF
    # {"BOOST_OFF":[{"hours":0,"minutes":10},<devices>]}
    # Possible results
    # {"result":"boost off"}"
    # {"error":"BOOST_OFF failed"}
    # {"error":"BOOST_OFF arguments not in an array"}
    # {"error":"Invalid first argument to BOOST_OFF, should be object"}
    # {"error":"Invalid second argument to BOOST_OFF, should be a valid
    # device or array of valid devices"}
    def boost_off(self, device, interval):
        q = {"BOOST_OFF": [interval, device]}
        return self.call(q, expecting={"result": "boost off"})

    # BOOST_ON
    # {"BOOST_OFF":[{"hours":0,"minutes":10},<devices>]]}
    # Possible results
    # {"result":"boost on"}
    # {"error":"BOOST_ON failed"}
    # {"error":"BOOST_ON arguments not in an array"}
    # {"error":"Invalid first argument to BOOST_ON, should be object"}
    # {"error":"Invalid second argument to BOOST_ON, should be a valid
    # device or array of valid devices"}
    def boost_on(self, device, interval):
        q = {"BOOST_ON": [interval, device]}
        return self.call(q, expecting={"result": "boost on"})

    # FROST_OFF
    # {"FROST_OFF":<device(s)>}
    # Possible results
    # {"result":"frost off"}
    # {"error":"Could not complete frost off"}
    # {"error":"Invalid argument to FROST_OFF, should be a valid device or
    # array of valid devices"}
    def frost_off(self, device):
        q = {"FROST_OFF": device}
        return self.call(q, expecting={"result": "frost off"})

    # FROST_ON
    # {"FROST_ON":<device(s)>}
    # Possible results
    # {"result":"frost on"}
    # {"error":"Could not complete frost on"}
    # {"error":"Invalid argument to FROST_ON, should be a valid device or
    # array of valid devices"}
    def frost_on(self, device):
        q = {"FROST_ON": device}
        return self.call(q, expecting={"result": "frost on"})

    # SET_FROST - aka set minimum temp
    # {"SET_FROST":[<temp>, <device(s)>]}
    # Possible results
    # {"result":"temperature was set"}
    # {"error":"set frost failed"}
    # {"error":"SET_FROST arguments not in an array"}
    # {"error":"Invalid first argument to SET_FROST, should be integer"}
    # {"error":"Invalid second argument to SET_FROST, should be a valid
    # device or array of valid devices"}
    def set_frost(self, device, temp):
        q = {"SET_FROST": [int(temp), device]}
        return self.call(q, expecting={"result": "temperature was set"})

    # SET_PREHEAT
    # {"SET_PREHEAT":[<temp>, <device(s)>]}
    # Possible results
    # {"result":"max preheat was set"}
    # {"error":"setting max preheat failed"}
    # {"error":"SET_PREHEAT arguments not in an array"}
    # {"error":"Invalid first argument to SET_PREHEAT, should be integer"}
    # {"error":"Invalid second argument to SET_PREHEAT, should be a valid
    # device or array of valid devices"}
    def set_preheat(self, device, temp):
        q = {"SET_PREHEAT": [int(temp), device]}
        return self.call(q, expecting={"result": "max preheat was set"})

    # SET_TEMP
    # {"SET_TEMP":[<temp>, <device(s)>]}
    # Possible results
    # {"result":"temperature was set"}
    # {"error":"setting temperature failed"}
    # {"error":"SET_TEMP arguments not in an array"}
    # {"error":"Invalid first argument to SET_TEMP, should be integer or
    # float"}
    # {"error":"Invalid second argument to SET_TEMP, should be a valid
    # device or array of valid devices"}
    def set_temp(self, device, temp):
        q = {"SET_TEMP": [int(temp), device]}
        return self.call(q, expecting={"result": "temperature was set"})

    # CREATE_GROUP
    # {"CREATE_GROUP":[[<devices>], <name>]}
    # Possible results
    # {"result":"group created"}
    # {"error":"Argument to CREATE_GROUP should be an array"}
    # {"error":"array for CREATE_GROUP should be size 2
    # [devices,groupname]"}
    # {"error":"first argument to CREATE_GROUP should be an array of
    # devices"}
    # {"error":"second argument to CREATE_GROUP should be a string (group
    # name)"}
    def create_group(self, device, name):
        q = {"CREATE_GROUP": [[device], str(name)]}
        return self.call(q, expecting={"result": "group created"})

    # DELETE_GROUP
    # {"DELETE_GROUP":<group>}
    # Possible results
    # {"result":"group removed"}
    # {"error":"Argument to DELETE_GROUP should be a string"}
    # NeoHub JSON commands 03 February 2016
    # Revision 2.5 Page 14 of 21
    # GET_GROUPS
    # {"GET_GROUPS":0}
    # Possible results
    # {"<groupname1>":["<devicename1>", "<devicename2>", <etc>],
    # "<groupname2>":[<members>], <etc>}
    def delete_group(self, name):
        q = {"DELETE_GROUP": str(name)}
        return self.call(q, expecting={"result": "group removed"})

    # ZONE_TITLE
    # {"ZONE_TITLE":[<oldname>, <newname>]}
    # Possible results
    # {"result":"zone renamed"}
    # {"error":"Argument to ZONE_TITLE should be an array"}
    # {"error":"array for ZONE_TITLE should be size 2 [oldname,newname]"}
    # {"error":"first argument to ZONE_TITLE should be a device"}
    # {"error":"second argument to ZONE_TITLE should be a string (new
    # device name)"}
    def zone_title(self, oldname, newname):
        q = {"ZONE_TITLE": [str(oldname), str(newname)]}
        return self.call(q, expecting={"result": "zone renamed"})

    def firmware_version(self):
        q = {"FIRMWARE": 0}
        ret = self.call(q)
        return ret["firmware version"]


    # GET_TEMPLOG
    # {"GET_TEMPLOG":<device(s)>}
    # Possible results
    # {"day:1":{<id>:[<96 temperatures for that day>], etc},"day:2":<same
    # as day1>, "today":<todays values>}
    # {"error":"Invalid argument to GET_TEMPLOG, should be a valid device
    # or array of valid devices"}
    def get_templog(self, device):
        q = {"GET_TEMPLOG": device}
        return self.call(q)

    # GET_ZONES
    # Possible results
    # {<id>:<number>,<id>:<number>,etc} the numbers are NeoHub internal
    # references and can be ignored, they will work as alternative for the
    # device names
    # {}
    def get_zones(self):
        q = {"GET_ZONES": 0}
        return self.call(q)

    # Merge together INFO and ENGINEERS_DATA for each device
    # and augment with some derived field names, in lower-case
    # since various things are inconsistently named
    def update(self):
        self.ensure_connected()
        resp = self.call({"INFO": "0"})
        resp2 = self.call({"ENGINEERS_DATA": "0"}) 
        for dev in resp["devices"]:
            name = dev["device"]
            merged = dev.copy()
            merged.update(resp2[name])
            # frost is called STANDBY i think :S
            merged["frost_enabled"] = merged["STANDBY"]
            self._devices[name].update(merged)
        #logging.info("DEVICES: %s", repr(devices))
        return devices

    def devices(self):
        return self._devices

    def device(self, name):
        return self._devices[name]


def ok(b):
    if b:
        return 0
    else:
        return 1


def main(neo, cmd, args):
    if cmd == "call":
        print(json.dumps(neo.call(json.loads(args[0])), sort_keys=True, indent=2))
        return 0

    if cmd == "stat":
        print(json.dumps(neo.update()[args[0]], sort_keys=True, indent=2))
        return 0

    if cmd == "frost_on":
        return ok(neo.frost_on(args[0]))

    if cmd == "frost_off":
        return ok(neo.frost_off(args[0]))

    if cmd == "list":
        neo.update()
        for dev in neo.devices().keys():
            d = neo.devices()[dev]
            frosty = "not frosted"
            if d["frost_enabled"]:
                frosty = "frosted"
            print("%s\tcurrent_temp:%s current_set_temp:%s frost_temp:%s %s" % (dev, d["CURRENT_TEMPERATURE"], d["CURRENT_SET_TEMPERATURE"], d["FROST TEMPERATURE"], frosty))
        return 0

    return 1



if __name__ == '__main__':
    neo = Neohub("10.0.0.197", 4242)
    # print(neo.set_temperature("Kitchen", 22))
    cmd = sys.argv[1]
    args = sys.argv[2:]
    sys.exit(main(neo, cmd, args))



    


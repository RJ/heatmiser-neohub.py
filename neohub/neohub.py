import asyncio
import json
import socket
import logging
import time
from .neostat import NeoStat
from .neoplug import NeoPlug


class NeoHub(object):

    def __init__(self, host, port, cache_duration=15):
        self._cache_duration = cache_duration or 15
        self._host = host
        self._port = port
        self._sock = None
        self.devices = {}
        self._neostats = {}
        self._neoplugs = {}
        self._connected = False
        self._last_update_time = 0
        self._dirty = False
        self._update_in_progress = False

    async def async_setup(self):
        await self.connect_to_hub()
        await self.initial_zone_load()
        await self.read_dcb()
        await self.update()

    async def connect_to_hub(self):
        self._reader, self._writer = await asyncio.open_connection(self._host, self._port)

    async def read_dcb(self):
        """Reads neohub settings"""
        self._dcb = await self.call({"READ_DCB": 100})

    async def initial_zone_load(self):
        self.devices = {}
        zones = await self.get_zones()
        for name in zones:
            self.devices[name] = {"id": zones[name]}

    async def call(self, j, expecting=None):
        payload = bytearray(json.dumps(j) + "\0\r", "utf-8")
        self._writer.write(payload)
        await self._writer.drain()

        response = ""
        while True:
            buf = (await self._reader.read(4096)).decode()
            response += buf
            if "\0" in response:
                response = response.rstrip("\0")
                break
            if len(response) == 0:
                break

        self._dirty = True

        # Got string back from hub, now decode json
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

    def neostats(self):
        return self._neostats

    def neoplugs(self):
        return self._neoplugs
    
    def corf(self):
        """Returns C or F, for celcius/farenheit"""
        return self._dcb["CORF"]

    ## with expecting, we return true if all is ok.
    ## otherwise we should probably raise the specific error so it can be
    ## sent to the UI. (TODO)
    
    ## "device" can be a single device name, or list thereof, eg: "Kitchen"
    ##          or a list of device names, eg: ["Kitchen", "Bedroom 2"]
    ##          or a group name, eg: "First Floor"

    async def set_away_mode(self, device, onoff):
        if onoff:
            return await self.set_away_mode_on(device)
        else:
            return await self.set_away_mode_off(device)

    # AWAY_ON
    # Possible results
    # {"result":"away on"}
    # {"error":"Could not complete away on"}
    # {"error":"Invalid argument to AWAY_OFF, should be a valid device or
    #           array of valid devices"}
    async def set_away_mode_on(self, device):
        q = {"AWAY_ON": device}
        return await self.call(q, expecting={"result": "away on"})

    # AWAY_OFF
    # Possible results
    # {"result":"away off"}
    # {"error":"Could not complete away off"}
    # {"error":"Invalid argument to AWAY_OFF, should be a valid device or
    #           array of valid devices"}
    async def set_away_mode_off(self, device):
        q = {"AWAY_OFF": device}
        return await self.call(q, expecting={"result": "away off"})

    # BOOST_OFF
    # {"BOOST_OFF":[{"hours":0,"minutes":10},<devices>]}
    # Possible results
    # {"result":"boost off"}"
    # {"error":"BOOST_OFF failed"}
    # {"error":"BOOST_OFF arguments not in an array"}
    # {"error":"Invalid first argument to BOOST_OFF, should be object"}
    # {"error":"Invalid second argument to BOOST_OFF, should be a valid
    # device or array of valid devices"}
    async def boost_off(self, device, interval):
        q = {"BOOST_OFF": [interval, device]}
        return await self.call(q, expecting={"result": "boost off"})

    # BOOST_ON
    # {"BOOST_OFF":[{"hours":0,"minutes":10},<devices>]]}
    # Possible results
    # {"result":"boost on"}
    # {"error":"BOOST_ON failed"}
    # {"error":"BOOST_ON arguments not in an array"}
    # {"error":"Invalid first argument to BOOST_ON, should be object"}
    # {"error":"Invalid second argument to BOOST_ON, should be a valid
    # device or array of valid devices"}
    async def boost_on(self, device, interval):
        q = {"BOOST_ON": [interval, device]}
        return await self.call(q, expecting={"result": "boost on"})

    # FROST_OFF
    # {"FROST_OFF":<device(s)>}
    # Possible results
    # {"result":"frost off"}
    # {"error":"Could not complete frost off"}
    # {"error":"Invalid argument to FROST_OFF, should be a valid device or
    # array of valid devices"}
    async def frost_off(self, device):
        q = {"FROST_OFF": device}
        return await self.call(q, expecting={"result": "frost off"})

    # FROST_ON
    # {"FROST_ON":<device(s)>}
    # Possible results
    # {"result":"frost on"}
    # {"error":"Could not complete frost on"}
    # {"error":"Invalid argument to FROST_ON, should be a valid device or
    # array of valid devices"}
    async def frost_on(self, device):
        q = {"FROST_ON": device}
        return await self.call(q, expecting={"result": "frost on"})

    # SET_FROST - aka set minimum temp
    # {"SET_FROST":[<temp>, <device(s)>]}
    # Possible results
    # {"result":"temperature was set"}
    # {"error":"set frost failed"}
    # {"error":"SET_FROST arguments not in an array"}
    # {"error":"Invalid first argument to SET_FROST, should be integer"}
    # {"error":"Invalid second argument to SET_FROST, should be a valid
    # device or array of valid devices"}
    async def set_frost(self, device, temp):
        q = {"SET_FROST": [int(temp), device]}
        return await self.call(q, expecting={"result": "temperature was set"})

    # SET_PREHEAT
    # {"SET_PREHEAT":[<temp>, <device(s)>]}
    # Possible results
    # {"result":"max preheat was set"}
    # {"error":"setting max preheat failed"}
    # {"error":"SET_PREHEAT arguments not in an array"}
    # {"error":"Invalid first argument to SET_PREHEAT, should be integer"}
    # {"error":"Invalid second argument to SET_PREHEAT, should be a valid
    # device or array of valid devices"}
    async def set_preheat(self, device, temp):
        q = {"SET_PREHEAT": [int(temp), device]}
        return await self.call(q, expecting={"result": "max preheat was set"})

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
    async def set_temp(self, device, temp):
        q = {"SET_TEMP": [int(temp), device]}
        return await self.call(q, expecting={"result": "temperature was set"})

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
    async def create_group(self, device, name):
        q = {"CREATE_GROUP": [[device], str(name)]}
        return await self.call(q, expecting={"result": "group created"})

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
    async def delete_group(self, name):
        q = {"DELETE_GROUP": str(name)}
        return await self.call(q, expecting={"result": "group removed"})

    # ZONE_TITLE
    # {"ZONE_TITLE":[<oldname>, <newname>]}
    # Possible results
    # {"result":"zone renamed"}
    # {"error":"Argument to ZONE_TITLE should be an array"}
    # {"error":"array for ZONE_TITLE should be size 2 [oldname,newname]"}
    # {"error":"first argument to ZONE_TITLE should be a device"}
    # {"error":"second argument to ZONE_TITLE should be a string (new
    # device name)"}
    async def zone_title(self, oldname, newname):
        q = {"ZONE_TITLE": [str(oldname), str(newname)]}
        return await self.call(q, expecting={"result": "zone renamed"})

    async def firmware_version(self):
        q = {"FIRMWARE": 0}
        ret = await self.call(q)
        return ret["firmware version"]


    # GET_TEMPLOG
    # {"GET_TEMPLOG":<device(s)>}
    # Possible results
    # {"day:1":{<id>:[<96 temperatures for that day>], etc},"day:2":<same
    # as day1>, "today":<todays values>}
    # {"error":"Invalid argument to GET_TEMPLOG, should be a valid device
    # or array of valid devices"}
    async def get_templog(self, device):
        q = {"GET_TEMPLOG": device}
        return await self.call(q)

    # GET_ZONES
    # Possible results
    # {<id>:<number>,<id>:<number>,etc} the numbers are NeoHub internal
    # references and can be ignored, they will work as alternative for the
    # device names
    # {}
    async def get_zones(self):
        q = {"GET_ZONES": 0}
        return await self.call(q)

    # REMOVE_ZONE
    # {"REMOVE_ZONE":<zone>}
    # Possible results
    # {"result":"zone removed"}
    # {"error":"Invalid argument to REMOVE_ZONE, should be a valid device or array of valid devices"}
    async def remove_zone(self, device):
        q = {"REMOVE_ZONE": device}
        return await self.call(q, expecting={"result": "zone removed"})

    # Note1
    # Neoplug is seen primarily as a timeclock by the system with a few additional commands for manual
    # switching so use timeclock commands for programming
    # Note2
    # To override the neoplug for a period of time use TIMER_HOLD_ON and TIMER HOLD OFF
    # To turn the output on or off use TIMER_ON or TIMER_OFF

    # MANUAL_ON
    # {"MANUAL_ON":<devices>}
    # Turns on NeoPlug manual mode. This is the opposite of automatic and
    # disables the time clock,effectively turning the neoplug into a
    # switch.
    # Possible results
    # {"result":"manual on"}
    # {"error":"Could not complete manual on"}
    # {"error":"Invalid argument to MANUAL_ON, should be a valid device or
    # array of valid devices"}
    # MANUAL_OFF
    # {"MANUAL_OFF":<devices>}
    # Turns off NeoPlug manual mode.
    # Possible results
    # {"result":"manual off"}
    # {"error":"Could not complete manual off"}
    # {"error":"Invalid argument to MANUAL_OFF, should be a valid device
    # or array of valid devices"}
    async def switch_plug_on(self, device):
        q = {"TIMER_ON": device}
        return await self.call(q, expecting={"result": "time clock overide on"})

    async def switch_plug_off(self, device):
        q = {"TIMER_OFF": device}
        return await self.call(q, expecting={"result": "timers off"})

    # Guard / memoize / debounce access to actual_update()
    async def update(self, force_update=False):
        if self._update_in_progress:
            return self.devices

        if (self._dirty or self._last_update_time is None or force_update or (time.time() - self._last_update_time) >= self._cache_duration):
            self._last_update_time = time.time()
            logging.debug("Querying NeoHub for all device data")
            self._dirty = False
            return await self.actual_update()
        else:
            #logging.debug("(cached)")
            return self.devices

    # Merge together INFO and ENGINEERS_DATA for each device
    # and augment with some derived field names, in lower-case
    # since various things are inconsistently named
    async def actual_update(self):
        self._update_in_progress = True
        resp = await self.call({"INFO": "0"})
        resp2 = await self.call({"ENGINEERS_DATA": "0"}) 
        for dev in resp["devices"]:
            name = dev["device"]
            merged = dev.copy()
            merged.update(resp2[name])
            self.devices[name].update(merged)

            # device type 1 = neostat
            #             6 = neoplug
            if merged["DEVICE_TYPE"] == 0:
                # offline therm?
                pass
            elif merged["DEVICE_TYPE"] == 1:
                if name not in self._neostats:
                    self._neostats[name] = NeoStat(self, name)
            elif merged["DEVICE_TYPE"] == 6:
                if name not in self._neoplugs:
                    self._neoplugs[name] = NeoPlug(self, name)
            else:
                logging.warn("Unimplemented NeoSomething device_type(%s)! "
                             "Only support neostat(1) and neoplug(6) at the mo" % (merged["DEVICE_TYPE"]))
                print(repr(merged))
                pass

        self._update_in_progress = False
        return self.devices

    def devices(self):
        return self.devices

    def device(self, name):
        return self.devices[name]


def json_compare(j1, j2):
    return ordered(j1) == ordered(j2)

def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj

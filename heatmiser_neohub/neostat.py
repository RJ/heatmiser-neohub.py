import asyncio
from .neodevice import NeoDevice


class NeoStat(NeoDevice):
    """Represents one NeoStat thermostat.

    Method naming convention:

    .is_<feature>  - boolean to check if feature is enabled
    .set_<feature> - set feature value
    .<feature>     - get current value
 
    Mutates, such as set_frost_on, upon success, poke an updated value into
    self, rather than do another INFO/ENGINEERS_DATA query to the hub.
    """
    def __repr__(self):
        return "<NeoStat id=%-2d temp=%0.1f frost=%s name='%s'>" % (self['id'], self.current_temperature(), self.is_frosted(), self.name)

    def current_temperature(self):
        """Gets current temperature as measured at the thermostat"""
        return float(self["CURRENT_TEMPERATURE"])

    def currently_heating(self):
        """Is the thermostat currently heating the room"""
        return self["HEATING"]

    def is_frosted(self):
        """is the stat is currently in frost mode"""
        return self["STANDBY"]

    def frost_temperature(self):
        """returns the frost temperature, regardless of if frost mode is on"""
        return self["FROST TEMPERATURE"]

    async def set_frost_temperature(self, temp):
        """sets the frost (minimum allowable) temperature"""
        if await self.hub.set_frost(self.name, temp):
            self["FROST TEMPERATURE"] = temp
            return True
        else:
            return False

    async def set_frost_on(self):
        """enable frost mode"""
        if await self.hub.frost_on(self.name):
            self["STANDBY"] = True
            return True
        else:
            return False

    async def set_frost_off(self):
        """disable frost mode"""
        if await self.hub.frost_off(self.name):
            self["STANDBY"] = False
            return True
        else:
            return False

    def is_temperature_held(self):
        """Returns whether a hold temperature is in effect
        
        The temperature hold function allows you to manually override the
        current operating program and set a different temperature for a desired
        period."""
        return self["TEMP_HOLD"]

    def hold_temperature(self):
        """Gets the current hold temperature
        
        The temperature hold function allows you to manually override the
        current operating program and set a different temperature for a desired
        period."""
        return self["HOLD_TEMPERATURE"]

    def set_temperature(self):
        """Gets the so-called SET_TEMPERATURE

        This temperature is maintained only until the next programmed comfort
        level. At this time, the thermostat will revert back to the programmed
        levels
        """
        return float(self["CURRENT_SET_TEMPERATURE"])

    async def set_set_temperature(self, temp):
        """Sets the so-called SET_TEMPERATURE

        This temperature is maintained only until the next programmed comfort
        level. At this time, the thermostat will revert back to the programmed
        levels
        """
        if await self.hub.set_temp(self.name, temp):
            self["CURRENT_SET_TEMPERATURE"] = temp

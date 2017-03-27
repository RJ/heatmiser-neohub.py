"""
homeassistant.components.thermostat.heatmiser_neohub
----------------------------------------------------

Talks to neohub, controls neostat zigbee thermostats and neoplugs
"""
import asyncio
import logging

import voluptuous as vol

from homeassistant.components.climate import ClimateDevice, PLATFORM_SCHEMA

from homeassistant.components.climate import (
    STATE_HEAT, STATE_COOL, STATE_IDLE, ClimateDevice, PLATFORM_SCHEMA)
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT, STATE_ON, STATE_OFF, ATTR_TEMPERATURE)
from homeassistant.const import (
    TEMP_CELSIUS, TEMP_FAHRENHEIT, ATTR_TEMPERATURE, CONF_PORT, CONF_NAME)

from homeassistant.components.switch import SwitchDevice
from homeassistant.const import DEVICE_DEFAULT_NAME

import homeassistant.helpers.config_validation as cv

import socket
import json

from .neohub import NeoHub, NeoPlug

_LOGGER = logging.getLogger(__name__)

CONF_HOST = 'host'
CONF_PORT = 'port'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT): cv.port,
})

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """ Query neohub, create a hass ClimateDevice for each """
    host = config.get(CONF_HOST, "10.0.0.197")
    port = config.get("CONF_PORT", 4242)
    hub = NeoHub(host, port)

    neoplugs = hub.neoplugs()
    async_add_devices([NeoPlugSwitch(neoplugs[name], None, False) for name in neoplugs])

    neostats = hub.neostats()
    async_add_devices([NeoStatDevice(neostats[name]) for name in neostats])







class NeoStatDevice(ClimateDevice):
    """ Represents a Heatmiser Neostat thermostat. """
    def __init__(self, n):
        self._neo = n

    @property
    def should_poll(self):
        """ No polling needed for a demo thermostat. """
        return True

    @property
    def name(self):
        """ Returns the name. """
        return self._neo.name

    @property
    def current_operation(self):
        """ Returns current operation. heat, cool idle """
        if self._neo.currently_heating():
            return STATE_HEAT
        else:
            return STATE_IDLE

    @property
    def temperature_unit(self):
        """ Returns the unit of measurement. """
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """ Returns the current temperature. """
        return self._neo.current_temperature()

    @property
    def target_temperature(self):
        """ Returns the temperature we try to reach. """
        return self._neo.set_temperature()

    @property
    def min_temp(self):
        return self._neo.frost_temperature()

    @property
    def is_away_mode_on(self):
        """ Returns if away mode is on. """
        return self._neo.is_frosted()

    def set_temperature(self, **kwargs):
        """ Set new target temperature. """
        new_temp = int(kwargs.get(ATTR_TEMPERATURE))
        self._neo.set_set_temperature(new_temp)

    def turn_away_mode_on(self):
        """ Turns away mode on. """
        self._neo.set_frost_on()
        return

    def turn_away_mode_off(self):
        """ Turns away mode off. """
        self._neo.set_frost_off()
        return

    @asyncio.coroutine
    def async_update(self):
        yield self._neo.update()


class NeoPlugSwitch(SwitchDevice):
    def __init__(self, neo, icon, assumed):
        _LOGGER.debug("Neo Switch: %s" % repr(neo))
        self._neo = neo
        self._state = neo.is_on()
        self._icon = icon
        self._assumed = assumed

    @property
    def should_poll(self):
        """No polling needed for a demo switch."""
        return True

    @property
    def name(self):
        return self._neo.name or DEVICE_DEFAULT_NAME

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return self._icon

    @property
    def assumed_state(self):
        """Return if the state is based on assumptions."""
        return self._assumed

    @asyncio.coroutine
    def async_update(self):
        yield self._neo.update()

    @property
    def is_on(self):
        return self._neo.is_on()

    def turn_on(self, **kwargs):
        self._state = True
        self._neo.switch_on()
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._state = False
        self._neo.switch_off()
        self.schedule_update_ha_state()


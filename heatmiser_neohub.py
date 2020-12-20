"""
homeassistant.components.thermostat.heatmiser_neohub
----------------------------------------------------

Talks to neohub, controls neostat zigbee thermostats and neoplugs


OLD - hass component separate now, this just pypy lib, per hass guidelines

"""
import asyncio
import logging

import voluptuous as vol

from homeassistant.components.climate import ClimateDevice, PLATFORM_SCHEMA

from homeassistant.components.climate import (
    STATE_AUTO, STATE_COOL, STATE_HEAT, SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_HIGH, SUPPORT_TARGET_TEMPERATURE_LOW,
    SUPPORT_OPERATION_MODE, SUPPORT_AWAY_MODE, STATE_IDLE, ClimateDevice, PLATFORM_SCHEMA)
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

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_TARGET_TEMPERATURE_HIGH |
                 SUPPORT_TARGET_TEMPERATURE_LOW | SUPPORT_OPERATION_MODE |
                 SUPPORT_AWAY_MODE)

async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """ Query neohub, create a hass ClimateDevice for each """
    _LOGGER.info("Starting async_setup_platform")
    host = config.get(CONF_HOST, "10.0.0.197")
    port = config.get("CONF_PORT", 4242)
    hub = NeoHub(host, port)
    await hub.async_setup()

    plugs = hub.neoplugs()
    stats = hub.neostats()
    neoplugs = [NeoPlugSwitch(plugs[name], None, False) for name in plugs]
    neostats = [NeoStatDevice(stats[name]) for name in stats]
    async_add_devices(neoplugs)
    async_add_devices(neostats)
    _LOGGER.info("Added %s plugs, %s stats" % (len(plugs), len(stats)))


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

    def update_after(self, secs):
        async def wait_and_update():
            await asyncio.sleep(secs)
            _LOGGER.info("updating after delay of %s" % (secs))
            await self.async_update()
            #self.async_schedule_update_ha_state()

        asyncio.ensure_future(wait_and_update())

    async def async_set_temperature(self, **kwargs):
        """ Set new target temperature. """
        new_temp = int(kwargs.get(ATTR_TEMPERATURE))
        await self._neo.set_set_temperature(new_temp)
        self.update_after(1.5)

    async def async_turn_away_mode_on(self):
        """ Turns away mode on. """
        await self._neo.set_frost_on()
        self.update_after(1.5)

    async def async_turn_away_mode_off(self):
        """ Turns away mode off. """
        await self._neo.set_frost_off()
        self.update_after(1.5)

    async def async_update(self):
        await self._neo.update()

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS
                            


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

    async def async_update(self):
        await self._neo.update()

    @property
    def is_on(self):
        return self._neo.is_on()

    async def async_turn_on(self, **kwargs):
        self._state = True
        await self._neo.switch_on()
        self.update_after(1.5)
        #await self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        self._state = False
        await self._neo.switch_off()
        self.update_after(1.5)
        #await self.async_schedule_update_ha_state()

    def update_after(self, secs):
        async def wait_and_update():
            await asyncio.sleep(secs)
            _LOGGER.info("updating after delay of %s" % (secs))
            await self.async_update()
            #self.async_schedule_update_ha_state()

        asyncio.ensure_future(wait_and_update())


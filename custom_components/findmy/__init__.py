"""The Find My integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_ACCOUNT, CONF_PLIST
from .coordinator import FindMyUpdateCoordinator
from .findmy_hub import FindMyHub

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER]

type FindMyConfigEntry = ConfigEntry[FindMyUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: FindMyConfigEntry) -> bool:
    """Set up Find My from a config entry."""

    hub = FindMyHub(entry.data[CONF_URL])
    hub.restore_account(entry.data[CONF_ACCOUNT])
    hub.load_plist(entry.data[CONF_PLIST])

    coordinator = FindMyUpdateCoordinator(hass=hass, hub=hub)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: FindMyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

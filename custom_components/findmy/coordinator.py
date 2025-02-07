"""DataUpdateCoordinator for the FindMy integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_UPDATE_INTERVAL
from .findmy_hub import FindMyHub, FindMyReport

_LOGGER = logging.getLogger(__name__)


class FindMyUpdateCoordinator(DataUpdateCoordinator[FindMyReport]):
    """The FindMy update coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        hub: FindMyHub,
    ) -> None:
        """Initialize the FindMy coordinator."""
        self.hub = hub

        super().__init__(
            hass,
            _LOGGER,
            name="FindMy Accessory",
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> FindMyReport:
        """Trigger position update."""
        return await self.hub.get_position()

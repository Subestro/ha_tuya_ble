"""The Tuya BLE integration."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Callable

from homeassistant.components.switch import (
    SwitchEntityDescription,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)


TuyaBLESwitchGetter = (
    Callable[["TuyaBLESwitch", TuyaBLEProductInfo], bool | None] | None
)


TuyaBLESwitchIsAvailable = (
    Callable[["TuyaBLESwitch", TuyaBLEProductInfo], bool] | None
)


TuyaBLESwitchSetter = (
    Callable[["TuyaBLESwitch", TuyaBLEProductInfo, bool], None] | None
)


@dataclass
class TuyaBLESwitchMapping:
    dp_id: int
    description: SwitchEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None
    bitmap_mask: bytes | None = None
    is_available: TuyaBLESwitchIsAvailable = None
    getter: TuyaBLESwitchGetter = None
    setter: TuyaBLESwitchSetter = None


def is_remote_unlock_available(
    self: TuyaBLESwitch, product: TuyaBLEProductInfo
) -> bool:
    # Add your logic here to determine if remote unlock is available for the device
    return True  # For demonstration, assuming it's always available


def remote_unlock_setter(
    self: TuyaBLESwitch, product: TuyaBLEProductInfo, value: bool
) -> None:
    # Add your logic here to trigger remote unlock action
    pass


@dataclass
class TuyaBLECategorySwitchMapping:
    products: dict[str, list[TuyaBLESwitchMapping]] | None = None
    mapping: list[TuyaBLESwitchMapping] | None = None


mapping: dict[str, TuyaBLECategorySwitchMapping] = {
    "ms": TuyaBLECategorySwitchMapping(
        products={
            "isljqiq1": [  # Smart Lock
                TuyaBLESwitchMapping(
                    dp_id=62,
                    description=SwitchEntityDescription(
                        key="remote_unlock",
                        icon="mdi:lock-open-outline",
                        entity_category=EntityCategory.DOOR,
                    ),
                    is_available=is_remote_unlock_available,
                    setter=remote_unlock_setter,
                ),
            ],
        },
    ),
}


def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLECategorySwitchMapping]:
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if category.mapping is not None:
            return category.mapping
        else:
            return []
    else:
        return []


class TuyaBLESwitch(TuyaBLEEntity, SwitchEntity):
    """Representation of a Tuya BLE Switch."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLESwitchMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        # Add your logic here to determine the state of the switch
        return False

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self._mapping.setter:
            return self._mapping.setter(self, self._product, True)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self._mapping.setter:
            return self._mapping.setter(self, self._product, False)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        result = super().available
        if result and self._mapping.is_available:
            result = self._mapping.is_available(self, self._product)
        return result


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLESwitch] = []
    for mapping in mappings:
        if mapping.force_add or data.device.datapoints.has_id(
            mapping.dp_id, mapping.dp_type
        ):
            entities.append(
                TuyaBLESwitch(
                    hass,
                    data.coordinator,
                    data.device,
                    data.product,
                    mapping,
                )
            )
    async_add_entities(entities)


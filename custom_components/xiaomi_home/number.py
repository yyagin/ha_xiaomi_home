# -*- coding: utf-8 -*-
"""
Copyright (C) 2024 Xiaomi Corporation.

The ownership and intellectual property rights of Xiaomi Home Assistant
Integration and related Xiaomi cloud service API interface provided under this
license, including source code and object code (collectively, "Licensed Work"),
are owned by Xiaomi. Subject to the terms and conditions of this License, Xiaomi
hereby grants you a personal, limited, non-exclusive, non-transferable,
non-sublicensable, and royalty-free license to reproduce, use, modify, and
distribute the Licensed Work only for your use of Home Assistant for
non-commercial purposes. For the avoidance of doubt, Xiaomi does not authorize
you to use the Licensed Work for any other purpose, including but not limited
to use Licensed Work to develop applications (APP), Web services, and other
forms of software.

You may reproduce and distribute copies of the Licensed Work, with or without
modifications, whether in source or object form, provided that you must give
any other recipients of the Licensed Work a copy of this License and retain all
copyright and disclaimers.

Xiaomi provides the Licensed Work on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied, including, without
limitation, any warranties, undertakes, or conditions of TITLE, NO ERROR OR
OMISSION, CONTINUITY, RELIABILITY, NON-INFRINGEMENT, MERCHANTABILITY, or
FITNESS FOR A PARTICULAR PURPOSE. In any event, you are solely responsible
for any direct, indirect, special, incidental, or consequential damages or
losses arising from the use or inability to use the Licensed Work.

Xiaomi reserves all rights not expressly granted to you in this License.
Except for the rights expressly granted by Xiaomi under this License, Xiaomi
does not authorize you in any form to use the trademarks, copyrights, or other
forms of intellectual property rights of Xiaomi and its affiliates, including,
without limitation, without obtaining other written permission from Xiaomi, you
shall not use "Xiaomi", "Mijia" and other words related to Xiaomi or words that
may make the public associate with Xiaomi in any form to publicize or promote
the software or hardware devices that use the Licensed Work.

Xiaomi has the right to immediately terminate all your authorization under this
License in the event:
1. You assert patent invalidation, litigation, or other claims against patents
or other intellectual property rights of Xiaomi or its affiliates; or,
2. You make, have made, manufacture, sell, or offer to sell products that knock
off Xiaomi or its affiliates' products.

Number entities for Xiaomi Home.
"""
from __future__ import annotations
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.number import NumberEntity

from .miot.const import DOMAIN
from .miot.miot_spec import MIoTSpecAction, MIoTSpecProperty
from .miot.miot_device import MIoTActionEntity, MIoTDevice, MIoTPropertyEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a config entry."""
    device_list: list[MIoTDevice] = hass.data[DOMAIN]['devices'][
        config_entry.entry_id]

    new_entities = []
    for miot_device in device_list:
        for prop in miot_device.prop_list.get('number', []):
            new_entities.append(Number(miot_device=miot_device, spec=prop))
        for action in miot_device.action_list.get('number', []):
            new_entities.append(
                ActionNumber(miot_device=miot_device, spec=action))

    if new_entities:
        async_add_entities(new_entities)


class Number(MIoTPropertyEntity, NumberEntity):
    """Number entities for Xiaomi Home."""

    def __init__(self, miot_device: MIoTDevice, spec: MIoTSpecProperty) -> None:
        """Initialize the Notify."""
        super().__init__(miot_device=miot_device, spec=spec)
        # Set device_class
        self._attr_device_class = spec.device_class
        # Set unit
        if self.spec.external_unit:
            self._attr_native_unit_of_measurement = self.spec.external_unit
        # Set icon
        if self.spec.icon and not self.device_class:
            self._attr_icon = self.spec.icon
        # Set value range
        if self._value_range:
            self._attr_native_min_value = self._value_range.min_
            self._attr_native_max_value = self._value_range.max_
            self._attr_native_step = self._value_range.step

    @property
    def native_value(self) -> Optional[float]:
        """Return the current value of the number."""
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.set_property_async(value=value)


class ActionNumber(MIoTActionEntity, NumberEntity):
    """Number entities backed by a single-argument MIoT action."""

    _in_prop: MIoTSpecProperty

    def __init__(self, miot_device: MIoTDevice, spec: MIoTSpecAction) -> None:
        """Initialize the ActionNumber."""
        super().__init__(miot_device=miot_device, spec=spec)
        self._in_prop = spec.in_[0]
        self._attr_native_value = None
        if self._in_prop.value_range:
            self._attr_native_min_value = self._in_prop.value_range.min_
            self._attr_native_max_value = self._in_prop.value_range.max_
            self._attr_native_step = self._in_prop.value_range.step
            self._attr_native_value = self._in_prop.value_range.min_

    @property
    def native_value(self) -> Optional[float]:
        """Return the last value sent to the action."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Execute the action with the given value."""
        value_out: Any = (
            int(value) if self._in_prop.format_ == int else value)
        await self.action_async(
            in_list=[{'piid': self._in_prop.iid, 'value': value_out}])
        self._attr_native_value = value
        self.async_write_ha_state()

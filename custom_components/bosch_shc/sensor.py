"""Platform for sensor integration."""
from __future__ import annotations
from .device import SHCDevice
from .session import SHCSession

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    ENERGY_KILO_WATT_HOUR,
    PERCENTAGE,
    POWER_WATT,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_SESSION, DOMAIN
from .entity import SHCEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SHC sensor platform."""
    entities: list[SensorEntity] = []
    session: SHCSession = hass.data[DOMAIN][config_entry.entry_id][DATA_SESSION]

    for sensor in session.device_helper.thermostats:
        entities.append(
            TemperatureSensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )
        entities.append(
            ValveTappetSensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )

    for sensor in session.device_helper.wallthermostats:
        entities.append(
            TemperatureSensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )
        entities.append(
            HumiditySensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )

    for sensor in session.device_helper.twinguards:
        entities.append(
            TemperatureSensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )
        entities.append(
            HumiditySensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )
        entities.append(
            PuritySensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )
        entities.append(
            AirQualitySensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )
        entities.append(
            TemperatureRatingSensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )
        entities.append(
            HumidityRatingSensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )
        entities.append(
            PurityRatingSensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )

    for sensor in (
        session.device_helper.smart_plugs + session.device_helper.light_switches
    ):
        entities.append(
            PowerSensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )
        entities.append(
            EnergySensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )

    for sensor in session.device_helper.smart_plugs_compact:
        entities.append(
            PowerSensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )
        entities.append(
            EnergySensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )
        entities.append(
            CommunicationQualitySensor(
                device=sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )

    if entities:
        async_add_entities(entities)


class TemperatureSensor(SHCEntity, SensorEntity):
    """Representation of an SHC temperature reporting sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = TEMP_CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC temperature reporting sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{device.name} Temperature"
        self._attr_unique_id = f"{device.serial}_temperature"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._device.temperature


class HumiditySensor(SHCEntity, SensorEntity):
    """Representation of an SHC humidity reporting sensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC humidity reporting sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{device.name} Humidity"
        self._attr_unique_id = f"{device.serial}_humidity"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._device.humidity


class PuritySensor(SHCEntity, SensorEntity):
    """Representation of an SHC purity reporting sensor."""

    _attr_icon = "mdi:molecule-co2"
    _attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC purity reporting sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{device.name} Purity"
        self._attr_unique_id = f"{device.serial}_purity"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._device.purity


class AirQualitySensor(SHCEntity, SensorEntity):
    """Representation of an SHC airquality reporting sensor."""

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC airquality reporting sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{device.name} Air Quality"
        self._attr_unique_id = f"{device.serial}_airquality"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._device.combined_rating.name

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "rating_description": self._device.description,
        }


class TemperatureRatingSensor(SHCEntity, SensorEntity):
    """Representation of an SHC temperature rating sensor."""

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC temperature rating sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{device.name} Temperature Rating"
        self._attr_unique_id = f"{device.serial}_temperature_rating"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._device.temperature_rating.name


class CommunicationQualitySensor(SHCEntity, SensorEntity):
    """Representation of an SHC communication quality reporting sensor."""

    _attr_icon = "mdi:wifi"

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC communication quality reporting sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{device.name} Communication Quality"
        self._attr_unique_id = f"{device.serial}_communication_quality"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._device.communicationquality.name


class HumidityRatingSensor(SHCEntity, SensorEntity):
    """Representation of an SHC humidity rating sensor."""

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC humidity rating sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{device.name} Humidity Rating"
        self._attr_unique_id = f"{device.serial}_humidity_rating"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._device.humidity_rating.name


class PurityRatingSensor(SHCEntity, SensorEntity):
    """Representation of an SHC purity rating sensor."""

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC purity rating sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{device.name} Purity Rating"
        self._attr_unique_id = f"{device.serial}_purity_rating"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._device.purity_rating.name


class PowerSensor(SHCEntity, SensorEntity):
    """Representation of an SHC power reporting sensor."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = POWER_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC power reporting sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{device.name} Power"
        self._attr_unique_id = f"{device.serial}_power"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._device.powerconsumption


class EnergySensor(SHCEntity, SensorEntity):
    """Representation of an SHC energy reporting sensor."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = ENERGY_KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC energy reporting sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{self._device.name} Energy"
        self._attr_unique_id = f"{self._device.serial}_energy"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._device.energyconsumption / 1000.0


class ValveTappetSensor(SHCEntity, SensorEntity):
    """Representation of an SHC valve tappet reporting sensor."""

    _attr_icon = "mdi:gauge"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC valve tappet reporting sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{device.name} Valvetappet"
        self._attr_unique_id = f"{device.serial}_valvetappet"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._device.position

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "valve_tappet_state": self._device.valvestate.name,
        }

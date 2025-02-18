"""Platform for binarysensor integration."""
import asyncio
import logging
from datetime import datetime, timedelta
from .device import SHCDevice
from .models_impl import SHCBatteryDevice, SHCShutterContact, SHCSmokeDetectionSystem, SHCSmokeDetector, SHCWaterLeakageSensor
from .session import SHCSession

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import (
    ATTR_COMMAND,
    ATTR_DEVICE_ID,
    ATTR_ID,
    ATTR_NAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import EntityCategory

from .const import (
    ATTR_EVENT_SUBTYPE,
    ATTR_EVENT_TYPE,
    ATTR_LAST_TIME_TRIGGERED,
    DATA_SESSION,
    DOMAIN,
    EVENT_BOSCH_SHC,
    SERVICE_SMOKEDETECTOR_ALARMSTATE,
    SERVICE_SMOKEDETECTOR_CHECK,
)
from .entity import SHCEntity, async_get_device_id, migrate_old_unique_ids

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the SHC binary sensor platform."""
    entities = []
    session: SHCSession = hass.data[DOMAIN][config_entry.entry_id][DATA_SESSION]

    for binary_sensor in session.device_helper.shutter_contacts:
        entities.append(
            ShutterContactSensor(
                device=binary_sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )

    for binary_sensor in session.device_helper.motion_detectors:
        entities.append(
            MotionDetectionSensor(
                hass=hass,
                device=binary_sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )

    for binary_sensor in session.device_helper.smoke_detectors:
        entities.append(
            SmokeDetectorSensor(
                device=binary_sensor,
                parent_id=session.information.unique_id,
                hass=hass,
                entry_id=config_entry.entry_id,
            )
        )

    binary_sensor = session.device_helper.smoke_detection_system
    if binary_sensor:
        migrate_old_unique_ids(
            hass,
            Platform.BINARY_SENSOR,
            f"{binary_sensor.serial}",
            f"{binary_sensor.root_device_id}_{binary_sensor.serial}",
        )
        entities.append(
            SmokeDetectionSystemSensor(
                device=binary_sensor,
                parent_id=session.information.unique_id,
                hass=hass,
                entry_id=config_entry.entry_id,
            )
        )

    for binary_sensor in session.device_helper.water_leakage_detectors:
        entities.append(
            WaterLeakageDetectorSensor(
                device=binary_sensor,
                parent_id=session.information.unique_id,
                entry_id=config_entry.entry_id,
            )
        )

    for binary_sensor in (
        session.device_helper.motion_detectors
        + session.device_helper.shutter_contacts
        + session.device_helper.smoke_detectors
        + session.device_helper.thermostats
        + session.device_helper.twinguards
        + session.device_helper.universal_switches
        + session.device_helper.wallthermostats
        + session.device_helper.water_leakage_detectors
    ):
        if binary_sensor.supports_batterylevel:
            entities.append(
                BatterySensor(
                    device=binary_sensor,
                    parent_id=session.information.unique_id,
                    entry_id=config_entry.entry_id,
                )
            )

    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_SMOKEDETECTOR_CHECK,
        {},
        "async_request_smoketest",
    )
    platform.async_register_entity_service(
        SERVICE_SMOKEDETECTOR_ALARMSTATE,
        {
            vol.Required(ATTR_COMMAND): cv.string,
        },
        "async_request_alarmstate",
    )

    if entities:
        async_add_entities(entities)


class ShutterContactSensor(SHCEntity, BinarySensorEntity):
    """Representation of a SHC shutter contact sensor."""

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self._device.state == SHCShutterContact.ShutterContactService.State.OPEN

    @property
    def device_class(self):
        """Return the class of this device."""
        switcher = {
            "ENTRANCE_DOOR": BinarySensorDeviceClass.DOOR,
            "REGULAR_WINDOW": BinarySensorDeviceClass.WINDOW,
            "FRENCH_WINDOW": BinarySensorDeviceClass.DOOR,
            "GENERIC": BinarySensorDeviceClass.WINDOW,
        }
        return switcher.get(self._device.device_class, BinarySensorDeviceClass.WINDOW)


class MotionDetectionSensor(SHCEntity, BinarySensorEntity):
    """Representation of a SHC motion detection sensor."""

    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(self, hass, device, parent_id: str, entry_id: str):
        """Initialize the motion detection device."""
        self.hass = hass
        self._service = None
        super().__init__(device=device, parent_id=parent_id, entry_id=entry_id)

        for service in self._device.device_services:
            if service.id == "LatestMotion":
                self._service = service
                self._service.subscribe_callback(
                    self._device.id + "_eventlistener", self._async_input_events_handler
                )

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._handle_ha_stop)

    @callback
    def _async_input_events_handler(self):
        """Handle device input events."""
        self.hass.bus.async_fire(
            EVENT_BOSCH_SHC,
            {
                ATTR_DEVICE_ID: asyncio.run_coroutine_threadsafe(
                    async_get_device_id(self.hass, self._device.id), self.hass.loop
                ).result(),
                ATTR_ID: self._device.id,
                ATTR_NAME: self._device.name,
                ATTR_LAST_TIME_TRIGGERED: self._device.latestmotion,
                ATTR_EVENT_TYPE: "MOTION",
                ATTR_EVENT_SUBTYPE: "",
            },
        )

    @callback
    def _handle_ha_stop(self, _):
        """Handle Home Assistant stopping."""
        _LOGGER.debug(
            "Stopping motion detection event listener for %s", self._device.name
        )
        self._service.unsubscribe_callback(self._device.id + "_eventlistener")

    @property
    def is_on(self):
        """Return the state of the sensor."""
        try:
            latestmotion = datetime.strptime(
                self._device.latestmotion, "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        except ValueError:
            return False

        elapsed = datetime.utcnow() - latestmotion
        if elapsed > timedelta(seconds=4 * 60):
            return False
        return True

    @property
    def should_poll(self):
        """Retrieve motion state."""
        return True

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_motion_detected": self._device.latestmotion,
        }


class SmokeDetectorSensor(SHCEntity, BinarySensorEntity):
    """Representation of a SHC smoke detector sensor."""

    _attr_device_class = BinarySensorDeviceClass.SMOKE

    def __init__(
        self,
        device: SHCSmokeDetector,
        parent_id: str,
        hass: HomeAssistant,
        entry_id: str,
    ):
        """Initialize the smoke detector device."""
        self._hass = hass
        self._service = None
        super().__init__(device=device, parent_id=parent_id, entry_id=entry_id)

        for service in self._device.device_services:
            if service.id == "Alarm":
                self._service = service
                self._service.subscribe_callback(
                    self._device.id + "_eventlistener", self._async_input_events_handler
                )

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._handle_ha_stop)

    @callback
    def _async_input_events_handler(self):
        """Handle device input events."""
        self._hass.bus.async_fire(
            EVENT_BOSCH_SHC,
            {
                ATTR_DEVICE_ID: asyncio.run_coroutine_threadsafe(
                    async_get_device_id(self._hass, self._device.id), self._hass.loop
                ).result(),
                ATTR_ID: self._device.id,
                ATTR_NAME: self._device.name,
                ATTR_EVENT_TYPE: "ALARM",
                ATTR_EVENT_SUBTYPE: self._device.alarmstate.name,
            },
        )

    @callback
    def _handle_ha_stop(self, _):
        """Handle Home Assistant stopping."""
        _LOGGER.debug("Stopping alarm event listener for %s", self._device.name)
        self._service.unsubscribe_callback(self._device.id + "_eventlistener")

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self._device.alarmstate != SHCSmokeDetector.AlarmService.State.IDLE_OFF

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:smoke-detector"

    async def async_request_smoketest(self):
        """Request smokedetector test."""
        _LOGGER.debug("Requesting smoke test on entity %s", self.name)
        await self._hass.async_add_executor_job(self._device.smoketest_requested)

    async def async_request_alarmstate(self, command: str):
        """Request smokedetector alarm state."""

        def set_alarmstate(device, command):
            device.alarmstate = command

        _LOGGER.debug(
            "Requesting custom alarm state %s on entity %s", command, self.name
        )
        await self._hass.async_add_executor_job(set_alarmstate, self._device, command)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "smokedetectorcheck_state": self._device.smokedetectorcheck_state.name,
            "alarmstate": self._device.alarmstate.name,
        }


class WaterLeakageDetectorSensor(SHCEntity, BinarySensorEntity):
    """Representation of a SHC water leakage detector sensor."""

    _attr_device_class = BinarySensorDeviceClass.MOISTURE

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return (
            self._device.leakage_state
            != SHCWaterLeakageSensor.WaterLeakageSensorService.State.NO_LEAKAGE
        )

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:water-alert"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "push_notification_state": self._device.push_notification_state.name,
            "acoustic_signal_state": self._device.acoustic_signal_state.name,
        }


class SmokeDetectionSystemSensor(SHCEntity, BinarySensorEntity):
    """Representation of a SHC smoke detection system sensor."""

    _attr_device_class = BinarySensorDeviceClass.SMOKE

    def __init__(
        self,
        device: SHCSmokeDetectionSystem,
        parent_id: str,
        hass: HomeAssistant,
        entry_id: str,
    ):
        """Initialize the smoke detection system device."""
        self._hass = hass
        self._service = None
        super().__init__(device=device, parent_id=parent_id, entry_id=entry_id)
        self._attr_unique_id = f"{device.root_device_id}_{device.serial}"

        for service in self._device.device_services:
            if service.id == "SurveillanceAlarm":
                self._service = service
                self._service.subscribe_callback(
                    self._device.id + "_eventlistener", self._async_input_events_handler
                )

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._handle_ha_stop)

    @callback
    def _async_input_events_handler(self):
        """Handle device input events."""
        self._hass.bus.async_fire(
            EVENT_BOSCH_SHC,
            {
                ATTR_DEVICE_ID: asyncio.run_coroutine_threadsafe(
                    async_get_device_id(self._hass, self._device.id), self._hass.loop
                ).result(),
                ATTR_ID: self._device.id,
                ATTR_NAME: self._device.name,
                ATTR_EVENT_TYPE: "ALARM",
                ATTR_EVENT_SUBTYPE: self._device.alarm.name,
            },
        )

    @callback
    def _handle_ha_stop(self, _):
        """Handle Home Assistant stopping."""
        _LOGGER.debug("Stopping alarm event listener for %s", self._device.name)
        self._service.unsubscribe_callback(self._device.id + "_eventlistener")

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return (
            self._device.alarm
            != SHCSmokeDetectionSystem.SurveillanceAlarmService.State.ALARM_OFF
        )

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:smoke-detector"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "alarm_state": self._device.alarm.name,
        }


class BatterySensor(SHCEntity, BinarySensorEntity):
    """Representation of a SHC battery reporting sensor."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, device: SHCDevice, parent_id: str, entry_id: str) -> None:
        """Initialize an SHC temperature reporting sensor."""
        super().__init__(device, parent_id, entry_id)
        self._attr_name = f"{device.name} Battery"
        self._attr_unique_id = f"{device.serial}_battery"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        """Return the state of the sensor."""
        if (
            self._device.batterylevel
            == SHCBatteryDevice.BatteryLevelService.State.NOT_AVAILABLE
        ):
            _LOGGER.debug("Battery state of device %s is not available", self.name)

        if (
            self._device.batterylevel
            == SHCBatteryDevice.BatteryLevelService.State.CRITICAL_LOW
        ):
            _LOGGER.warning("Battery state of device %s is critical low", self.name)

        if (
            self._device.batterylevel
            == SHCBatteryDevice.BatteryLevelService.State.LOW_BATTERY
        ):
            _LOGGER.warning("Battery state of device %s is low", self.name)

        return (
            self._device.batterylevel != SHCBatteryDevice.BatteryLevelService.State.OK
        )

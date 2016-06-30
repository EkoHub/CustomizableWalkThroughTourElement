"""
Support for Vera devices.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/vera/
"""
import logging
from collections import defaultdict

from requests.exceptions import RequestException

from homeassistant.helpers import discovery
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.entity import Entity

REQUIREMENTS = ['pyvera==0.2.10']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'vera'

VERA_CONTROLLER = None

CONF_EXCLUDE = 'exclude'
CONF_LIGHTS = 'lights'

DEVICE_CATEGORIES = {
    'Sensor': 'binary_sensor',
    'Temperature Sensor': 'sensor',
    'Light Sensor': 'sensor',
    'Humidity Sensor': 'sensor',
    'Dimmable Switch': 'light',
    'Switch': 'switch',
    'Armable Sensor': 'switch',
    'On/Off Switch': 'switch',
    # 'Window Covering': NOT SUPPORTED YET
}

VERA_DEVICES = defaultdict(list)


# pylint: disable=unused-argument, too-many-function-args
def setup(hass, base_config):
    """Common setup for Vera devices."""
    global VERA_CONTROLLER
    import pyvera as veraApi

    config = base_config.get(DOMAIN)
    base_url = config.get('vera_controller_url')
    if not base_url:
        _LOGGER.error(
            "The required parameter 'vera_controller_url'"
            " was not found in config"
        )
        return False

    VERA_CONTROLLER, _ = veraApi.init_controller(base_url)

    def stop_subscription(event):
        """Shutdown Vera subscriptions and subscription thread on exit."""
        _LOGGER.info("Shutting down subscriptions.")
        VERA_CONTROLLER.stop()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_subscription)

    try:
        all_devices = VERA_CONTROLLER.get_devices(
            list(DEVICE_CATEGORIES.keys()))
    except RequestException:
        # There was a network related error connecting to the vera controller.
        _LOGGER.exception("Error communicating with Vera API")
        return False

    exclude = config.get(CONF_EXCLUDE, [])
    if not isinstance(exclude, list):
        _LOGGER.error("'exclude' must be a list of device_ids")
        return False

    lights_ids = config.get(CONF_LIGHTS, [])
    if not isinstance(lights_ids, list):
        _LOGGER.error("'lights' must be a list of device_ids")
        return False

    for device in all_devices:
        if device.device_id in exclude:
            continue
        dev_type = DEVICE_CATEGORIES.get(device.category)
        if dev_type is None:
            continue
        if dev_type == 'switch' and device.device_id in lights_ids:
            dev_type = 'light'
        VERA_DEVICES[dev_type].append(device)

    for component in 'binary_sensor', 'sensor', 'light', 'switch':
        discovery.load_platform(hass, component, DOMAIN, {}, base_config)

    return True


class VeraDevice(Entity):
    """Representation of a Vera devicetity."""

    def __init__(self, vera_device, controller):
        """Initialize the device."""
        self.vera_device = vera_device
        self.controller = controller
        self._name = self.vera_device.name

        self.controller.register(vera_device, self._update_callback)
        self.update()

    def _update_callback(self, _device):
        self.update_ha_state(True)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed."""
        return False

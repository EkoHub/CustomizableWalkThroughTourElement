"""
A component which allows you to send data to Dweet.io.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/dweet/
"""
import logging
from datetime import timedelta
import voluptuous as vol

from homeassistant.const import EVENT_STATE_CHANGED, STATE_UNKNOWN
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import state as state_helper
from homeassistant.util import Throttle


_LOGGER = logging.getLogger(__name__)

DOMAIN = "dweet"
DEPENDENCIES = []

REQUIREMENTS = ['dweepy==0.2.0']

CONF_NAME = 'name'
CONF_WHITELIST = 'whitelist'

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=1)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_WHITELIST): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


# pylint: disable=too-many-locals
def setup(hass, config):
    """Setup the Dweet.io component."""
    conf = config[DOMAIN]
    name = conf[CONF_NAME]
    whitelist = conf.get(CONF_WHITELIST, [])
    json_body = {}

    def dweet_event_listener(event):
        """Listen for new messages on the bus and sends them to Dweet.io."""
        state = event.data.get('new_state')
        if state is None or state.state in (STATE_UNKNOWN, '') \
                or state.entity_id not in whitelist:
            return

        try:
            _state = state_helper.state_as_number(state)
        except ValueError:
            _state = state.state

        json_body[state.attributes.get('friendly_name')] = _state

        send_data(name, json_body)

    hass.bus.listen(EVENT_STATE_CHANGED, dweet_event_listener)

    return True


@Throttle(MIN_TIME_BETWEEN_UPDATES)
def send_data(name, msg):
    """Send the collected data to Dweet.io."""
    import dweepy
    try:
        dweepy.dweet_for(name, msg)
    except dweepy.DweepyError:
        _LOGGER.error("Error saving data '%s' to Dweet.io", msg)

"""
Offer template automation rules.

For more details about this automation rule, please refer to the documentation
at https://home-assistant.io/components/automation/#template-trigger
"""
import logging

import voluptuous as vol

from homeassistant.const import (
    CONF_VALUE_TEMPLATE, CONF_PLATFORM, MATCH_ALL)
from homeassistant.helpers import condition
from homeassistant.helpers.event import track_state_change
import homeassistant.helpers.config_validation as cv


_LOGGER = logging.getLogger(__name__)

TRIGGER_SCHEMA = IF_ACTION_SCHEMA = vol.Schema({
    vol.Required(CONF_PLATFORM): 'template',
    vol.Required(CONF_VALUE_TEMPLATE): cv.template,
})


def trigger(hass, config, action):
    """Listen for state changes based on configuration."""
    value_template = config.get(CONF_VALUE_TEMPLATE)

    # Local variable to keep track of if the action has already been triggered
    already_triggered = False

    def state_changed_listener(entity_id, from_s, to_s):
        """Listen for state changes and calls action."""
        nonlocal already_triggered
        template_result = condition.template(hass, value_template)

        # Check to see if template returns true
        if template_result and not already_triggered:
            already_triggered = True
            action({
                'trigger': {
                    'platform': 'template',
                    'entity_id': entity_id,
                    'from_state': from_s,
                    'to_state': to_s,
                },
            })
        elif not template_result:
            already_triggered = False

    track_state_change(hass, MATCH_ALL, state_changed_listener)
    return True

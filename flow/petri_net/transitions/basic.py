from base import TransitionBase
from flow.petri_net import lua

import flow.redisom as rom
import logging


LOG = logging.getLogger(__file__)


class BasicTransition(TransitionBase):
    _consume_tokens = rom.Script(lua.load('consume_tokens_basic'))

    def consume_tokens(self, enabler, color_descriptor, color_marking_key,
            group_marking_key):

        active_tokens_key = self.active_tokens_key(color_descriptor)
        state_key = self.state_key(color_descriptor)
        arcs_in_key = self.arcs_in.key
        enablers_key = self.enablers.key

        keys = [state_key, active_tokens_key, arcs_in_key, color_marking_key,
                group_marking_key, enablers_key]
        args = [enabler, color_descriptor.group.idx, color_descriptor.color]

        LOG.debug("Consume tokens: KEYS=%r, ARGS=%r", keys, args)
        rv = self._consume_tokens(keys=keys, args=args)
        LOG.debug("Consume tokens returned: %r", rv)

        return rv[0]

    def state_key(self, color_descriptor):
        return self.subkey("state", color_descriptor.color)

    def active_tokens_key(self, color_descriptor):
        return self.subkey("active_tokens", color_descriptor.color)
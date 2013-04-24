from abc import ABCMeta, abstractmethod, abstractproperty
from flow.protocol.exceptions import InvalidMessageException
from flow.util import stats
from flow.interfaces import IHandler
from twisted.internet import defer
import logging

LOG = logging.getLogger(__name__)

class Handler(IHandler):
    def __call__(self, encoded_message):
        try:
            deferred = self._handle_message(encoded_message)
        except InvalidMessageException:
            LOG.exception('Invalid message.  message = %s', encoded_message)
            deferred = defer.fail(None)
        except:
            LOG.exception('Unexpected error handling message. message = %s',
                    encoded_message)
            deferred = defer.fail(None)
        return deferred

    @abstractmethod
    def _handle_message(self, message):
        """
        Returns a deferred that will callback when the message has been
        completely handled, or will errback when the message cannot be
        handled.  This function may also raise an InvalidMessageException.
        """

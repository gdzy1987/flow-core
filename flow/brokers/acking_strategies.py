from flow.protocol import codec
from flow.protocol.exceptions import InvalidMessageException
from pika.spec import Basic

import collections
import blist
import logging

LOG = logging.getLogger(__name__)


class Immediate(object):
    def reset(self):
        self._largest_receive_tag = 0

    def register_broker(self, broker):
        self.broker = broker

    def on_channel_open(self, channel):
        pass

    def add_receive_tag(self, receive_tag):
        self._largest_receive_tag = receive_tag

    def add_publish_tag(self, receive_tag=None, publish_tag=None):
        pass

    def remove_publish_tag(self, publish_tag, multiple=False):
        pass

    def pop_ackable_receive_tags(self):
        return [self._largest_receive_tag], True


class PublisherConfirmation(object):
    def reset(self):
        LOG.debug('Restting PublisherConfirmation state.')
        self._ackable_receive_tags = blist.sortedlist()
        self._non_ackable_receive_tags = blist.sortedlist()
        self._unconfirmed_publish_tags = blist.sortedlist()

        self._publish_to_receive_map = {}
        self._receive_to_publish_set_map = collections.defaultdict(set)

    def register_broker(self, broker):
        self.broker = broker

    def on_channel_open(self, channel):
        LOG.debug('Enabling publisher confirms.')
        channel.confirm_delivery()
        channel.callbacks.add(channel.channel_number, Basic.Ack,
                self._on_publisher_confirm_ack, one_shot=False)
        channel.callbacks.add(channel.channel_number, Basic.Nack,
                self._on_publisher_confirm_nack, one_shot=False)

    def _on_publisher_confirm_ack(self, method_frame):
        publish_tag = method_frame.method.delivery_tag
        multiple = method_frame.method.multiple
        LOG.debug('Got publisher confirm for message (%d), multiple = %s',
                publish_tag, multiple)

        self.remove_publish_tag(publish_tag, multiple=multiple)
        self.broker.ack_if_able()

    def _on_publisher_confirm_nack(self, method_frame):
        LOG.critical('Got failed publisher confirm.  Killing broker.')
        self.broker.disconnect()


    def add_receive_tag(self, receive_tag):
        self._ackable_receive_tags.add(receive_tag)

    def add_publish_tag(self, receive_tag=None, publish_tag=None):
        if receive_tag in self._ackable_receive_tags:
            self._ackable_receive_tags.remove(receive_tag)
            self._non_ackable_receive_tags.add(receive_tag)

        self._receive_to_publish_set_map[receive_tag].add(publish_tag)
        self._publish_to_receive_map[publish_tag] = receive_tag
        self._unconfirmed_publish_tags.add(publish_tag)

    def remove_publish_tag(self, publish_tag, multiple=False):
        if multiple:
            max_index = self._unconfirmed_publish_tags.bisect(publish_tag)
            ready_tags = self._unconfirmed_publish_tags[:max_index]
            del self._unconfirmed_publish_tags[:max_index]

            LOG.debug('Multiple confirm for (%d) includes: %s',
                    publish_tag, ready_tags)

            for tag in ready_tags:
                self._remove_single_publish_tag(tag)
        else:
            LOG.debug('Single confirm for (%d)', publish_tag)
            self._unconfirmed_publish_tags.remove(publish_tag)
            self._remove_single_publish_tag(publish_tag)


    def _remove_single_publish_tag(self, publish_tag):
        receive_tag = self._publish_to_receive_map.pop(publish_tag)
        LOG.debug('Publish tag (%d) maps to receive tag (%d)',
                publish_tag, receive_tag)
        publish_tag_set = self._receive_to_publish_set_map[receive_tag]
        publish_tag_set.remove(publish_tag)

        if not publish_tag_set:
            del self._receive_to_publish_set_map[receive_tag]
            self._set_receive_tag_ready_to_ack(receive_tag)
            LOG.debug('Receive tag (%d) ready to ack', receive_tag)
        else:
            LOG.debug('Waiting for %d more publisher confirms '
                    'before acking received message (%d)',
                    len(publish_tag_set), receive_tag)

    def _set_receive_tag_ready_to_ack(self, receive_tag):
        self._non_ackable_receive_tags.remove(receive_tag)
        self._ackable_receive_tags.add(receive_tag)


    def pop_ackable_receive_tags(self):
        '''
        Returns 2 element tuple.
            First element is a sorted list of receive_tags to ack.
            Second element is whether the first (smallest) tag should be multiple-ack'd
        '''
        # Cases
        # -----
        # 1) There are no ackable tags:
        #   rv = ([], False)
        # 2) There are no unackable tags:
        #   rv = ([ackable_tags[-1]], True)
        # 3) There are unackable tags
        # OR 4) The ackable tags are all less than the smallest unackable tag
        #   rv = ([ackable_tags[-1]], True)
        # 5) All the ackable tags are greater than the smallest unackable tag
        # OR 6) The smallest unackable tag is in the middle of the ackable tags
        #   This is the complex case:
        #       first ackable tag is the largest one smaller than the
        #       smallest unackable tag, rest are just thrown in the list
        #       if there is more than one tag smaller than smallest
        #       unackable, second rv element = True

        ackable_tags = self._ackable_receive_tags
        LOG.debug('Effective ack size = %d', len(ackable_tags))

        if not ackable_tags:
            return [], False

        unackable_tags = self._non_ackable_receive_tags
        if (not unackable_tags) or (unackable_tags[0] > ackable_tags[-1]):
            LOG.debug('All ackable tags are smaller than smallest unackable tag')
            ready_tags = [ackable_tags[-1]]
            multiple = len(ackable_tags) > 1
        else:
            # We assume that a tag is never in both ackable and unackable lists
            index = ackable_tags.bisect(unackable_tags[0])
            LOG.debug('Smallest unackable tag (%d) would insert at index %d',
                    unackable_tags[0], index)
            ready_tags = []
            multiple = False
            if index:
                ready_tags.append(ackable_tags[index - 1])
                if index > 1:
                    multiple = True
            ready_tags.extend(ackable_tags[index:])

        self._ackable_receive_tags = blist.sortedlist()
        return ready_tags, multiple
import logging
import time

import tweepy

from .errors import ERROR_CODES
from .stream_config import StreamConfig
from .tasks import handle_tweet

logger = logging.getLogger(__name__)


class StreamManager():
    def __init__(self, auth, listener):
        # High chunk_size means lower latency but higher processing efficiency
        self.stream = tweepy.Stream(
            auth=auth, listener=listener, tweet_mode='extended',
            parser=tweepy.parsers.JSONParser())
        self.stream_config = StreamConfig()

    def start(self):
        config = self.stream_config.get_pooled_config()
        logger.info(
            'Starting to track for keywords %s in languages %s',
            config['keywords'], config['lang'])
        self.stream.filter(
            track=config['keywords'], languages=config['lang'],
            encoding='utf-8', stall_warnings=True)

    def stop(self):
        logger.info('Stopping stream...')
        try:
            self.stream.disconnect()
        except Exception:
            pass


class StreamListener(tweepy.StreamListener):
    """Handles data received from the stream."""
    def __init__(self, test_mode=False):
        super(StreamListener, self).__init__()
        self.rate_error_count = 0
        self.tweet_count = 0
        self.test_mode = test_mode

    def on_status(self, status):
        if (self.test_mode and self.tweet_count < 100) or not self.test_mode:
            handle_tweet(status._json)
            self.tweet_count += 1
            return True
        return False

    def on_error(self, status_code):
        if status_code in ERROR_CODES:
            logger.error(
                '%d Error. %s. %s',
                status_code,
                ERROR_CODES[status_code]['text'],
                ERROR_CODES[status_code]['description'])
            if status_code == 420:
                logger.info('Waiting for a bit...')
                self.rate_error_count += 1
                # wait at least 15min
                time.sleep(self.rate_error_count * 15 * 60)
        else:
            logger.error('Unknown %d Error.', status_code)
        return True  # To continue listening

    def on_timeout(self):
        logger.error('Stream listener has timed out.')
        return True  # To continue listening

    def on_connect(self):
        self.rate_error_count = 0  # Reset error count
        logger.info('Successfully connected to Twitter Streaming API.')

    def on_warning(self, notice):
        logger.warning(notice)

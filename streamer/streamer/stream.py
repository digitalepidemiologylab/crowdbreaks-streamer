import logging
import time
import json

from queue import Queue
from threading import Thread

import tweepy

from awstools.config import config_manager
from awstools.env import Env

from .utils.errors import ERROR_CODES
from .tasks import handle_tweet

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class StreamManager():
    def __init__(self, auth, listener):
        # High chunk_size means lower latency but higher processing efficiency
        self.stream = tweepy.Stream(
            auth=auth, listener=listener, tweet_mode='extended',
            parser=tweepy.parsers.JSONParser())

    def start(self):
        config = config_manager.filter_config
        logger.info(
            'Starting to track for keywords %s in languages %s.',
            config.keywords, config.lang)
        self.stream.filter(
            track=config.keywords, languages=config.lang,
            encoding='utf-8', stall_warnings=True, is_async=True)

    def stop(self):
        logger.info('Stopping stream.')
        self.stream.disconnect()


class StreamListener(tweepy.StreamListener):
    """Handles data received from the stream."""
    def __init__(self, q=Queue()):
        # Threads and queues are to avoid IncompleteRead error:
        # https://stackoverflow.com/a/48046123/4949133
        super().__init__()
        self.rate_error_count = 0
        self.q = q
        for _ in range(Env.NUM_WORKERS):
            thread = Thread(target=self.handle_status)
            thread.daemon = True
            thread.start()

    def on_status(self, status):
        # Put to the queue
        self.q.put(status)

    def handle_status(self):
        while True:
            status = self.q.get()
            try:
                handle_tweet(status._json, config_manager)
            except KeyError as exc:
                logger.error(
                    '%s: %s\n%s',
                    type(exc).__name__, str(exc), json.dumps(status._json))
                raise exc
            self.q.task_done()

    def on_error(self, status_code):
        if status_code in ERROR_CODES:
            logger.error(
                '%d Error. %s. %s',
                status_code,
                ERROR_CODES[status_code]['text'],
                ERROR_CODES[status_code]['description'])
            if status_code == 420:
                logger.info('Error 420. Waiting.')
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

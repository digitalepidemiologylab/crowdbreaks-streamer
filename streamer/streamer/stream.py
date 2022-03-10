import logging
import time
import json
import traceback

from queue import Queue
from threading import Thread

import tweepy

from awstools.config import config_manager

from .utils.errors import ERROR_CODES
from .tasks import handle_tweet
from .env import TwiEnv
from awstools.env import Env

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class StreamManager():
    def __init__(self):
        # High chunk_size means lower latency but higher processing efficiency
        self.stream = Stream(
            consumer_key=TwiEnv.CONSUMER_KEY,
            consumer_secret=TwiEnv.CONSUMER_SECRET,
            access_token=TwiEnv.OAUTH_TOKEN,
            access_token_secret=TwiEnv.OAUTH_TOKEN_SECRET)

    def stop(self):
        logger.info('Stopping stream.')
        self.stream.disconnect()


class StreamManagerFilter(StreamManager):
    def start(self):
        config = config_manager.filter_config
        logger.info(
            'Starting to track for keywords %s in languages %s.',
            config.keywords, config.lang)
        self.stream.filter(
            track=config.keywords, languages=config.lang,
            stall_warnings=True)


class StreamManagerCovid(StreamManager):
    def start(self):
        logger.info('Starting to stream from TCS.')
        self.stream.covid(int(TwiEnv.COVID_PARTITION))


class Stream(tweepy.Stream):
    """Handles data received from the stream."""
    def __init__(self, q=Queue(), *args, **kwargs):
        # Threads and queues are to avoid IncompleteRead error:
        # https://stackoverflow.com/a/48046123/4949133
        super().__init__(*args, **kwargs)
        self.rate_error_count = 0
        self.q = q
        for _ in range(4):
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
            except Exception as exc:
                logger.error(
                    '%s: %s. Traceback: %s', type(exc).__name__, str(exc),
                    '; '.join(traceback.format_tb(exc.__traceback__)))
            self.q.task_done()

    def on_request_error(self, status_code):
        if status_code in ERROR_CODES:
            logger.error(
                '%d Error. %s. %s',
                status_code,
                ERROR_CODES[status_code]['text'],
                ERROR_CODES[status_code]['description'])
            if status_code == 420:
                logger.error('Error 420. Waiting.')
                self.rate_error_count += 1
                # wait at least 15min
                time.sleep(self.rate_error_count * 15 * 60)
        else:
            logger.error('Unknown %d Error.', status_code)
        return True  # To continue listening

    def on_connect(self):
        self.rate_error_count = 0  # Reset error count
        logger.info('Successfully connected to Twitter Streaming API.')

import logging
import sys
import time
from http.client import IncompleteRead

from tweepy import OAuthHandler, TweepError
from urllib3.exceptions import ProtocolError

from .env import Env, TwiEnv
from .stream import StreamListener
from .stream import StreamManager
from .setup_logging import setup_logging

from .firehose import create_delivery_stream

logger = logging.getLogger(__name__)


def main():
    """Here we instantiate the stream manager, listener
    and connect to the Twitter streaming API.
    """
    # Setting things up
    auth = get_auth()
    listener = StreamListener()
    # Wait for a bit before connecting, in case container will be paused
    logger.debug('Streaming container is ready, waiting 10 s.')
    time.sleep(10)
    last_error_time = 0
    n_errors_last_hour = 0
    while True:
        logger.debug('Trying to connect to Twitter API.')
        stream = StreamManager(auth, listener)
        try:
            stream.start()
        except KeyboardInterrupt:
            sys.exit()
        except Exception as exc:
            logger.error(
                'Stream starting exception %s: %s.',
                type(exc).__name__, str(exc))
            try:
                stream.stop()
            except Exception as exc:
                logger.error(
                    'Stream stopping exception %s: %s.',
                    type(exc).__name__, str(exc))
            n_errors_last_hour = update_error_count(
                n_errors_last_hour, last_error_time)
            last_error_time = time.time()
        wait_some_time(n_errors_last_hour)
    logger.info('Shutting down...')


def update_error_count(n_errors, last_error_time):
    if (time.time() - last_error_time) < 3600:
        return n_errors + 1
    return 0   # Reset to zero


def wait_some_time(n_errors_last_hour):
    base_delay = 60
    if n_errors_last_hour == 0:
        time.sleep(base_delay)
    else:
        time.sleep(min(base_delay * n_errors_last_hour, 1800))  # Don't wait longer than 30 min


def get_auth():
    if TwiEnv.CONSUMER_KEY is None or TwiEnv.CONSUMER_SECRET is None or \
            TwiEnv.OAUTH_TOKEN is None or TwiEnv.OAUTH_TOKEN_SECRET is None:
        raise Exception('Twitter API keys needed for streaming to work.')
    auth = OAuthHandler(TwiEnv.CONSUMER_KEY, TwiEnv.CONSUMER_SECRET)
    auth.set_access_token(TwiEnv.OAUTH_TOKEN, TwiEnv.OAUTH_TOKEN_SECRET)
    return auth


if __name__ == '__main__':
    setup_logging()
    Env.STREAM_CONFIG_PATH
    main()

import logging
import sys
import time
from http.client import IncompleteRead

from tweepy import OAuthHandler, TweepError
from urllib3.exceptions import ProtocolError

from stream.config import Config
from stream.stream import StreamListener
from stream.stream import StreamManager

from stream.stream_config import StreamConfig

logger = logging.getLogger(__name__)


def main():
    """Here we instantiate the stream manager, listener and connect to the Twitter streaming API."""
    # Setting things up
    listener = StreamListener()
    auth = get_auth()
    # Wait for a bit before connecting, in case container will be paused
    logger.debug('Streaming container is ready, waiting 10 s')
    time.sleep(10)
    last_error_time = 0
    n_errors_last_hour = 0
    while True:
        logger.debug('Trying to connect to Twitter API')
        stream = StreamManager(auth, listener)
        try:
            stream.start()
        except KeyboardInterrupt:
            sys.exit()
        except IncompleteRead:
            # This error occurrs sometimes under high volume, simply reconnect
            stream.stop()
        except (TweepError, ConnectionError, ConnectionResetError, ProtocolError) as e:
            stream.stop()
            logger.error('%s', str(e))
            n_errors_last_hour = update_error_count(n_errors_last_hour, last_error_time)
            last_error_time = time.time()
        except Exception as e:
            stream.stop()
            logger.error('Stream exception %s: %s', type(e).__name__, str(e))
            n_errors_last_hour = update_error_count(n_errors_last_hour, last_error_time)
            last_error_time = time.time()
        wait_some_time(n_errors_last_hour)
    logger.info('Shutting down...')


def update_error_count(n_errors, last_error_time):
    if (time.time() - last_error_time) < 3600:
        return n_errors + 1
    return 0  # reset to zero


def wait_some_time(n_errors_last_hour):
    base_delay = 60
    if n_errors_last_hour == 0:
        time.sleep(base_delay)
    else:
        time.sleep(min(base_delay * n_errors_last_hour, 1800)) # don't wait longer than 30min


def get_auth():
    config = Config()
    if config.CONSUMER_KEY is None or config.CONSUMER_SECRET is None or config.OAUTH_TOKEN is None or config.OAUTH_TOKEN_SECRET is None:
        raise Exception('Twitter API keys needed for streaming to work.')
    auth = OAuthHandler(config.CONSUMER_KEY, config.CONSUMER_SECRET)
    auth.set_access_token(config.OAUTH_TOKEN, config.OAUTH_TOKEN_SECRET)
    return auth


if __name__ == '__main__':
    main()

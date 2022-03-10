import logging
import sys
import os
import time
import traceback

from awstools.env import KFEnv
from awstools.config import config_manager
from awstools.firehose import create_delivery_stream
from awstools.elasticsearch import create_index
from awstools.llambda import set_s3_triggers

from .env import TwiEnv
from .stream import StreamManagerFilter, StreamManagerCovid
from .setup_logging import setup_logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def run():
    """Here we instantiate the stream manager, listener
    and connect to the Twitter streaming API.
    """
    # Wait for a bit before connecting, in case container will be paused
    logger.debug('Streaming container is ready, waiting 10 s.')
    time.sleep(10)
    last_error_time = 0
    n_errors_last_hour = 0
    while True:
        logger.debug('Trying to connect to Twitter API.')
        stream = StreamManagerCovid() if TwiEnv.COVID_STREAM_NAME else StreamManagerFilter()
        try:
            stream.start()
        except KeyboardInterrupt:
            logger.info('Shutting down...')
            sys.exit()
        except Exception as exc:
            logger.error(
                'Stream starting exception %s: %s. Traceback: %s',
                type(exc).__name__, str(exc),
                '; '.join(traceback.format_tb(exc.__traceback__)))
            try:
                stream.stop()
            except Exception as exc:
                logger.error(
                'Stream stopping exception%s: %s. Traceback: %s',
                type(exc).__name__, str(exc),
                '; '.join(traceback.format_tb(exc.__traceback__)))
            n_errors_last_hour = update_error_count(
                n_errors_last_hour, last_error_time)
            last_error_time = time.time()
        wait_some_time(n_errors_last_hour)


def update_error_count(n_errors, last_error_time):
    if (time.time() - last_error_time) < 3600:
        return n_errors + 1
    return 0   # Reset to zero


def wait_some_time(n_errors_last_hour):
    base_delay = 60
    if n_errors_last_hour == 0:
        time.sleep(base_delay)
    else:
        # Don't wait longer than 30 min
        time.sleep(min(base_delay * n_errors_last_hour, 1800))


def main():
    setup_logging()
    logger.info(os.path.dirname(os.path.realpath(__file__)))
    logger.info(os.getcwd())

    # Create a delivery stream for unmanched tweets
    if KFEnv.UNMATCHED_STORE_S3 == 1:
        create_delivery_stream(
            KFEnv.UNMATCHED_STREAM_NAME,
            f'{KFEnv.UNMATCHED_STREAM_NAME}/')
    # Create delivery streams and ES indices for the listed projects
    for conf in config_manager.covid(TwiEnv.COVID_STREAM_NAME is not None):
        create_delivery_stream(
            conf.slug, f'{KFEnv.STORAGE_BUCKET_PREFIX}{conf.slug}/')
        create_index(conf.slug, conf.lang[0], only_new=True)
    # Set S3 triggers for the delivery streams if nonexistent
    s3_prefixes = ['tweets/project_{}' for conf in config_manager.covid(TwiEnv.COVID_STREAM_NAME is not None)]
    set_s3_triggers('s3-to-es', s3_prefixes)
    run()

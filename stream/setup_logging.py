import logging
import os
import time
from enum import Enum
from pathlib import Path

# from .env import Env


# class LogDirs(Enum):
#     LOGS = os.path.join(Env.PROJECT_ROOT, 'logs')

#     # Stream
#     STREAM = os.path.join(LOGS, 'stream')
#     STREAM_INFO = os.path.join(STREAM, 'all')
#     STREAM_WARN = os.path.join(STREAM, 'warnings')
#     STREAM_DEBUG = os.path.join(STREAM, 'debug')

#     # Tweets
#     TWEETS = os.path.join(LOGS, 'tweets')
#     UNMATCHED = os.path.join(TWEETS, 'unmatched')
#     MATCH_TEST = os.path.join(TWEETS, 'match_test')
#     KEY_ERRORS = os.path.join(TWEETS, 'key_errors')

#     @classmethod
#     def create_folders(cls):
#         for const in cls:
#             Path(const.value).mkdir(parents=True, exist_ok=True)


def setup_logging(
        # debug=False
):
    # LogDirs.create_folders()

    handlers = []

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    handlers.append(stream_handler)

    # In the ECS container, there's no need in file handlers
    # as the logs get streamed right into CloudWatch
    # info_file_handler = logging.FileHandler(os.path.join(
    #     LogDirs.STREAM_INFO.value, time.strftime("info_%Y%m%d_%H%M%S.log")))
    # info_file_handler.setLevel(logging.INFO)
    # handlers.append(info_file_handler)

    # warn_file_handler = logging.FileHandler(os.path.join(
    #     LogDirs.STREAM_WARN.value, time.strftime("warn_%Y%m%d_%H%M%S.log")))
    # warn_file_handler.setLevel(logging.WARN)
    # handlers.append(warn_file_handler)

    # if debug:
    #     debug_file_handler = logging.FileHandler(os.path.join(
    #         LogDirs.STREAM_DEBUG.value,
    #         time.strftime("debug_%Y%m%d_%H%M%S.log")))
    #     debug_file_handler.setLevel(logging.DEBUG)
    #     handlers.append(debug_file_handler)

    logging.basicConfig(
        format='[%(asctime)s %(levelname)-4.4s %(name)s] %(message)s',
        handlers=handlers)

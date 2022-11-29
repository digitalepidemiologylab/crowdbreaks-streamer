import json
import logging
import time
import traceback

from requests import Response

from tweepy import StreamingClient, StreamRule

from awstools.config import config_manager

from .utils.errors import ERROR_CODES
from .tasks_v2 import handle_response
from .env import TwiEnv

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


expansions = [
    'attachments.media_keys', 'geo.place_id', 'attachments.poll_ids',
    'referenced_tweets.id', 'author_id', 'entities.mentions.username',
    'in_reply_to_user_id', 'referenced_tweets.id.author_id'
]


media_fields = [
    'url', 'duration_ms', 'height', 'non_public_metrics', 'organic_metrics',
    'preview_image_url', 'promoted_metrics', 'public_metrics', 'width',
    'alt_text', 'variants'
]


place_fields = [
    'contained_within', 'country', 'country_code', 'geo', 'name', 'place_type'
]


poll_fields = ['duration_minutes', 'end_datetime', 'voting_status']


tweet_fields = [
    'attachments', 'author_id', 'context_annotations',
    'conversation_id', 'created_at', 'edit_controls', 'entities',
    'in_reply_to_user_id', 'lang', 'non_public_metrics', 'organic_metrics',
    'possibly_sensitive', 'promoted_metrics', 'public_metrics',
    'referenced_tweets', 'reply_settings', 'source', 'withheld'
]


user_fields = [
    'created_at', 'description', 'entities', 'location', 'pinned_tweet_id',
    'profile_image_url', 'protected', 'public_metrics', 'url', 'verified',
    'withheld'
]


class StreamManager():
    def __init__(self):
        self.stream = Stream(bearer_token=TwiEnv.BEARER_TOKEN)

    def start(self):
        raise NotImplementedError

    def stop(self):
        logger.info('Stopping stream.')
        self.stream.disconnect()


def create_rule(conf):
    rule_keywords = '(' + ' OR '.join(conf.keywords) + ')'
    rule_langs = ' '.join(map(lambda l: f'lang:{l}', conf.lang))
    return StreamRule(f'{rule_keywords} {rule_langs}', tag=conf.slug)


class StreamManagerFilter(StreamManager):
    def start(self):
        rules = []
        for conf in config_manager.config:
            logger.info(
                'Starting to track for keywords %s in languages %s.',
                conf.keywords, conf.lang)
            rules.append(create_rule(conf))
        self.stream.add_rules(rules)
        self.stream.filter(
            expansions=expansions,
            media_fields=media_fields,
            place_fields=place_fields,
            poll_fields=poll_fields,
            tweet_fields=tweet_fields,
            user_fields=user_fields,
            threaded=False
        )


class Stream(StreamingClient):
    def on_data(self, data):
        handle_response(data, config_manager)

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

import logging
import re
import json
from collections import defaultdict

from .stream_config import StreamConfig

logger = logging.getLogger(__name__)


class ReverseTweetMatcher():
    """Tries to reverse match a tweet object given a set of
    keyword lists and languages.
    """

    def __init__(self, tweet=None):
        self.is_retweet = self._is_retweet(tweet)
        self.tweet = self._get_tweet(tweet)
        self.stream_config_reader = StreamConfig()

    def match_projects(self):
        """Returns matching keywords for each project."""
        relevant_text = self.fetch_relevant_text()
        config = self.stream_config_reader.read()
        if len(config) == 0:
            return []
        else:
            return self._match_to_config_keywords(relevant_text, config)

    def fetch_relevant_text(self):
        """Here we pool all relevant text within the tweet to do the matching.
        From the Twitter docs:
        "Specifically, the text attribute of the Tweet,
        expanded_url and display_url for links and media, text for hashtags,
        and screen_name for user mentions are checked for matches."
        https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters.html
        """
        def fetch_from_status(status, text):
            if status['truncated']:
                text += status['extended_tweet']['full_text']
            else:
                text += status['text']
            text += self._fetch_user_mentions(status)
            text += self._fetch_urls(status)
            return text

        text = ''
        text = fetch_from_status(self.tweet, text)

        # Pool together with text from quoted tweet
        if 'quoted_status' in self.tweet:
            text = fetch_from_status(self.tweet['quoted_status'], text)

        return text.lower()

    def _is_retweet(self, tweet):
        return 'retweeted_status' in tweet

    def _get_tweet(self, tweet):
        if self.is_retweet:
            return tweet['retweeted_status']
        else:
            return tweet

    def _match_to_project_keywords(self, relevant_text, project):
        """Match project keywords with text."""
        # Filter by language setting
        if self.tweet['lang'] in project['lang'] or \
                len(project['lang']) == 0 or self.tweet['lang'] == 'und':
            matching_keywords = defaultdict(list)
            keywords = [kw.lower().split() for kw in project['keywords']]
            for keyword_list in keywords:
                if len(keyword_list) == 1:
                    if keyword_list[0] in relevant_text:
                        matching_keywords[project['slug']].append(
                            keyword_list[0])
                else:
                    # Keywords with more than one word:
                    # Check if all words are contained in text
                    match_result = re.findall(
                        r'{}'.format('|'.join(keyword_list)), relevant_text)
                    if set(match_result) == set(keyword_list):
                        matching_keywords[project['slug']].extend(keyword_list)
            return matching_keywords
        else:
            return {}

    def _match_to_config_keywords(self, relevant_text, config):
        """For each project in config, match project keywords with text."""
        matching_keywords = defaultdict(list)
        for project in config:
            matching_keywords = {
                **matching_keywords,
                **self._match_to_project_keywords(relevant_text, project)}
        return matching_keywords

    def _fetch_urls(self, obj):
        text = []
        if 'urls' in obj['entities']:
            for url in obj['entities']['urls']:
                text.append(url['expanded_url'])

        if 'extended_entities' in obj:
            if 'media' in obj['extended_entities']:
                for medium in obj['extended_entities']['media']:
                    text.append(medium['expanded_url'])
        return ''.join(text)

    def _fetch_user_mentions(self, obj):
        text = []
        if 'user_mentions' in obj['entities']:
            for user_mention in obj['entities']['user_mentions']:
                text.append(user_mention['screen_name'])
        return ''.join(text)

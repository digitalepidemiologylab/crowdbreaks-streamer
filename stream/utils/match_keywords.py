"""
Tries to reverse match a status statusect given a set of
keyword lists and languages.
"""

import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


def match_keywords(status, config):
    """Returns matching keywords for each project."""
    relevant_text = fetch_relevant_text(status)
    return _match_to_config(status, relevant_text, config)


def fetch_relevant_text(status):
    """Here we pool all relevant text within the status to do the matching.
    From the Twitter docs:
    "Specifically, the text attribute of the Tweet,
    expanded_url and display_url for links and media, text for hashtags,
    and screen_name for user mentions are checked for matches."
    https://developer.twitter.com/en/docs/statuss/filter-realtime/guides/basic-stream-parameters.html
    """
    def fetch_from_status(status, text):
        if status['truncated']:
            text += status['extended_status']['full_text']
        else:
            text += status['text']
        text += _fetch_user_mentions(status)
        text += _fetch_urls(status)
        return text

    if 'retweeted_status' in status:
        status = status['retweeted_status']

    text = ''
    text = fetch_from_status(status, text)

    # Pool together with text from quoted status
    if 'quoted_status' in status:
        text = fetch_from_status(status['quoted_status'], text)

    return text.lower()


def _fetch_user_mentions(status):
    text = []
    if 'user_mentions' in status['entities']:
        for user_mention in status['entities']['user_mentions']:
            text.append(user_mention['screen_name'])
    return ''.join(text)


def _fetch_urls(status):
    text = []
    if 'urls' in status['entities']:
        for url in status['entities']['urls']:
            text.append(url['expanded_url'])

    if 'extended_entities' in status:
        if 'media' in status['extended_entities']:
            for medium in status['extended_entities']['media']:
                text.append(medium['expanded_url'])
    return ''.join(text)


def _match_to_config(status, relevant_text, config):
    """For each project in config, match project keywords with text."""
    matching_keywords = defaultdict(list)
    for conf in config:
        matching_keywords = {
            **matching_keywords,
            **_match_to_conf_keywords(status, relevant_text, conf)}
    return matching_keywords


def _match_to_conf_keywords(status, relevant_text, conf):
    """Match project keywords with text."""
    # Filter by language setting
    if status['lang'] in conf.lang or \
            len(conf.lang) == 0 or status['lang'] == 'und':
        matching_keywords = defaultdict(list)
        keywords = [kw.lower().split() for kw in conf.keywords]
        for keyword_list in keywords:
            if len(keyword_list) == 1:
                if keyword_list[0] in relevant_text:
                    matching_keywords[conf.slug].append(
                        keyword_list[0])
            else:
                # Keywords with more than one word:
                # Check if all words are contained in text
                match_result = re.findall(
                    r'{}'.format('|'.join(keyword_list)), relevant_text)
                if set(match_result) == set(keyword_list):
                    matching_keywords[conf.slug].extend(keyword_list)
        return matching_keywords
    else:
        return {}

"""
Tries to reverse match a status statusect given a set of
keyword lists and languages.
"""

import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def match_keywords(tweet, config):
    """For each project in config, match project keywords with text."""
    matching_keywords = defaultdict(list)
    for conf in config:
        matching_keywords = {
            **matching_keywords,
            **_match_to_conf_keywords(tweet, conf)}
    return matching_keywords


def _match_to_conf_keywords(tweet, conf):
    """Match project keywords with text."""
    # Filter by language setting
    if tweet.lang in conf.lang or \
            len(conf.lang) == 0 or tweet.lang == 'und':
        matching_keywords = defaultdict(list)
        keywords = [kw.lower().split() for kw in conf.keywords]
        for keyword_list in keywords:
            if len(keyword_list) == 1:
                if keyword_list[0] in tweet.keyword_matching_text:
                    matching_keywords[conf.slug].append(
                        keyword_list[0])
            else:
                # Keywords with more than one word:
                # Check if all words are contained in text
                match_result = re.findall(
                    r'{}'.format(
                        '|'.join(keyword_list)), tweet.keyword_matching_text)
                if set(match_result) == set(keyword_list):
                    matching_keywords[conf.slug].append(
                        ' '.join(keyword_list))
        return matching_keywords
    else:
        return {}

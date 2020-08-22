"""
Generates random tweets
=======================
"""

import argparse
import random
import json
from datetime import datetime
from faker import Faker
from faker.providers import profile, date_time, lorem

tweet_example = {  
    "created_at": "Thu May 10 15:24:15 +0000 2018",
    "id_str": "850006245121695744",
    "text": "Here is the Tweet message.",
    "user": {
        "id": 2244994945,
        "name": "Twitter Dev",
        "screen_name": "TwitterDev",
        "description": "User description"
    },
    "place": {
    },
    "entities": {
    },
    "extended_entities": {
    }
}

parser = argparse.ArgumentParser()

parser.add_argument(
    '--n-tweets', type=int, default=10,
    help='number of tweets to generate')
parser.add_argument(
    '--keywords', type=str, default=None, nargs='+',
    help='keywords that need to be in the generated text')

args = parser.parse_args()

fake = Faker()
fake.add_provider(profile)
fake.add_provider(date_time)
fake.add_provider(lorem)

with open(datetime.now().strftime('%Y-%m-%d_%H-%M-%S.txt'), 'w') as f:
    for i in range(0, args.n_tweets):
        profile = fake.profile()

        text = fake.sentence(nb_words=10)
        for j in range(random.randint(0, 4)):
            text += ' ' + fake.sentence(nb_words=10)
        text = text.split(' ')

        n_tags = random.randint(0, 4)
        n_keywords = random.randint(0, 4)

        for tag_i in random.sample(range(0, len(text)), n_tags):
            text[tag_i] = '#' + text[tag_i]

        if args.keywords is not None:
            for k_i in random.sample(range(0, len(text)), n_keywords):
                text[k_i] = random.sample(args.keywords, n_keywords) + ' ' + text[k_i]

        text = ' '.join(text)

        tweet = {
            "created_at": fake.date_between().ctime(),
            "id_str": str(random.randint(10**18, 10**19)),
            "text": text,
            "user": {
                "name": profile['name'],
                "screen_name": profile['username'],
                "description": fake.sentence(10)
            }
        }
        json.dump(tweet, f, separators=(',', ':'))
        f.write('\n')

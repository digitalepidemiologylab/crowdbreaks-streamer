from awstools.config import config_manager
from awstools.elasticsearch import create_index


def handler(event, context):
    for conf in config_manager.config:
        create_index(conf.slug, conf.lang[0])

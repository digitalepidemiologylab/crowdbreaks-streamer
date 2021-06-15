import logging
import json

from enum import Enum
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, asdict, field

import dacite
from .s3 import get_s3_object, s3
from .env import AWSEnv

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class StorageMode(Enum):
    S3 = 1
    S3_ES = 2
    S3_NO_RETWEETS = 3
    S3_ES_NO_RETWEETS = 4
    TEST_MODE = 5


class ImageStorageMode(Enum):
    ACTIVE = 1
    INACTIVE = 2


converter = {
    StorageMode: lambda x: StorageMode[x.upper().replace('-', '_')],
    ImageStorageMode: lambda x: ImageStorageMode[x.upper().replace('-', '_')],
}


@dataclass(frozen=True)
class Conf:
    keywords: List[str]
    lang: List[str]
    locales: List[str]
    slug: str
    storage_mode: StorageMode
    image_storage_mode: ImageStorageMode
    model_endpoints: Optional[Dict]


@dataclass(frozen=True)
class FilterConf:
    keywords: Set[str] = field(default_factory=set)
    lang: Set[str] = field(default_factory=set)


class ConfigManager():
    """Read, write and validate project configs."""
    def __init__(self, s3_client=s3, version_id=None):
        self.dict, self.config = self._load(s3_client, version_id)
        self.filter_config = self._pool_config()

    def get_conf_by_slug(self, slug):
        for conf in self.config:
            if conf.slug == slug:
                return conf

    def get_tracking_info(self, slug):
        """Adds tracking info to all tweets before pushing to S3."""
        for conf in self.config:
            if conf.slug == slug:
                info = {
                    key: getattr(conf, key)
                    for key in ['lang', 'keywords', 'slug']}
                return info

    def write(self):
        return json.dumps([conf for conf in self.dict], indent=4)

    def _load(self, s3_client, version_id):
        raw = json.loads(get_s3_object(
            AWSEnv.BUCKET_NAME, AWSEnv.STREAM_CONFIG_S3_KEY,
            s3_client, version_id))
        # Sort raw by slug
        raw = sorted(raw, key=lambda conf: conf['slug'])
        # What is this even???
        # latest_version = max([int(key.replace('_', '')) for key in raw])
        # raw = raw['_' + str(latest_version)]
        config = []
        for conf in raw:
            config.append(dacite.from_dict(
                data_class=Conf, data=conf,
                config=dacite.Config(type_hooks=converter)))
        return raw, config

    def _pool_config(self):
        """Pools all filtering configs to run everything in a single stream."""
        filter_conf = FilterConf()
        for conf in self.config:
            filter_conf.keywords.update(conf.keywords)
            filter_conf.lang.update(conf.lang)
        return filter_conf


config_manager = ConfigManager()

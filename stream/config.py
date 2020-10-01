import logging
import os
import json

from enum import Enum
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, asdict, field

import dacite

from .env import Env

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class StorageMode(Enum):
    TEST_MODE = 1
    S3_ES = 2
    S3_ES_NO_RETWEETS = 3


class ImageStorageMode(Enum):
    ACTIVE = 1
    INACTIVE = 2


converter = {
    StorageMode: lambda x: StorageMode[x],
    ImageStorageMode: lambda x: ImageStorageMode[x],
}


@dataclass(frozen=True)
class Conf:
    keywords: List[str]
    lang: List[str]
    locales: List[str]
    slug: str
    storage_mode: StorageMode
    image_storage_mode: ImageStorageMode
    model_endpoints: Optional[Dict[str, str]]


@dataclass(frozen=True)
class FilterConf:
    keywords: Set[str] = field(default_factory=set)
    lang: Set[str] = field(default_factory=set)


class ConfigManager():
    """Read, write and validate project configs."""
    def __init__(self, config=None):
        self.config_path = os.path.join(
            Env.CONFIG_PATH, Env.STREAM_CONFIG_PATH)
        self.config = self._load() if config is None else self._load(config)
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
        with open(self.config_path, 'w') as f:
            json.dump([asdict(conf) for conf in self.config], f, indent=4)

    def _load(self, raw=None):
        if raw is None:
            with open(self.config_path, 'r') as f:
                raw = json.load(f)
        config = []
        for conf in raw:
            config.append(dacite.from_dict(
                data_class=Conf, data=conf,
                config=dacite.Config(type_hooks=converter)))
        return config

    def _pool_config(self):
        """Pools all filtering configs to run everything in a single stream."""
        filter_conf = FilterConf()
        for conf in self.config:
            filter_conf.keywords.update(conf.keywords)
            filter_conf.lang.update(conf.lang)
        return filter_conf

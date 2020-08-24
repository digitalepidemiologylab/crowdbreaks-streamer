import logging
import os
import json

from .config import Conf

logger = logging.getLogger(__name__)

# Why always pass the config around? Why not just have it as an attribute?


class StreamConfig():
    """Read, write and validate project configs."""

    def __init__(self, config=None):
        self.config_path = os.path.join(
            Conf.CONFIG_PATH, Conf.STREAM_CONFIG_FILENAME)
        self.required_keys = [
            'keywords', 'es_index_name', 'lang', 'locales', 'slug',
            'storage_mode', 'image_storage_mode', 'model_endpoints',
            'compile_trending_tweets', 'compile_trending_topics',
            'compile_data_dump_ids']
        self.required_types = {
            'keywords': list,
            'lang': list,
            'es_index_name': str,
            'storage_mode': str,
            'image_storage_mode': str,
            'slug': str,
            'model_endpoints': dict,
            'locales': list,
            'compile_trending_tweets': bool,
            'compile_trending_topics': bool,
            'compile_data_dump_ids': bool}
        if config is None:
            config = self.load(self.config_path)
        self._validate(config)
        # Any keywords other than required will be ignored
        self.config = self._extract_required_config(config)

    def get_conf_by_index_name(self, es_index_name):
        for conf in self.config:
            if conf['es_index_name'] == es_index_name:
                return conf

    def get_conf_by_slug(self, slug):
        for conf in self.config:
            if conf['slug'] == slug:
                return conf

    def get_es_index_names(self):
        return [d['es_index_name'] for d in self.config]

    def get_pooled_config(self):
        """Pools all filtering configs to run everything in a single stream."""
        filter_conf = {'keywords': set(), 'lang': set()}
        for stream in self.config:
            filter_conf['keywords'].update(stream['keywords'])
            filter_conf['lang'].update(stream['lang'])
        return filter_conf

    def get_tracking_info(self, slug):
        """Adds tracking info to all tweets before pushing into S3."""
        for conf in self.config:
            if conf['slug'] == slug:
                info = {
                    key: conf[key]
                    for key in ['lang', 'keywords', 'es_index_name']}
                return info

    def load(self, config_path):
        self._check_file_exists()
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config

    def write(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def _check_empty_or_none(self, config):
        if config is None:
            raise ValueError('Config is None.')
        if len(config) == 0:
            raise ValueError('Config contains no streams.')

    def _check_file_exists(self):
        if not os.path.isfile(self.config_path):
            raise ValueError('Config file does not exist.')

    def _check_required_keys(self, conf):
        """Tests if all required keys are present."""
        for k in self.required_keys:
            if k not in conf:
                raise ValueError(
                    "One or more of the following keywords are not "
                    f"present in the sent config: {self.required_keys}.")

    def _check_required_types(self, conf):
        for key, data_type in self.required_types.items():
            if not isinstance(conf[key], data_type):
                raise TypeError(
                    f"Config:\n{conf}.\n"
                    "One or more of the values is of the wrong type. "
                    f"The required types are: {self.required_types}.")

    def _extract_required_config(self, config):
        required_config = []
        for conf in config:
            req_conf = {}
            for k in self.required_keys:
                req_conf[k] = conf[k]
            required_config.append(req_conf)
        return required_config

    def _validate(self, config):
        self._check_empty_or_none(config)
        for conf in config:
            self._check_required_keys(conf)
            self._check_required_types(conf)

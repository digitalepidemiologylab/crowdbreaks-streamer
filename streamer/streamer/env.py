"""Application configuration."""
import os
from pathlib import Path
from aenum import Constant
from dotenv import load_dotenv

env_path = os.path.join(Path(__file__).parent.absolute(), 'streamer.env')
load_dotenv(dotenv_path=env_path)


class TwiEnv(Constant):
    """Twitter API config."""
    CONSUMER_KEY = os.environ.get('TWI_CONSUMER_KEY')
    CONSUMER_SECRET = os.environ.get('TWI_CONSUMER_SECRET')
    OAUTH_TOKEN = os.environ.get('TWI_OAUTH_TOKEN')
    OAUTH_TOKEN_SECRET = os.environ.get('TWI_OAUTH_TOKEN_SECRET')

    COVID_STREAM_NAME = os.environ.get('COVID_STREAM_NAME', None)
    COVID_PARTITION = os.environ.get('COVID_PARTITION', '0')
    assert COVID_PARTITION in ['0', '1', '2', '3', '4']

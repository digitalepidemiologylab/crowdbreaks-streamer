"""Application configuration."""
import os
from aenum import Constant
from dotenv import load_dotenv

load_dotenv()


class TwiEnv(Constant):
    """Twitter API config."""
    CONSUMER_KEY = os.environ.get('TWI_CONSUMER_KEY')
    CONSUMER_SECRET = os.environ.get('TWI_CONSUMER_SECRET')
    OAUTH_TOKEN = os.environ.get('TWI_OAUTH_TOKEN')
    OAUTH_TOKEN_SECRET = os.environ.get('TWI_OAUTH_TOKEN_SECRET')

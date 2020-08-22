import logging
import time

logging.basicConfig(
    format='[%(asctime)s %(levelname)-4.4s %(name)s] %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(time.strftime("logs/logging/%Y%m%d_%H%M%S.log")),
        logging.StreamHandler()
    ])

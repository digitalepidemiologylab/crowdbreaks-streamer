import os
import logging

from awstools.llambda import (create_s3_to_es_lambda,
                              create_lambda_layer,
                              zip_lambda_func,
                              zip_lambda_layer)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main():
    print('blabla')
    logger.info(os.path.dirname(os.path.realpath(__file__)))
    logger.info(os.getcwd())
    zip_lambda_func()
    zip_lambda_layer()
    create_lambda_layer(push_layer=True, create_layer=False)
    create_s3_to_es_lambda(push_func=True)

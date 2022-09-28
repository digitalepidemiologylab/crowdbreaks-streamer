import os
import logging

from awstools.llambda import (create_lambda,
                              create_lambda_layer,
                              zip_lambda_func,
                              zip_lambda_layer)
from awstools.env import SagemakerTrainEnv as Env

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main():
    lambda_name = 'moob-training-job'
    lambda_dir = os.path.dirname(os.path.realpath(__file__))

    policy_path = os.path.join(
        lambda_dir, 'function/config/lambda_policy.json')

    lambda_local_zip_path = zip_lambda_func(lambda_dir)
    layer_local_zip_path = zip_lambda_layer(lambda_dir)

    create_lambda_layer(
        lambda_name,
        layer_local_zip_path,
        push_to_s3=True
    )

    more_env_vars = {
        'BUCKET_NAME': Env.BUCKET_NAME,
        'HYPERPARAMS_S3_KEY': Env.HYPERPARAMS_S3_KEY,
        'ECREPO_NAME': Env.ECREPO_NAME,
        'INSTANCE_TYPE': Env.INSTANCE_TYPE,
        'OUTPUT_PREFIX': Env.OUTPUT_PREFIX
    }
    create_lambda(
        lambda_name,
        lambda_local_zip_path,
        policy_path,
        push_to_s3=True,
        more_env_vars=more_env_vars
    )


if __name__ == "__main__":
    main()

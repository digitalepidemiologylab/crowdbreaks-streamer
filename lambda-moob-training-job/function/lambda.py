import json
import logging

import sagemaker
from sagemaker.estimator import Estimator

from awstools.env import SagemakerTrainEnv as Env
from awstools.s3 import get_long_s3_object

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_model_uri():
    return


def get_hyperparams():
    return json.loads(get_long_s3_object(
        Env.BUCKET_NAME, Env.HYPERPARAMS_S3_KEY,
        {'CompressionType': 'NONE', 'JSON': {'Type': 'DOCUMENT'}}))


def run(stream_uri):
    role = sagemaker.get_execution_role()

    moob_est = Estimator(
        image_uri=f'{Env.ACCOUNT_NUM}.dkr.ecr.{Env.REGION}.amazonaws.com/'
                f'{Env.ECREPO_NAME}:latest',
        role=role,
        instance_count=1,
        instance_type=Env.INSTANCE_TYPE,
        output_path=Env.OUTPUT_PREFIX,
        base_job_name=Env.ECREPO_NAME,
        tags=[{
            "Key": "project",
            "Value": "crowdbreaks"
        }]
    )
    hyperparams = get_hyperparams()
    moob_est.set_hyperparameters(hyperparams)

    model_uri = get_model_uri()
    stream_config = sagemaker.TrainingInput(stream_uri, content_type='text/csv')
    fit_params = {'stream': stream_config}
    if model_uri is not None:
        fit_params['model'] = sagemaker.TrainingInput(model_uri)
    moob_est.fit(fit_params, wait=False)


def handler(event, context):
    logger.debug(event)

    # A new input file is uploaded once per month, so no reason for
    # a lot of records (a lot of files in a short period)
    assert len(event['Records']) == 1

    stream_uri = event['Records'][-1]['s3']['object']['key']

    run(stream_uri)

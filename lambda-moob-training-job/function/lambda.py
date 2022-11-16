import json
import logging

import sagemaker
from sagemaker.estimator import Estimator

from awstools.session import ecr
from awstools.env import SMAEnv
from awstools.s3 import get_long_s3_object

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_model_uri():
    return


def get_image_uri():
    jmespath_expression = 'sort_by(imageDetails, &to_string(imagePushedAt))[-1].imageTags'
    paginator = ecr.get_paginator('describe_images')
    iterator = paginator.paginate(repositoryName=SMAEnv.ECREPO_NAME)
    filter_iterator = iterator.search(jmespath_expression)
    latest_tag =  list(filter_iterator)[0]

    return f'{SMAEnv.ACCOUNT_NUM}.dkr.ecr.{SMAEnv.REGION}.amazonaws.com/' \
           f'{SMAEnv.ECREPO_NAME}:{latest_tag}'


def get_hyperparams():
    return json.loads(get_long_s3_object(
        SMAEnv.BUCKET_NAME, SMAEnv.HYPERPARAMS_S3_KEY,
        {'CompressionType': 'NONE', 'JSON': {'Type': 'DOCUMENT'}}))


def run(stream_uri):
    moob_est = Estimator(
        image_uri=get_image_uri(),
        role=SMAEnv.SAGEMAKER_ROLE,
        instance_count=1,
        instance_type=SMAEnv.INSTANCE_TYPE,
        output_path=SMAEnv.OUTPUT_PREFIX,
        base_job_name=SMAEnv.JOB_NAME,
        tags=[{
            "Key": "project",
            "Value": "crowdbreaks"
        }]
    )
    hyperparams = get_hyperparams()
    moob_est.set_hyperparameters(**hyperparams)

    model_uri = get_model_uri()
    stream_config = sagemaker.TrainingInput(stream_uri, content_type='text/csv')
    fit_params = {'stream': stream_config}
    if model_uri is not None:
        fit_params['model'] = sagemaker.TrainingInput(model_uri)
    moob_est.fit(fit_params, wait=False)

    job_name = moob_est._current_job_name
    


def handler(event, context):
    logger.debug(event)

    # A new input file is uploaded once per month, so no reason for
    # a lot of records (a lot of files in a short period)
    assert len(event['Records']) == 1

    record = event['Records'][-1]
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']

    stream_uri = f's3://{bucket}/{key}'

    run(stream_uri)

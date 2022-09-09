from pathlib import Path
from aenum import Constant


class Env(Constant):
    hyperparams_path = Path('/opt/ml/input/config/hyperparams.json')
    inputdataconfig_path = Path('/opt/ml/input/config/inputdataconfig.json')
    resource_path = Path('/opt/ml/input/config/resourceconfig.json')
    data_dir = Path('/opt/ml/input/data/')
    embeddings_path = data_dir.joinpath('embeddings_with_labels_full_stream.csv')
    failure_path = Path('/opt/ml/output/failure')
    model_artifacts_dir = Path('/opt/ml/model/')

    training_job_name_env = 'TRAINING_JOB_NAME'
    training_job_arn_env = 'TRAINING_JOB_ARN'

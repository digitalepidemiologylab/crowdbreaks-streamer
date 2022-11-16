import io
import json
from pathlib import Path

from joblib import load
import pandas as pd

from .env import Env
from .helpers import load_hyperparams
from .process import input_data_to_embeddings


def model_fn(model_dir):
    model_dir = Path(model_dir)
    hyperparams_path = model_dir / 'hyperparameters.json'
    hyperparams_path.write_bytes(Env.hyperparams_path.read_bytes())

    return load(model_dir / Env.model_artifacts_fname)


def input_fn(input_data, content_type):
    assert content_type == 'CSV'
    hyperparams = load_hyperparams(Env.hyperparams_path)

    return input_data_to_embeddings(
        io.BytesIO(input_data), hyperparams.model_name,
        hyperparams.ppcs_params, hyperparams.tknr_params)


def predict_fn(input_object, clf):
    return clf.predict(input_object)


def output_fn(prediction, content_type):
    assert content_type == 'application/json'
    return json.dumps(prediction.tolist())

import io

import pandas as pd

from .process import input_data_to_embeddings


def model_fn(self, model_dir):
    pass


def input_fn(self, input_data, content_type):
    assert content_type == 'CSV'

    return input_data_to_embeddings(io.BytesIO(input_data))


def output_fn(self, prediction, accept):
    pass
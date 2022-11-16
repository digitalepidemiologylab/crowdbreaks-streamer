import sys

import numpy as np

from .env import Env
from .helpers import (load_json_and_print, load_data_paths_and_print,
                      load_hyperparams, print_env_var, handle_exceptions,
                      save_model_artifacts, write_to_file)
from .train import train_moob_bert


@handle_exceptions(Env.failure_path)
def train():
    if (len(sys.argv) < 2) or (sys.argv[1] != "train"):
        print("Missing required argument 'train'.", file=sys.stderr)
        sys.exit(1)

    print("\nLoading config...")

    with Env.hyperparams_path.open() as json_file:
        print(json_file.read())

    hyperparams = load_hyperparams(Env.hyperparams_path)
    input_data_paths = load_data_paths_and_print(
        Env.inputdataconfig_path, Env.data_dir)
    input_stream_path = input_data_paths['stream']
    input_model_path = input_data_paths.get('model')
    resource_config = load_json_and_print(Env.resource_path)

    print_env_var(Env.training_job_name_env)
    print_env_var(Env.training_job_arn_env)

    print("\nRunning training...")

    # Train MOOB
    scores, metrics_list, clf = train_moob_bert(
        hyperparams.model_name, input_stream_path, input_model_path,
        hyperparams.eval_mode, hyperparams.n_estimators,
        hyperparams.chunk_size, hyperparams.interval,
        hyperparams.clf_params, hyperparams.ppcs_params,
        hyperparams.tknr_params)

    # At the end of the training loop, we have to save model artifacts.
    print(type(clf))
    save_model_artifacts(
        Env.model_artifacts_dir, Env.model_artifacts_fname, clf)
    # Save hyperparameters to model artifacts path to be read by
    # the inference container
    Env.hyperparams_path.write_bytes(
        (Env.model_artifacts_dir / 'hyperparameters.json').read_bytes())
    np.savetxt(Env.output_path / 'data/scores.csv', scores, delimiter=',')
    metrics_list = '[' + ' '.join(str(m) for m in metrics_list) + ']'
    write_to_file(Env.output_path / 'data/metrics_list.json', metrics_list)
    print('Printing output_path')
    print(*Env.output_path.iterdir(), sep="\n")

    print("\nTraining completed!")

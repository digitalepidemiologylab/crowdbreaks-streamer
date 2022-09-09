import sys
import time

from .config import load_hyperparams
from .env import Env
from .helpers import ExitSignalHandler
from .helpers import (load_json_and_print, load_data_paths_and_print,
                      print_env_var, handle_exceptions, save_model_artifacts)
from .train import train_moob_bert


@handle_exceptions
def train():
    print("\nLoading config...")

    hyperparams = load_json_and_print(Env.hyperparams_path)
    hyperparams = load_hyperparams(hyperparams)
    input_data_paths = load_data_paths_and_print(Env.inputdataconfig_path)
    input_stream_path = input_data_paths['stream']
    input_model_path = input_data_paths.get('model')
    resource_config = load_json_and_print(Env.resource_path)

    print_env_var(Env.training_job_name_env)
    print_env_var(Env.training_job_arn_env)
        
    # This object is used to handle SIGTERM and SIGKILL signals.
    signal_handler = ExitSignalHandler()

    print("\nRunning training...")

    # Train MOOB
    scores, metrics_list, clf = train_moob_bert(
        input_stream_path, input_model_path, hyperparams.clf_params,
        hyperparams.eval_mode, hyperparams.n_estimators,
        hyperparams.chunk_size, hyperparams.interval)
    
    # At the end of the training loop, we have to save model artifacts.
    save_model_artifacts(Env.model_artifacts_dir, clf)
    
    print("\nTraining completed!")


if __name__ == "__main__":
    if (sys.argv[1] == "train"):
        train()
    else:
        print("Missing required argument 'train'.", file=sys.stderr)
        sys.exit(1)

from functools import wraps
import json
import os
import pickle
import pprint
import signal
import sys


# Signal handler
class ExitSignalHandler:
    def __init__(self):
        self.exit_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.exit_now = True


# Helpers
def load_json_object(json_file_path):
    with json_file_path.open() as json_file:
        return json.load(json_file)


def print_json_object(json_object):
    pprint.pprint(json_object)


def load_json_and_print(path):
    if path.exists() and path.is_file():
        json_object = load_json_object(path)
        print(f'\n{path}: ')
        print_json_object(json_object)
        return json_object


def print_env_var(key):
    if key in os.environ:
        print(f'\n{key}: ')
        print(os.environ[key])


def files_in_path(path):
    return [child for child in path.iterdir() if child.is_file()]


def load_data_paths_and_print(inputdataconfig_path, data_dir):
    input_data_config = load_json_and_print(inputdataconfig_path)
    if 'model' not in input_data_config:
        print("'model' channel missing. "
              'The model will be trained from scratch.')
    if 'stream' not in input_data_config:
        raise ValueError("'stream' channel missing.")
    input_data_config = {k: v for k, v in input_data_config.items()
                         if k in ['stream', 'model']}

    input_data_paths = {}
    for key in input_data_config:
        channel_path = data_dir.joinpath(key)
        files = files_in_path(channel_path)
        if len(files) != 1:
            raise ValueError('There should be exactly one file per channel '
                             'containing all of the data.')
        input_data_paths[key] = files[0]
        print('\nData path for {key} channel: ')
        print(input_data_paths[key])

    return input_data_paths


def save_model_artifacts(model_artifacts_path, model):
    if model_artifacts_path.exists() and model_artifacts_path.is_dir():
        pickle.dump(model, model_artifacts_path)


def write_failure_file(failure_file_path, failure_reason):
    failure_file = failure_file_path.open('w')
    failure_file.write(failure_reason)
    failure_file.close()


def write_output_file(output_file_path, output_info):
    output_file = output_file_path.open('w')
    output_file.write(output_info)
    output_file.close()


def handle_exceptions(failure_path, exc=Exception):
    def handle_exc(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except exc as e:
                write_failure_file(
                    failure_path, f'{type(exc).__name__}: {str(exc)}')
                print(e, file=sys.stderr)
                sys.exit(1)
        return wrapper
    return handle_exc

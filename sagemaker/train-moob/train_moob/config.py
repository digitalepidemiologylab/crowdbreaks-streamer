from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Union

import dacite


class EvalMode(Enum):
    PREQUENTIAL = 1
    TEST_THEN_TRAIN = 2


class Activation(Enum):
    IDENTITY = 1
    LOGISTIC = 2
    TANH = 3
    RELU = 4


class Solver(Enum):
    LBFGS = 1
    SGD = 2
    ADAM = 3


class Padding(Enum):
    LONGEST = 1
    MAX_LENGTH = 2
    DO_NOT_PAD = 3


# https://huggingface.co/docs/transformers/main_classes/tokenizer#transformers.PreTrainedTokenizer.__call__
@dataclass(frozen=True)
class BertTokenizer:
    truncation: Optional[bool] = None
    padding: Optional[Padding] = None
    max_length: Optional[int] = None
    add_special_tokens: Optional[bool] = None


@dataclass(frozen=True)
class MLPClassifier:
    activation: Activation
    hidden_layer_sizes: List[int]
    solver: Solver
    max_iter: int
    random_state: Optional[int] = None


@dataclass(frozen=True)
class Preprocess:
    remove_punctuation: Optional[bool] = None
    standardize_punctuation: Optional[bool] = None
    asciify_emoji: Optional[bool] = None
    remove_emoji: Optional[bool] = None
    merge_multiple_users: Optional[bool] = None
    merge_multiple_urls: Optional[bool] = None
    merge_multiple_emails: Optional[bool] = None
    replace_url_with: Optional[str] = None
    replace_user_with: Optional[str] = None
    replace_email_with: Optional[str] = None
    min_num_tokens: Optional[int] = None
    lemmatize: Optional[bool] = None
    remove_stop_words: Optional[bool] = None
    asciify: Optional[bool] = None
    lower_case: Optional[bool] = None
    min_num_chars: Optional[int] = None


@dataclass(frozen=True)
class Hyperparams:
    eval_mode: EvalMode
    n_estimators: int
    chunk_size: int
    interval: int
    ppcs_params: Preprocess
    tknr_params: BertTokenizer
    clf_params: Optional[MLPClassifier] = None


converter = {
    EvalMode: lambda x: EvalMode[x.upper().replace('-', '_')],
    Activation: lambda x: Activation[x.upper()],
    Solver: lambda x: Solver[x.upper()]
}


def load_hyperparams(d):
    return dacite.from_dict(data_class=Hyperparams, data=d,
                            config=dacite.Config(type_hooks=converter))

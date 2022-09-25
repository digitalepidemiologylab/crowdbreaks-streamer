import pytest

from .config import (EvalMode, Activation, Solver, MLPClassifier, Preprocess,
                    BertTokenizer, Hyperparams, load_hyperparams)

from dacite.exceptions import MissingValueError


test_correct = [
    {
        'eval_mode': 'prequential',
        'n_estimators': 5,
        'chunk_size': 1000,
        'interval': 200,
        'ppcs_params': {
            'standardize_punctuation': True,
            'asciify_emoji': True,
            'replace_url_with': 'twitterurl',
            'replace_user_with': 'twitteruser',
            'replace_email_with': 'twitteremail',
            'merge_multiple_users': True,
            'merge_multiple_urls': True,
            # Haven't found a single tweet with stacked multiple emails.
            'merge_multiple_emails': False,
            'asciify': False
        },
        'tknr_params': {}
    },
    {
        'eval_mode': 'test-then-train',
        'n_estimators': 1,
        'chunk_size': 800,
        'interval': 100,
        'clf_params': {
            'activation': 'logistic',
            'hidden_layer_sizes': [],
            'solver': 'adam',
            'max_iter': 500,
            'random_state': 1
        },
        'ppcs_params': {},
        'tknr_params': {}
    },
    {
        'eval_mode': 'test-then-train',
        'n_estimators': 1,
        'chunk_size': 800,
        'interval': 100,
        'clf_params': {
            'activation': 'logistic',
            'hidden_layer_sizes': [],
            'solver': 'adam',
            'max_iter': 500
        },
        'ppcs_params': {},
        'tknr_params': {}
    }
]

missing_interval = {
    'eval_mode': 'prequential',
    'n_estimators': 5,
    'chunk_size': 1000,
    'ppcs_params': {},
    'tknr_params': {}
}

missing_activation = {
    'eval_mode': 'test-then-train',
    'n_estimators': 1,
    'chunk_size': 800,
    'interval': 100,
    'clf_params': {
        'hidden_layer_sizes': [],
        'solver': 'adam',
        'max_iter': 500
    },
    'ppcs_params': {},
    'tknr_params': {}
}

missing_ppcs_params = {
    'eval_mode': 'test-then-train',
    'n_estimators': 1,
    'chunk_size': 800,
    'interval': 100,
    'clf_params': {
        'activation': 'logistic',
        'hidden_layer_sizes': [],
        'solver': 'adam',
        'max_iter': 500
    },
    'tknr_params': {}
}

missing_tknr_params = {
    'eval_mode': 'test-then-train',
    'n_estimators': 1,
    'chunk_size': 800,
    'interval': 100,
    'clf_params': {
        'activation': 'logistic',
        'hidden_layer_sizes': [],
        'solver': 'adam',
        'max_iter': 500
    },
    'ppcs_params': {}
}


def test_config():
    hyperparams = [load_hyperparams(config) for config in test_correct]

    assert hyperparams == [
        Hyperparams(**{
            'eval_mode': EvalMode.PREQUENTIAL,
            'n_estimators': 5,
            'chunk_size': 1000,
            'interval': 200,
            'clf_params': None,
            'ppcs_params': Preprocess(**{
                'standardize_punctuation': True,
                'asciify_emoji': True,
                'replace_url_with': 'twitterurl',
                'replace_user_with': 'twitteruser',
                'replace_email_with': 'twitteremail',
                'merge_multiple_users': True,
                'merge_multiple_urls': True,
                # Haven't found a single tweet with stacked multiple emails.
                'merge_multiple_emails': False,
                'asciify': False
            }),
            'tknr_params': BertTokenizer()
        }),
        Hyperparams(**{
            'eval_mode': EvalMode.TEST_THEN_TRAIN,
            'n_estimators': 1,
            'chunk_size': 800,
            'interval': 100,
            'clf_params': MLPClassifier(**{
                'activation': Activation.LOGISTIC,
                'hidden_layer_sizes': [],
                'solver': Solver.ADAM,
                'max_iter': 500,
                'random_state': 1
            }),
            'ppcs_params': Preprocess(),
            'tknr_params': BertTokenizer()
        }),
        Hyperparams(**{
            'eval_mode': EvalMode.TEST_THEN_TRAIN,
            'n_estimators': 1,
            'chunk_size': 800,
            'interval': 100,
            'clf_params': MLPClassifier(**{
                'activation': Activation.LOGISTIC,
                'hidden_layer_sizes': [],
                'solver': Solver.ADAM,
                'max_iter': 500,
                'random_state': None
            }),
            'ppcs_params': Preprocess(),
            'tknr_params': BertTokenizer()
        })
    ]

    with pytest.raises(MissingValueError) as excinfo:
        load_hyperparams(missing_interval)
    assert 'missing value for field "interval"' in str(excinfo.value)

    with pytest.raises(MissingValueError) as excinfo:
        load_hyperparams(missing_activation)
    assert 'missing value for field "clf_params.activation"' in str(excinfo.value)

    with pytest.raises(MissingValueError) as excinfo:
        load_hyperparams(missing_ppcs_params)
    assert 'missing value for field "ppcs_params"' in str(excinfo.value)

    with pytest.raises(MissingValueError) as excinfo:
        load_hyperparams(missing_tknr_params)
    assert 'missing value for field "tknr_params"' in str(excinfo.value)

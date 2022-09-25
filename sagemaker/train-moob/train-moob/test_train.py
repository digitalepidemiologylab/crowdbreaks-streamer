from pathlib import Path
import pytest

from .config import MLPClassifier, Activation, Solver
from .train import train_moob_bert


def test_train():
    with pytest.raises(ValueError) as excinfo:
        input_model_path = Path('/some/path/')
        clf_params = MLPClassifier(Activation.LOGISTIC, (), Solver.ADAM, 500)
        train_moob_bert(None, input_model_path, None, None, None, None, clf_params, None)
    assert "'clf_params' should exist, and vice versa" in str(excinfo.value)
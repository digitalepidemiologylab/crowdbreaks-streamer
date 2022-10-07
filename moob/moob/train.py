
import os
import logging
import pickle

import numpy as np
import pandas as pd
from strlearn.streams import CSVParser
from strlearn.classifiers import SampleWeightedMetaEstimator
from strlearn.evaluators import Prequential, TestThenTrain
from strlearn.metrics import geometric_mean_score_1
from sklearn.neural_network import MLPClassifier

import torch
from transformers import BertModel, BertTokenizer
from twiprocess.preprocess import preprocess

from matplotlib import pyplot as plt

from .config import EvalMode
from .ensembles import MOOB  # Custom ensemble class
from .env import Env


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def calculate_n_chunks(n_instances, chunk_size):
    return int(np.ceil(n_instances / chunk_size))


def generate_embeddings(model_name, df, ppcs_params, tknr_params):
    # The following model generates 768-dimensional embeddings
    # model_name = 'bert-base-uncased'

    model = BertModel.from_pretrained(model_name)
    tokenizer = BertTokenizer.from_pretrained(model_name)

    ppcs_params = {k: v for k, v in ppcs_params.items() if v is not None}

    preprocessed_text_list = df.text.apply(preprocess, **ppcs_params).tolist()

    # Tokenization
    # max_seq_length = 96
    # Whether or not to encode the sequences with the special tokens
    # relative to their model
    # special_tokens_bool = True
    tokenizer_output = tokenizer(
        preprocessed_text_list, return_tensors='pt', **tknr_params)

    input_ids_tensor = tokenizer_output.data['input_ids']
    token_type_ids_tensor = tokenizer_output.data['token_type_ids']
    attention_mask_tensor = tokenizer_output.data['attention_mask']

    with torch.no_grad():
        model_output = model(
            input_ids=input_ids_tensor, token_type_ids=token_type_ids_tensor,
            attention_mask=attention_mask_tensor)
        # Extract hidden state corresponding to the CLS token
        # (this is different the pooled output produced by BertPooler
        # because in our case no activation function (hyperbolic tangent)
        # has been applied)
        hidden_state_cls_token = model_output['last_hidden_state'][:, 0, :]

    # Convert to Numpy array
    embeddings = hidden_state_cls_token.detach().numpy()

    return embeddings


def stream_processing(
    eval_mode, n_estimators, chunk_size, n_chunks,
    interval=0, clf=None, clf_params=None):
    if clf is None:
        # Create neural network; the classification model that will be used is
        # different from the finetuning of a BERT model because in our case
        # BERT's weights are not updated.
        # The data are processed in the same way as in Jay Alammar's blog post
        # "A Visual Guide to Using BERT for the First Time":
        # the model consists of a simple classification scheme analogous to
        # a logistic regression since we use a two-layer neural network (i.e.,
        # perceptron with no hidden layer) with a softmax activation function.
        # mlp_classifier = MLPClassifier(
        #     activation='logistic', hidden_layer_sizes=(), solver='adam',
        #     max_iter=500, random_state=0)
        mlp_classifier = MLPClassifier(**clf_params.__dict__.copy())
        # Note about the optimization algorithm (solver for weight optimization): 
        # the default solver ‘adam’ works pretty well on relatively large datasets
        # (with thousands of training samples or more) in terms of both
        # training time and validation score. 
        # For small datasets, however, ‘lbfgs’ can converge faster and perform better 
        # (Reminder: LBFGS = Limited-memory BFGS, where BFGS stands for
        # the Broyden-Fletcher-Goldfarb-Shanno algorithm).
        
        # Create base estimator
        base = SampleWeightedMetaEstimator(base_classifier=mlp_classifier)
        # Ensemble approach: Multiclass Oversampling-based Online Bagging (MOOB)
        clf = MOOB(base_estimator=base, n_estimators=n_estimators)

    # Load data stream
    stream = CSVParser(Env.embeddings_path, chunk_size=chunk_size, n_chunks=n_chunks)
    stream.classes_ = np.array([0, 1, 2])

    # Include the geometric mean of the classwise recall
    metrics_list = [geometric_mean_score_1]
    if eval_mode == EvalMode.PREQUENTIAL:
        evaluator = Prequential(metrics=metrics_list)
        evaluator.process(stream, clf, interval=interval)
    elif eval_mode == EvalMode.TEST_THEN_TRAIN:
        evaluator = TestThenTrain(metrics=metrics_list)
        evaluator.process(stream, clf)

    # evaluator.scores returns a three-dimensional Numpy array:
    #
    # The first dimension is the index of a classifier submitted for processing.
    # In our case the second argument passed to evaluator.process, i.e., clf,
    # has a length of 1 because we are considering one ensemble of classifiers
    # (and not multiple ensemble of classifiers).
    #
    # The second dimension specifies the instance of evaluation.
    # It is equivalent to n_chunks in the case of test-then-train evaluation
    # while the length of the second dimension is determined by the actual
    # number of chunks in the case of prequential evaluation.
    #
    # The third dimension indicates the metric used in the processing.
    scores = evaluator.scores[0, :, :]
    # Since the index associated with the first dimension is defined,
    # scores is a two-dimensional array.
    return scores, metrics_list, clf


def train_moob_bert(model_name, input_data_path, input_model_path,
                    eval_mode, n_estimators, chunk_size, interval,
                    clf_params, ppcs_params, tknr_params):
    """Trains an MOOB ensemble of BERT classifiers in a stream mode.

    Args:
        eval_mode (EvalMode, Enum): Estimation techniques implemented by
            the evaluators module of the strlearn package.
        n_estimators (int): Number of estimators in the ensemble classifier.
        chunk_size (int): The size of the sliding window.
        interval (int): The value of this argument should be provided
            in case of prequential evaluation: the interval represents
            the number of instances by which the sliding window moves
            before the next evaluation and training steps.
    """
    if (input_model_path is None) != (clf_params is not None):
        raise ValueError("In case there is no 'input_model_path', "
                         "'clf_params' should exist, and vice versa.")

    df = pd.read_csv(input_data_path, parse_dates=['created_at'])
    df = df.sort_values(by=['created_at'])
    labels_list = sorted(df.label.unique())
    labels_to_num_dict = {k: v for v, k in enumerate(labels_list)}
    mapped_labels = df.label.map(labels_to_num_dict).tolist()

    embeddings = pd.DataFrame(generate_embeddings(
        model_name, df, ppcs_params, tknr_params))
    embeddings = pd.concat([embeddings, pd.Series(mapped_labels)], axis=1)
    # Save stream as a headerless CSV file
    # (the rightmost column corresponds to the class labels)
    embeddings.to_csv(Env.embeddings_path, index=False, header=False)

    n_instances = len(df)
    # n_chunks represents the number of chunks in a stream to which
    # a test-then-train procedure would be applied. 
    # That's how this parameter should be understood,
    # *even when using the prequential evaluation mode*. 
    # Example: n_instances = 22814 tweets and chunk_size = 1000 tweets ->
    # we have n_chunks = 23
    # (22 chunks with chunk_size=1000 tweets, and 1 chunk with 814 tweets)
    n_chunks = calculate_n_chunks(n_instances, chunk_size)

    clf = pickle.load(input_model_path) if input_model_path else None

    logger.info('Process data...')
    return stream_processing(eval_mode, n_estimators, chunk_size, n_chunks,
                             interval, clf, clf_params)



# Metric plot
def prequential(n_chunks, n_instances, interval, chunk_size):
    all_chunks_list = []
    lower_bound = - interval
    n_windows = (n_chunks - 1) * 2

    for i in range(n_windows):
        lower_bound += interval
        if i == n_windows - 1:
            upper_bound = n_instances
        else:
            upper_bound = lower_bound + chunk_size
        all_chunks_list.append([lower_bound, upper_bound])

    return all_chunks_list


def test_then_train(n_chunks, n_instances, chunk_size):
    all_chunks_list = []
    lower_bound = 0
    n_windows = n_chunks - 1

    for i in range(n_windows):
        lower_bound += chunk_size
        if i == n_windows - 1:
            upper_bound = n_instances
        else:
            upper_bound = lower_bound + chunk_size
        all_chunks_list.append([lower_bound, upper_bound])

    return all_chunks_list


def plot_metrics(
    evaluator_scores, metrics_list, eval_mode, df,
    n_estimators, chunk_size, interval, output_dir
):
    n_instances = len(df)
    n_chunks = calculate_n_chunks(n_instances, chunk_size)
    if eval_mode == EvalMode.PREQUENTIAL:
        all_chunks_list = prequential(n_chunks, n_instances, interval, chunk_size)
    elif eval_mode == EvalMode.TEST_THEN_TRAIN:
        all_chunks_list = test_then_train(n_chunks, n_instances, chunk_size)

    fig, ax = plt.subplots(figsize=(7, 7), nrows=1, ncols=1, dpi=300)

    logger.info('Generate figure...')
    for m, metric in enumerate(metrics_list):
        # ax.plot(evaluator_scores[:, m], marker='o', label=metric.__name__)
        ax.plot(evaluator_scores[:, m], marker='o')

    xticks_list = df.created_at[np.array(all_chunks_list)[:,0]].tolist()
    xticks_list = [timestamp.strftime('%Y-%m-%d') for timestamp in xticks_list]
    ax.set_xticks(np.arange(0, len(evaluator_scores)))
    ax.set_xticklabels(xticks_list)
    plt.xticks(rotation=90, fontsize=8)
    ax.set_xlabel('Time')

    # ax.legend()
    # ax.set_ylim([0, 1])
    ax.set_ylim([0, .8])
    ax.set_ylabel('G-mean')

    ax.set_title('Performance of the online classifier')
    plt.tight_layout() 
    fig.savefig(os.path.join(
        output_dir,
        f'{eval_mode.name.lower()}_evaluation_ensemble_with_{n_estimators}_base_estimators_'
        f'performance_{chunk_size}_instances_per_chunk_'
        f'{interval}_instances_per_sliding_step.png'))

import pandas as pd
import torch

from transformers import BertModel, BertTokenizer
from twiprocess.preprocess import preprocess


def generate_embeddings(model_name, df, ppcs_params, tknr_params):
    model = BertModel.from_pretrained(model_name)
    tokenizer = BertTokenizer.from_pretrained(model_name)

    ppcs_params = {k: v for k, v in ppcs_params.items() if v is not None}

    preprocessed_text_list = df.text.apply(preprocess, **ppcs_params).tolist()

    # Tokenization
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


def input_data_to_embeddings(data_source, model_name, ppcs_params, tknr_params):
    df = pd.read_csv(data_source, parse_dates=['created_at'])
    df = df.sort_values(by=['created_at'])
    labels_list = sorted(df.label.unique())
    labels_to_num_dict = {k: v for v, k in enumerate(labels_list)}
    mapped_labels = df.label.map(labels_to_num_dict).tolist()

    embeddings = pd.DataFrame(generate_embeddings(
        model_name, df, ppcs_params, tknr_params))
    return pd.concat([embeddings, pd.Series(mapped_labels)], axis=1)

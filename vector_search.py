import os
from typing import Tuple
import pandas as pd
import numpy as np
import vertexai
import google.generativeai as genai
import backoff
from tenacity import retry, stop_after_attempt, wait_random_exponential
from google.oauth2 import service_account
from scipy.spatial.distance import euclidean
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import find_dotenv, load_dotenv
import json


load_dotenv(find_dotenv())
project_id = os.getenv('PROJECT_ID')
credentials = service_account.Credentials.from_service_account_file('aerobic-datum-429101-r4-59df87999b44.json')
vertexai.init(project=project_id, location='us-west1', credentials=credentials)
from vertexai.language_models import TextEmbeddingModel
embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")


@retry(wait=wait_random_exponential(min=10, max=120), stop=stop_after_attempt(5))
def embedding_model_with_backoff(text=[]):
    try:
        embeddings = embedding_model.get_embeddings(text)
        #print(f"embedding for text: {text} complete.")
        return [each.values for each in embeddings][0]
    except TypeError as te:
        print(te)

# get_context_from_question
def dot_product(
    question: str, vector_store: pd.DataFrame, sort_index_value: int = 2
    ) -> Tuple[str, pd.DataFrame]:

    query_vector = np.array(embedding_model_with_backoff([question]))
    vector_store["dot_product"] = vector_store["embedding"].apply(
        lambda row: np.dot(row, query_vector)
    )

    top_matched = vector_store.sort_values(by="dot_product", ascending=False)[
        :sort_index_value
    ].index
    top_matched_df = vector_store.loc[top_matched, ["file_name", "chunks"]]
    context = "\n".join(top_matched_df["chunks"].values)
    
    return context, top_matched_df


def euclidean_distance(
    question: str, vector_store: pd.DataFrame, sort_index_value: int = 2
    ) -> Tuple[str, pd.DataFrame]:

    query_vector = np.array(embedding_model_with_backoff([question]))
    vector_store['euclidean_distance'] = vector_store['embedding'].apply(
        lambda row: euclidean(row, query_vector)
    )

    top_matched = vector_store.sort_values(by="euclidean_distance")[
        :sort_index_value
    ].index
    top_matched_df = vector_store.loc[top_matched, ['file_name', 'chunks']]
    context = "\n".join(top_matched_df['chunks'].values)

    return context, top_matched_df

# cosine similarity name is already taken
def cosine_similitude(
    question: str, vector_store: pd.DataFrame, sort_index_value: int = 2
    ) -> Tuple[str, pd.DataFrame]:

    query_vector = np.array(embedding_model_with_backoff([question]))
    vector_store['cosine_similarity'] = vector_store['embedding'].apply(
        lambda row: cosine_similarity([row], [query_vector])[0][0]
    )
    top_matched = vector_store.sort_values(by='cosine_similarity', ascending=False)[
        :sort_index_value
    ].index

    top_matched_df = vector_store.loc[top_matched, ["file_name", "chunks"]]
    context = "\n".join(top_matched_df["chunks"].values)

    return context, top_matched_df


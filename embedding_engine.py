from openai import OpenAI
from config import OPENAI_API_KEY
import numpy as np
import traceback

client = OpenAI(

    api_key=OPENAI_API_KEY,

    timeout=60.0

)


# ======================================================
# CREATE EMBEDDING
# ======================================================

def create_embedding(text):

    try:

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )

        return response.data[0].embedding

    except Exception as e:


        print("[EMBEDDING ERROR]")
        traceback.print_exc()

        return None


# ======================================================
# COSINE SIMILARITY
# ======================================================

def cosine_similarity(vec1, vec2):

    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    dot_product = np.dot(vec1, vec2)

    norm_a = np.linalg.norm(vec1)
    norm_b = np.linalg.norm(vec2)

    if norm_a == 0 or norm_b == 0:
        return 0

    return dot_product / (norm_a * norm_b)
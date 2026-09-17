import logging

import numpy as np
from openai import (
    APIError,
    AuthenticationError,
    OpenAI,
    PermissionDeniedError,
)

from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=OPENAI_API_KEY,
    timeout=60.0,
)


# ======================================================
# CREATE EMBEDDING
# ======================================================

def create_embedding(text):
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding
    except (AuthenticationError, PermissionDeniedError):
        logger.error(
            "Embedding request rejected by OpenAI auth "
            "(check OPENAI_API_KEY / billing). Returning None; "
            "semantic memory recall is degraded until this is fixed.",
            exc_info=True,
        )
        return None
    except APIError:
        logger.warning(
            "Transient OpenAI error while creating embedding; "
            "returning None and degrading gracefully.",
            exc_info=True,
        )
        return None
    except Exception:
        logger.exception("Unexpected error in create_embedding")
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

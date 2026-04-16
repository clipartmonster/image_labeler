try:
    import torch
except ImportError:
    torch = None

try:
    from elasticsearch import Elasticsearch
except ImportError:
    Elasticsearch = None

from django.conf import settings
from django.apps import apps
import time
import traceback

def get_text_vector(
    text,
    normalize=True
):
    """
    Args:
        text: str
        normalize: L2 normalize embedding
    Returns:
        List[float] embedding
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    config = apps.get_app_config('labeling_api')
    text_processor = config.text_processor
    text_pca = config.text_pca

    if text_processor is None or torch is None:
        raise RuntimeError(
            "Text embedding models not loaded; install torch + sentence_transformers or skip search endpoints."
        )

    with torch.no_grad():
        text_vector = text_processor.encode(
            text,               # list[str]
            batch_size=16,       # even 4 helps
            normalize_embeddings=True
        )

    if text_pca is not None:
        text_vector = text_pca.transform([text_vector])[0]  # PCA usually expects 2D array

    # Ensure Python list for consistency
    return text_vector.tolist()

def get_image_vector(image):
    """
    Get 128-dimensional embedding vector for a single image using DINOv2.

    Args:
        image: PIL Image object

    Returns:
        List[float]: 128-dimensional embedding vector
    """
    import torch
    from django.apps import apps
    import torch.nn.functional as F

    # Get pre-loaded objects from AppConfig
    config = apps.get_app_config('labeling_api')
    model = config.dino_model
    processor = config.dino_processor
    dino_pca = config.dino_pca

    device = next(model.parameters()).device

    # Preprocess image
    inputs = processor(images=image, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(device)

    model.eval()
    with torch.no_grad():
        outputs = model(pixel_values=pixel_values)

        # CLS token embedding: [batch, hidden_dim]
        embedding = outputs.last_hidden_state[:, 0, :]

        # L2 normalize
        embedding = F.normalize(embedding, dim=-1)

    # Convert to numpy
    image_vector = embedding.squeeze(0).cpu().numpy()

    # Optional PCA to 128 dims
    if dino_pca is not None:
        image_vector = dino_pca.transform(image_vector.reshape(1, -1))[0]
    else:
        image_vector = image_vector[:128]

    return image_vector.tolist()

# Module-level ES client cache
_es_client = None

def _get_es_client():
    """Get or create a shared Elasticsearch client."""
    global _es_client
    if Elasticsearch is None:
        raise RuntimeError("elasticsearch package not installed")
    if _es_client is None:
        _es_client = Elasticsearch(**settings.ELASTICSEARCH_DSL["default"])
    return _es_client

def get_text_scores(text_string, num_results = 500):
  
    text_vector = get_text_vector(text_string) 

    # Use shared ES client (no ping check to reduce overhead)
    es = _get_es_client()

    knn_query = {
    "field": "text_embedding",
    "query_vector": text_vector,
    "k": num_results,
    "num_candidates": num_results * 2
    }
    
    response = es.search(
        index="mini_llm_text_embedding_index",
        size=num_results,
        knn=knn_query
    )
    
    hits = response.get("hits", {}).get("hits", [])
    
    listings = [
        {
            "asset_id": hit["_source"]["asset_id"],
            "score": hit["_score"]

        }
        for hit in hits
    ]

    return listings

def get_image_scores(image_vector, index = 'dino_384_image_embedding_index', num_results = 500):

    # Use shared ES client
    es = _get_es_client()

    knn_query = {
        "field": "embedding_vector",
        "query_vector": image_vector,
        "k": num_results,
        "num_candidates": num_results * 2
    }

    response = es.search(
        index = index,
        size=num_results,
        knn=knn_query,
        source=["asset_id"]  # only return fields you need
    )

    hits = response.get("hits", {}).get("hits", [])

    listings = [
        {
            "asset_id": hit["_source"]["asset_id"],
            "score": hit["_score"]
        }
        for hit in hits
    ]

    return listings



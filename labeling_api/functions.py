from elasticsearch import Elasticsearch
from django.conf import settings
from PIL import Image
import requests
from io import BytesIO
from django.utils import timezone
from .models import search_term_responses_table

# Create a session with connection pooling for image loading
_image_session = None

def _get_image_session():
    """Get or create a requests session with connection pooling."""
    global _image_session
    if _image_session is None:
        _image_session = requests.Session()
        # Configure adapter with connection pooling
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=Retry(total=1, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        )
        _image_session.mount('http://', adapter)
        _image_session.mount('https://', adapter)
    return _image_session

# Module-level ES client cache
_es_client_design = None

def _get_es_client_design():
    """Get or create a shared Elasticsearch client for design features."""
    global _es_client_design
    if _es_client_design is None:
        from elasticsearch import Elasticsearch
        _es_client_design = Elasticsearch(**settings.ELASTICSEARCH_DSL["default"])
    return _es_client_design

def get_asset_design_features(asset_ids):
    """
    Find design features for multiple assets in Elasticsearch.
    
    Args:
        asset_ids: List of asset IDs to search for
        
    Returns:
        list: List of design features documents
    """
    # Use shared ES client
    es = _get_es_client_design()
    index_name = "design_feature_index"
    
    try:
        query = {
            "query": {
                "terms": {
                    "asset_id": asset_ids
                }
            },
            "size": len(asset_ids)
        }
        
        response = es.search(index=index_name, body=query)
        
        # Return list of documents
        return [hit['_source'] for hit in response['hits']['hits']]
            
    except Exception as e:
        print(f"Error searching for asset_ids: {e}")
        return []
    

def load_image(image_source):
    """
    Load an image from either a URL or local file path.
    Uses connection pooling for better performance.
    
    Args:
        image_source: URL or file path
        
    Returns:
        PIL.Image.Image
    """
    if isinstance(image_source, str) and (image_source.startswith('http://') or image_source.startswith('https://')):
        # Download from URL using session with connection pooling
        session = _get_image_session()
        response = session.get(image_source, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    else:
        # Open local file
        return Image.open(image_source)



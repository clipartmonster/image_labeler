from django.apps import AppConfig
from pathlib import Path
import pickle

import psutil, os

def print_memory_usage(note=""):
    process = psutil.Process(os.getpid())
    mem_bytes = process.memory_info().rss
    mem_mb = mem_bytes / (1024 * 1024)
    print(f"[MEM] {note}: {mem_mb:.2f} MB")

class LabellingApiConfig(AppConfig):
    name = "labeling_api"
    path = str(Path(__file__).resolve().parent)
    
    # Class-level attributes to store models
    text_processor = None
    dino_model = None
    dino_processor = None
    text_pca = None
    dino_pca = None

    def ready(self):
        """
        Load models once when Django starts
        """
        # Only load in the main process, not in reloader process
        import sys
        import os
        
        # For production (gunicorn, uwsgi, etc.)
        if 'runserver' not in sys.argv:
            self.load_models()
        # For development runserver - only load once, not on auto-reload
        elif os.environ.get('RUN_MAIN') == 'true':
            self.load_models()
    
    def load_models(self):
        """Load heavy ML models once for CPU-friendly, low-memory inference"""
        try:
            import torch
        except ImportError:
            print("[labeling_api] torch not installed; skipping ML models (embedding search disabled).")
            return

        device1 = torch.device("cpu")  # force CPU

        # -----------------------
        # Load SentenceTransformer for text
        # -----------------------
        if LabellingApiConfig.text_processor is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                print("[labeling_api] sentence_transformers not installed; skipping ML models.")
                return

            model_name = "all-MiniLM-L6-v2"
            print(f"Loading lightweight text model: {model_name} (CPU)")
            LabellingApiConfig.text_processor = SentenceTransformer(
                model_name,
                device="cpu"
            )
            print("✓ Text processor model loaded successfully!")
            print_memory_usage("After loading MiniLM")
    
        # -----------------------
        # Load PCA (.pkl)
        # -----------------------
        if LabellingApiConfig.text_pca is None:
            pca_path = Path(self.path) / "modeling_files" / "mini_llm_text_embedding_index_pca_model.pkl"

            if not pca_path.exists():
                raise FileNotFoundError(f"PCA file not found: {pca_path}")

            with open(pca_path, "rb") as f:
                LabellingApiConfig.text_pca = pickle.load(f)

            print("✓ PCA model loaded (pickle)")       
            print_memory_usage("After loading PCA")
        
        # -----------------------
        # Load Dino for image embeddings
        # -----------------------
        if LabellingApiConfig.dino_model is None:
            from transformers import AutoModel, AutoProcessor
            import torch

            model_name = "facebook/dinov2-base"  # DINOv2 Base (ViT-B/14)

            # Optional processor (kept for future image preprocessing consistency)
            LabellingApiConfig.dino_processor = AutoProcessor.from_pretrained(
                model_name,
                trust_remote_code=True
            )

            # Load model on CPU explicitly
            LabellingApiConfig.dino_model = AutoModel.from_pretrained(
                model_name,
                trust_remote_code=True,
                device_map="cpu",             # Force CPU
                torch_dtype=torch.float32,     # float16 not efficient on CPU
                low_cpu_mem_usage=True
            )

            LabellingApiConfig.dino_model.eval()

            print("✓ DINOv2 model warmed up and weights resident in RAM!")
            print_memory_usage("After Warmup")

        # -----------------------
        # Load PCA (.pkl)
        # -----------------------
        if LabellingApiConfig.dino_pca is None:
            pca_path = Path(self.path) / "modeling_files" / "dino_384_image_embedding_index_pca_model.pkl"

            if not pca_path.exists():
                raise FileNotFoundError(f"PCA file not found: {pca_path}")

            with open(pca_path, "rb") as f:
                LabellingApiConfig.dino_pca = pickle.load(f)

            print("✓ PCA model loaded (pickle)")       
            print_memory_usage("After loading PCA")
        
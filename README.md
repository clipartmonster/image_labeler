# Image Labeler

A Django-based internal tool for labeling, reviewing, and managing clipart image classifications. The system supports batch-based labeling workflows, integration with Amazon Mechanical Turk for crowdsourced labeling, ML-powered semantic search via embeddings, and tools for reviewing model predictions and reconciling label disagreements.

---

## Architecture Overview

```
+----------------------------------------------------------+
|                     BROWSER                               |
|  +------------------+  +-------------+  +--------------+ |
|  | HTML Templates   |  | api_calls.js|  | Canvas Tools | |
|  | + static JS      |  | (fetch)     |  | (brush/fill) | |
|  +--------+---------+  +------+------+  +------+-------+ |
+-----------|-------------------|----------------|----------+
            |                   |                |
            | HTTP              | HTTP           | Direct upload
            |                   |                |
+-----------|-------------------|--------+       |
|           v                   v        |       v
|  +--------+-------+  +-------+------+ |  +----+----+
|  | label_images   |  | labeling_api | |  | AWS S3  |
|  | (UI views)     |  | (JSON API)   | |  +---------+
|  |                |  |              | |
|  | - renders HTML |  | - 50+ endpoints
|  | - calls API    |  | - ORM models | |
|  |   via requests |  | - ES queries | |
|  +--------+-------+  +--+-------+--+ |
|           |              |       |     |
|           +--> @api_authorization <--+ |
|                (api/decorators.py)     |
|                                        |
|          DJANGO PROCESS                |
+------------+----------------+----------+
             |                |
             v                v
      +------+------+  +-----+--------+
      | PostgreSQL  |  |Elasticsearch |
      |             |  |              |
      | - content.* |  | - kNN vector |
      | - label_data|  |   indexes    |
      | - model_    |  | - design     |
      |   predictions  |   features   |
      +------+------+  +-----+--------+
             |                |
             v                v
+------------+----------------+----------+
|        OFFLINE ETL (new_labels/)       |
|                                        |
|  create_new_batch_cursor.py            |
|  create_misclassification_batch_cursor |
|  rebuild_selected_assets_cursor.py     |
|  reconcile.py                          |
|  Jupyter notebooks                     |
+----------------------------------------+

                  +----------+
                  |  Amazon  |
                  |  MTurk   |
                  +----+-----+
                       |
                       | iframe embed
                       v
                  (Browser UI)
```

### Component Relationships

- **`label_images`** (UI app) renders pages and makes server-side `requests` calls to `labeling_api` with an `Authorization` header.
- **`labeling_api`** (API app) is mounted at the site root. It handles all data reads/writes against PostgreSQL (via unmanaged ORM models) and Elasticsearch. Optionally loads ML models at startup for embedding-based search.
- **`api/decorators.py`** provides `@api_authorization`, which gates API endpoints with a shared secret (`API_ACCESS_KEY`).
- **Browser JS** (`api_calls.js`) calls the API directly via `fetch`, loading the auth key from `/get_config/`.
- **Canvas tools** upload color-map PNGs to S3 using AWS credentials served by `/get_config/`.
- **Amazon Mechanical Turk** embeds UI pages in an iframe for crowdsourced labeling.
- **Offline scripts** (`new_labels/`) connect directly to PostgreSQL and Elasticsearch for batch creation, reconciliation, and analysis.

---

## Repository Structure

```
image_labeler/                          # Repository root
├── DOCUMENTATION.md                    # Canonical architecture documentation
├── README.md                           # This file
├── .gitattributes
├── api/
│   ├── __init__.py
│   └── decorators.py                   # @api_authorization (shared-secret check)
├── labeling_api/                       # HTTP API app (installed at repo root level)
│   ├── apps.py                         # ML model loading on startup
│   ├── embedding_functions.py          # Text/image vector generation + ES kNN
│   ├── functions.py                    # Elasticsearch helpers, image loading
│   ├── models.py                       # Unmanaged ORM models (PostgreSQL schemas)
│   ├── urls.py                         # 50+ API endpoints
│   ├── validation_functions.py         # Input validation utilities
│   ├── views.py                        # All API request handlers
│   └── modeling_files/
│       ├── dino_384_image_embedding_index_pca_model.pkl
│       └── mini_llm_text_embedding_index_pca_model.pkl
└── image_labeler/                      # Django project directory
    ├── manage.py
    ├── requirements.txt
    ├── build.sh                        # Deploy: pip install + collectstatic
    ├── image_labeler/                  # Django project package
    │   ├── settings.py                 # Central configuration
    │   ├── urls.py                     # Root URL routing
    │   ├── views.py                    # /get_config/ endpoint
    │   ├── context_processors.py       # Injects LABELING_API_BASE_URL into templates
    │   ├── wsgi.py
    │   └── asgi.py
    ├── label_images/                   # Browser UI app
    │   ├── views.py                    # Server-rendered pages (calls API internally)
    │   ├── urls.py                     # /label_images/... routes
    │   ├── apps.py
    │   ├── templates/                  # MTurk-specific templates
    │   └── migrations/
    ├── new_labels/                     # Offline ETL scripts and notebooks
    │   ├── create_new_batch_cursor.py
    │   ├── create_misclassification_batch_cursor.py
    │   ├── rebuild_selected_assets_cursor.py
    │   ├── reconcile.py
    │   ├── select_image_for_labelling.py
    │   ├── new_labels.ipynb
    │   ├── reconcile.ipynb
    │   └── embedding_labels.ipynb
    ├── static/
    │   ├── css/                        # 17 page-specific stylesheets
    │   └── js/                         # 21 JS modules (API client, canvas tools, pages)
    └── templates/                      # 31 HTML templates + components
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Django 5.0.7 |
| API layer | Django REST Framework 3.15 |
| Database | PostgreSQL (via psycopg2-binary) |
| Search engine | Elasticsearch 8.15 |
| Text embeddings | SentenceTransformers (all-MiniLM-L6-v2) |
| Image embeddings | DINOv2 (facebook/dinov2-base) via HuggingFace Transformers |
| Dimensionality reduction | scikit-learn PCA (serialized .pkl) |
| Static files | WhiteNoise (compressed, long-term caching) |
| WSGI server | Gunicorn |
| HTTP client (server-side) | Requests |
| AI/LLM | OpenAI API |
| Data processing | Pandas, NumPy, Pillow |
| Deployment | Render.com |
| Crowdsourcing | Amazon Mechanical Turk |
| Object storage | AWS S3 (browser-side SDK) |
| Environment config | python-dotenv |

---

## How It All Fits Together

### 1. The Labeling Pipeline (end-to-end)

```
+-------------------+       +------------------------+       +-------------------+
| Offline:          |       | DB: label_data.        |       | Web UI:           |
| Create Batch      +------>| selected_assets_new    +------>| Setup Session     |
| (new_labels/*.py) |       |                        |       |                   |
+-------------------+       +------------------------+       +---------+---------+
                                                                       |
       +---------------------------------------------------------------+
       |
       v
+------+----------+       +-----------------------+       +---------------------+
| Labeling        |       | API: collect_label /  |       | DB: prompt_         |
| Interface       +------>| collect_prompt        +------>| responses           |
| (operator/MTurk)|       |                       |       |                     |
+-----------------+       +-----------------------+       +----------+----------+
                                                                      |
       +--------------------------------------------------------------+
       |
       v
+------+----------+       +-----------------------+       +---------------------+
| Offline:        |       | DB: reconciled        |       | Model Training      |
| Reconcile       +------>| labels                +------>| (external)          |
| (reconcile.py)  |       |                       |       |                     |
+-----------------+       +-----------------------+       +----------+----------+
                                                                      |
       +--------------------------------------------------------------+
       |
       v
+------+--------------+       +-------------------------+       +-------------------+
| DB: model_          |       | Review UI:              |       | Offline:          |
| predictions         +------>| view_model_results      +------>| Misclassification |
|                     |       | view_labels             |       | Batch Creation    |
+---------------------+       +-------------------------+       +--------+----------+
                                                                         |
                                            loops back to top -----------+
```

1. **Batch creation** — Offline scripts (`new_labels/`) query production model predictions and asset metadata, selecting images that need labeling (uncertain predictions, misclassifications) and writing them to `label_data.selected_assets_new`.

2. **Session setup** — An operator opens the web UI, selects an asset type and batch via `/label_images/setup_session/`. The UI calls the API to fetch available options.

3. **Labeling** — The operator (or MTurk worker in an iframe) views images and submits labels. Canvas tools enable color mask painting. Labels are collected via API endpoints (`collect_label`, `collect_prompt`, `update_color_labels`).

4. **Reconciliation** — When multiple labelers disagree, the `reconcile.py` pipeline aggregates responses, computes agreement stats, and produces final reconciled labels.

5. **Review & QA** — Pages like `view_labels`, `view_batch_labels`, and `view_model_results` let operators inspect results, correct mismatches, and manage labeling rules.

6. **Search & discovery** — Elasticsearch + ML embeddings enable finding similar images by text or image queries (`get_search_results`, `get_text_search_results`).

7. **Feedback loop** — Model predictions are reviewed, misclassifications are identified, and new batches are created from them — restarting the cycle.

---

### 2. Deployment Modes

| Mode | `LABELING_API_BASE_URL` | Description |
|------|------------------------|-------------|
| **Unified (recommended)** | `http://127.0.0.1:8000` | Single Django process serves both UI and API |
| **Split (legacy)** | Remote Render URL | UI and API on separate hosts; requires CORS + matching keys |

---

### 3. Request Flow

**Page load (server-rendered):**

```
Browser                label_images          labeling_api           PostgreSQL
  |                      (views.py)            (views.py)               |
  |-- GET /label_images/ -->|                       |                   |
  |                         |-- GET /get_session_options/ -->|          |
  |                         |   (+ Authorization header)    |          |
  |                         |                       |-- SELECT ... -->  |
  |                         |                       |<-- rows --------- |
  |                         |<-- JSON --------------|                   |
  |<-- rendered HTML -------|                       |                   |
```

**Client-side API call (e.g. submitting a label):**

```
Browser (api_calls.js)         labeling_api            PostgreSQL
  |                              (views.py)                |
  |-- POST /collect_label/ -------->|                      |
  |   (+ Authorization header)      |                      |
  |                                 |-- INSERT ... ------> |
  |                                 |<-- OK -------------- |
  |<-- JSON confirmation -----------|                      |
```

**Search request (embedding-based):**

```
Browser              labeling_api         MiniLM/PCA      Elasticsearch    PostgreSQL
  |                    (views.py)             |                |               |
  |-- GET /get_search_results/?q=cat -->|    |                |               |
  |                    |-- encode text ----->|                 |               |
  |                    |<-- vector ----------|                 |               |
  |                    |-- kNN search ----------------------->|               |
  |                    |<-- asset IDs ------------------------|               |
  |                    |-- SELECT metadata ---------------------------------------->|
  |                    |<-- asset details ------------------------------------------|
  |<-- JSON results ---|                     |                |               |
```

---

### 4. Database Schema (key tables)

The app uses **unmanaged Django models** mapping to pre-existing PostgreSQL tables across multiple schemas:

| Schema | Table | Purpose |
|--------|-------|---------|
| `label_data` | `selected_assets_new` | Queue of assets awaiting labeling |
| `label_data` | `prompt_responses` | Raw labeler responses |
| `label_data` | `labeling_rules` | Rule definitions for labeling workflows |
| `label_data` | `asset_type.rule.labels` | Reconciled final labels per rule |
| `content` | `assets` | Master asset catalog (images, metadata) |
| `content` | `extracted_features` | Design features for search filtering |
| `model_predictions` | various | ML model output scores |
| (public) | `asset_color_manual_label` | Manual color annotations with masks |
| (public) | `simulated_assets_color_table` | Simulated color data for evaluation |

---

### 5. ML / Embedding Search

```
+------------------------------------------------------------------+
|  Django Startup (AppConfig.ready)                                 |
|                                                                   |
|  +---------------------+          +------------------------+     |
|  | all-MiniLM-L6-v2    |          | facebook/dinov2-base   |     |
|  | (SentenceTransformer)|         | (HuggingFace)          |     |
|  | 384-dim text vectors |          | 768-dim image vectors  |     |
|  +----------+----------+          +-----------+------------+     |
|             |                                 |                   |
|             v                                 v                   |
|  +----------+----------+          +-----------+------------+     |
|  | Text PCA model      |          | Image PCA model        |     |
|  | (.pkl, reduces dims) |          | (.pkl, reduces dims)   |     |
|  +----------+----------+          +-----------+------------+     |
+-------------|-----------------------------+---+------------------+
              |                             |
              v                             v
+-------------+-----------------------------+---+------------------+
|  Search Request (runtime)                                        |
|                                                                   |
|  Query (text or image)                                           |
|       |                                                           |
|       v                                                           |
|  Encode with appropriate model (MiniLM or DINOv2)                |
|       |                                                           |
|       v                                                           |
|  PCA dimensionality reduction                                    |
|       |                                                           |
|       v                                                           |
|  Elasticsearch kNN against pre-indexed asset vectors             |
|       |                                                           |
|       v                                                           |
|  Ranked asset list                                               |
+------------------------------------------------------------------+
```

If `torch` or `sentence_transformers` are not installed, the app skips model loading and search endpoints are unavailable (all other functionality works normally).

---

### 6. Key API Endpoints

| Category | Endpoints | Purpose |
|----------|-----------|---------|
| **Session** | `get_session_options`, `get_asset_batch`, `get_batch_indexes` | Load labeling session configuration |
| **Labeling** | `collect_label`, `collect_prompt`, `add_label` | Submit labels from UI |
| **Color** | `get_color_labels`, `update_color_labels`, `remove_color_label` | Color mask management |
| **Review** | `get_asset_labels`, `get_batch_for_viewing`, `get_predictions` | View existing labels/predictions |
| **QA** | `get_disputed_assets`, `get_mismatched_labels`, `collect_label_issue` | Quality assurance workflows |
| **Search** | `get_search_results`, `get_text_search_results` | Embedding-based similarity search |
| **Rules** | `get_labelling_rules`, `add_a_rule` | Manage labeling rule definitions |
| **Batches** | `create_sub_batch`, `get_sub_batch_options`, `get_reconcile_count` | Batch management |
| **Experiments** | `create_experiment` | Create labeling experiments |
| **Line width** | `get_line_widths`, `collect_line_width_sample` | Line-width feature collection |
| **MTurk** | `get_test_questions`, `get_lure_questions`, `update_submission_status` | Mechanical Turk integration |

---

### 7. Frontend Architecture

The frontend uses server-rendered Django templates with vanilla JavaScript:

| Module | Role |
|--------|------|
| `api_calls.js` | Central API client; fetches config from `/get_config/`, builds all API request wrappers |
| `show_images.js` | Main labeling interface logic |
| `brush_tool.js` | Canvas brush for color mask painting |
| `flood_fill_tool.js` | Flood-fill tool for regions |
| `full_fill_tool.js` | Full-layer fill tool |
| `label_tools.js` | Shared labeling utilities |
| `general_functions.js` | Shared helpers |
| `setup_session.js` | Session configuration page logic |
| `manage_rules.js` | Rule management interface |
| `view_*.js` | View-specific logic (labels, predictions, batches, etc.) |

---

## Running Locally

### Prerequisites

- Python 3.10+
- PostgreSQL (with schemas matching production: `content`, `label_data`, `model_predictions`)
- Elasticsearch 8.x (optional, for search features)

### Setup

```bash
# 1. Install dependencies
cd image_labeler
pip install -r requirements.txt

# 2. For embedding search (optional, heavy dependencies)
pip install torch sentence-transformers transformers scikit-learn

# 3. Create .env file in image_labeler/
cat > .env << 'EOF'
DJANGO_KEY=your-secret-key
DATABASE_URL=postgres://user:pass@localhost:5432/dbname
API_ACCESS_KEY=your-api-key
LABELING_API_BASE_URL=http://127.0.0.1:8000
ELASTICSEARCH_HOSTS=http://127.0.0.1:9200
EOF

# 4. Run migrations (creates Django system tables only; app tables are unmanaged)
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Start the server
python manage.py runserver
```

Open http://127.0.0.1:8000/ (redirects to `/label_images/front_page/`).

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DJANGO_KEY` | Yes (prod) | Django SECRET_KEY |
| `DATABASE_URL` | Yes | PostgreSQL connection URL |
| `API_ACCESS_KEY` | Yes | Shared secret for API authorization |
| `LABELING_API_BASE_URL` | No | API base URL (defaults to self) |
| `ELASTICSEARCH_HOSTS` | No | Comma-separated ES URLs (default: localhost:9200) |
| `DATABASE_URL_PROD` | No | Read-only production DB for cross-env queries |
| `AWS_ACCESS_KEY_ID` | No | For S3 color map uploads (exposed to browser) |
| `AWS_SECRET_ACCESS_KEY` | No | For S3 color map uploads |
| `MTURK_ACCESS_ID` | No | MTurk requester credentials |
| `MTURK_SECRET_KEY` | No | MTurk requester credentials |
| `MTURK_HOST` | No | MTurk endpoint (defaults to sandbox) |
| `CACHE_URL` | No | Redis URL for caching (defaults to in-memory) |
| `RENDER` | No | Set to "true" in production to disable DEBUG |

---

## Deployment

The app deploys to **Render.com** using:

```bash
# build.sh (runs on deploy)
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

Production uses **Gunicorn** as the WSGI server with **WhiteNoise** for static file serving.

---

## Security Notes

- `/get_config/` exposes `API_ACCESS_KEY` and AWS credentials to the browser — acceptable only for trusted operator environments (not public-facing).
- `X_FRAME_OPTIONS = "ALLOWALL"` allows iframe embedding (required for MTurk integration).
- CORS is restricted to MTurk origins and the app's own domains.
- The `@api_authorization` decorator enforces the shared secret on protected endpoints.

---

## Offline Tools (`new_labels/`)

These scripts run outside the Django server for batch management:

| Script | Purpose |
|--------|---------|
| `create_new_batch_cursor.py` | Select assets needing labels based on prediction confidence bands |
| `create_misclassification_batch_cursor.py` | Find misclassified assets using ES similarity + model predictions |
| `rebuild_selected_assets_cursor.py` | Rebuild selection queues from reconciled labels |
| `reconcile.py` | Aggregate multi-labeler responses into final consensus labels |
| `select_image_for_labelling.py` | Asset download and S3 workflow utilities |
| `new_labels.ipynb` | Interactive batch creation workflow |
| `reconcile.ipynb` | Interactive reconciliation analysis |
| `embedding_labels.ipynb` | Embedding-based labeling prep and analysis |

# Technical Design Document (TDD): Reference Asset Library with AI Analysis & Multi-Reference Generation

**Version:** 1.0  
**Status:** Design Phase  
**Authors:** Video Generation Team

---

## **Table of Contents**

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Reference Asset Library](#3-reference-asset-library)
4. [AI Analysis & Categorization](#4-ai-analysis--categorization)
5. [Semantic Search System](#5-semantic-search-system)
6. [Auto-Matching Logic](#6-auto-matching-logic)
7. [Enhanced Image Generation (Phase 2)](#7-enhanced-image-generation-phase-2)
8. [Logo Overlay System](#8-logo-overlay-system)
9. [Enhanced Video Generation (Phase 3)](#9-enhanced-video-generation-phase-3)
10. [Model Configuration System](#10-model-configuration-system)
11. [Data Models](#11-data-models)
12. [Cost Analysis](#12-cost-analysis)
13. [Testing Strategy](#13-testing-strategy)
14. [Implementation Roadmap](#14-implementation-roadmap)

---

## **1. Executive Summary**

### **1.1 Problem Statement**

Current video generation lacks product/brand consistency:
- ❌ No way to specify exact products/logos to include
- ❌ Each storyboard image generates product variations
- ❌ Brand logos are hallucinated or incorrect
- ❌ No reusable asset library for brand materials

### **1.2 Solution Overview**

**New Capabilities:**
```
Reference Asset Library → AI Analysis → Semantic Search → Auto-Matching → ControlNet Generation → Logo Overlay
```

**Key Innovations:**
1. ✅ **Reference Asset Library:** Upload and manage product images, logos, brand assets
2. ✅ **AI Analysis:** GPT-4 Vision analyzes assets for automatic categorization
3. ✅ **Semantic Search:** CLIP embeddings + pgvector for intelligent asset matching
4. ✅ **Auto-Matching:** Automatically select relevant assets per beat
5. ✅ **ControlNet Integration:** 85% product consistency in storyboards
6. ✅ **Logo Overlay:** Pixel-perfect logo placement (no AI generation)
7. ✅ **Configurable Models:** Draft/Standard/Final quality tiers

### **1.3 Success Criteria**

- [ ] Users can upload and categorize reference assets
- [ ] AI analysis accuracy >90% for asset type detection
- [ ] Semantic search retrieves relevant assets with >80% precision
- [ ] Auto-matching selects appropriate assets >75% of the time
- [ ] Product consistency in storyboards: 85% (ControlNet)
- [ ] Logo placement: 100% pixel-perfect (overlay)
- [ ] Cost increase: <$0.015 per storyboard image

---

## **2. System Architecture**

### **2.1 Enhanced Pipeline Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INPUT + ASSET SELECTION                  │
│  "Create 15s Nike ad" + [Nike_Sneaker.png, Nike_Logo.png]      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 0: REFERENCE ASSET MANAGEMENT                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │  On Upload:                                      │           │
│  │  1. GPT-4V Analysis (asset type, colors, etc)   │           │
│  │  2. CLIP Embedding Generation                    │           │
│  │  3. Logo Detection                               │           │
│  │  4. Store in Database with Vector Index          │           │
│  └──────────────────────────────────────────────────┘           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│         PHASE 1: PLANNING + REFERENCE AUTO-MATCHING              │
│  ┌──────────────────────────────────────────────────┐           │
│  │  1. Intent Analysis (existing)                   │           │
│  │  2. Beat Selection (existing)                    │           │
│  │  3. Extract Product/Brand Entities (NEW)         │           │
│  │  4. Semantic Search for Matching Assets (NEW)    │           │
│  │  5. Build Reference Mapping per Beat (NEW)       │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                   │
│  Output: Spec + Reference Mapping                                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 2: STORYBOARD WITH CONTROLNET                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Beat 1       │  │ Beat 2       │  │ Beat 3       │          │
│  │ + Product    │  │ + Product    │  │ + Product    │          │
│  │   Reference  │  │   Reference  │  │   Reference  │          │
│  │ → ControlNet │  │ → ControlNet │  │ → ControlNet │          │
│  │ → Logo       │  │ → Logo       │  │ → Logo       │          │
│  │   Overlay    │  │   Overlay    │  │   Overlay    │          │
│  │ → Image 1    │  │ → Image 2    │  │ → Image 3    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│         PHASE 3: VIDEO GENERATION (ENHANCED MODELS)              │
│  Models: Hailuo (draft) | Kling 1.5 (standard) | Runway (final)│
│                                                                   │
│  Storyboard → Video Chunk (model preserves consistency)         │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
              FINAL VIDEO WITH CONSISTENT BRANDING
```

### **2.2 New Components**

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Asset Analysis** | GPT-4 Vision | Categorize and analyze uploads |
| **Embedding Generation** | CLIP (ViT-L/14) | Semantic vector representations |
| **Vector Search** | pgvector | Fast similarity search |
| **Edge Detection** | OpenCV Canny | ControlNet preprocessing |
| **Logo Detection** | CV2 + Heuristics | Identify logo assets |
| **Overlay Compositing** | Pillow (PIL) | Logo placement |
| **Image Gen (Enhanced)** | SDXL + ControlNet | Reference-guided storyboards |
| **Video Gen (New)** | Kling 1.5, Minimax | Better seed preservation |

---

## **3. Reference Asset Library**

### **3.1 Asset Types**

```python
class AssetType(str, enum.Enum):
    PRODUCT = "product"          # Physical products (shoes, watches, etc.)
    LOGO = "logo"                # Brand logos (transparent PNGs preferred)
    PERSON = "person"            # People/models for consistency
    ENVIRONMENT = "environment"  # Locations, settings, backgrounds
    TEXTURE = "texture"          # Materials, patterns, surfaces
    PROP = "prop"                # Objects, accessories
```

### **3.2 Database Schema**

```python
# File: backend/app/common/models.py

from sqlalchemy import Column, String, DateTime, JSON, Enum as SQLEnum, Boolean, Float, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.database import Base
import uuid

class ReferenceAsset(Base):
    """Reference asset for video generation"""
    __tablename__ = "reference_assets"
    
    # Primary
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    # Asset Info
    asset_type = Column(SQLEnum(AssetType), nullable=False, index=True)
    name = Column(String, nullable=False)  # User-defined name
    description = Column(String)  # Optional user description
    
    # Storage
    image_url = Column(String, nullable=False)  # S3 URL
    thumbnail_url = Column(String)  # Optimized thumbnail
    file_size_bytes = Column(Float)
    width = Column(Float)
    height = Column(Float)
    has_transparency = Column(Boolean, default=False)
    
    # AI Analysis (from GPT-4V)
    analysis = Column(JSON)  # Full GPT-4V response
    primary_object = Column(String, index=True)  # "Nike Air Max sneaker"
    colors = Column(ARRAY(String))  # ["white", "red", "black"]
    dominant_colors_rgb = Column(JSON)  # [[255,255,255], [220,20,60]]
    style_tags = Column(ARRAY(String), index=True)  # ["athletic", "modern", "clean"]
    recommended_shot_types = Column(ARRAY(String))  # ["close_up", "hero_shot"]
    usage_contexts = Column(ARRAY(String))  # ["product shots", "action scenes"]
    
    # Logo-specific
    is_logo = Column(Boolean, default=False, index=True)
    logo_position_preference = Column(String)  # "bottom-right", "top-left", etc.
    
    # Semantic Search
    embedding = Column(Vector(768))  # CLIP ViT-L/14 produces 768-dim vectors
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    usage_count = Column(Float, default=0)  # Track how often used
    
    # Indexing
    __table_args__ = (
        Index('idx_embedding_cosine', 'embedding', postgresql_using='ivfflat', 
              postgresql_with={'lists': 100}, postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )
```

### **3.3 Storage Structure**

```
S3 Bucket: video-gen-assets
├── reference-assets/
│   ├── {user_id}/
│   │   ├── {asset_id}/
│   │   │   ├── original.png          # Original upload
│   │   │   ├── thumbnail.jpg         # 400x400 thumbnail
│   │   │   ├── preprocessed/
│   │   │   │   ├── edges.png         # Canny edges for ControlNet
│   │   │   │   ├── depth.png         # Depth map (if needed)
```

---

## **4. AI Analysis & Categorization**

### **4.1 Analysis Pipeline**

```python
# File: backend/app/services/asset_analysis.py

from openai import OpenAI
from PIL import Image
import io
import base64

client = OpenAI()

async def analyze_reference_asset(
    image_url: str,
    user_provided_name: str = None,
    user_provided_description: str = None
) -> dict:
    """
    Analyze reference asset using GPT-4 Vision
    
    Returns:
        {
            "asset_type": "product",
            "primary_object": "Nike Air Max 270 sneaker",
            "colors": ["white", "black", "neon green"],
            "dominant_colors_rgb": [[255,255,255], [0,0,0], [57,255,20]],
            "style_tags": ["athletic", "modern", "sleek", "sporty"],
            "recommended_shot_types": ["close_up", "hero_shot", "detail_showcase", "product_in_motion"],
            "usage_contexts": ["product photography", "action scenes", "athletic content"],
            "is_logo": false,
            "has_text": false,
            "confidence": 0.92
        }
    """
    
    # Build analysis prompt
    system_prompt = """You are an expert visual analyst for advertising and video production. 
    Analyze the provided image and extract detailed information for video generation use cases.
    
    Focus on:
    - What is the PRIMARY object/subject?
    - What TYPE of asset is this? (product, logo, person, environment, texture, prop)
    - What are the dominant COLORS?
    - What STYLE/AESTHETIC does it convey?
    - What SHOT TYPES would work well with this asset?
    - In what CONTEXTS would this be used in video?
    - Is this a LOGO? (high contrast, simple shapes, brand identifier)
    
    Return a structured JSON response."""
    
    user_prompt = f"""Analyze this image for video production.
    
    User-provided context:
    - Name: {user_provided_name or 'Not provided'}
    - Description: {user_provided_description or 'Not provided'}
    
    Return JSON with this EXACT structure:
    {{
        "asset_type": "product|logo|person|environment|texture|prop",
        "primary_object": "detailed description of main subject",
        "colors": ["color1", "color2", "color3"],
        "style_tags": ["tag1", "tag2", "tag3"],
        "recommended_shot_types": ["shot_type1", "shot_type2"],
        "usage_contexts": ["context1", "context2"],
        "is_logo": true/false,
        "has_text": true/false,
        "confidence": 0.0-1.0
    }}
    
    Shot types vocabulary: close_up, medium, wide, extreme_close_up, hero_shot, detail_showcase, 
    lifestyle_context, action_shot, overhead, dramatic_angle, product_in_motion
    
    Be specific and detailed in descriptions."""
    
    # Call GPT-4 Vision
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=1000
    )
    
    analysis = json.loads(response.choices[0].message.content)
    
    # Extract dominant colors using CV2
    dominant_colors_rgb = extract_dominant_colors(image_url, n_colors=5)
    analysis['dominant_colors_rgb'] = dominant_colors_rgb
    
    return analysis


def extract_dominant_colors(image_url: str, n_colors: int = 5) -> list:
    """
    Extract dominant colors using K-means clustering
    No AI needed - pure computer vision
    """
    import cv2
    import numpy as np
    from sklearn.cluster import KMeans
    
    # Download and load image
    image = download_image(image_url)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Reshape to list of pixels
    pixels = image.reshape(-1, 3)
    
    # K-means clustering
    kmeans = KMeans(n_clusters=n_colors, random_state=42)
    kmeans.fit(pixels)
    
    # Get cluster centers (dominant colors)
    colors = kmeans.cluster_centers_.astype(int).tolist()
    
    return colors
```

### **4.2 Logo Detection**

```python
# File: backend/app/services/logo_detection.py

def detect_logo(image_path: str) -> dict:
    """
    Detect if image is a logo using heuristics (no AI needed)
    
    Returns:
        {
            "is_logo": true/false,
            "confidence": 0.0-1.0,
            "reasons": ["has transparency", "small size", "high contrast"]
        }
    """
    import cv2
    from PIL import Image
    
    img = Image.open(image_path)
    img_cv = cv2.imread(image_path)
    
    reasons = []
    score = 0.0
    
    # Check 1: Has transparency (alpha channel)
    if img.mode == 'RGBA':
        # Check if alpha channel is actually used
        alpha = np.array(img)[:, :, 3]
        if np.any(alpha < 255):
            score += 0.3
            reasons.append("has_transparency")
    
    # Check 2: Small file size relative to dimensions
    file_size = os.path.getsize(image_path)
    pixels = img.width * img.height
    bytes_per_pixel = file_size / pixels
    if bytes_per_pixel < 0.5:  # Very compressed = simple graphics
        score += 0.2
        reasons.append("simple_graphics")
    
    # Check 3: High contrast / Limited colors
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    unique_colors = len(np.unique(gray))
    if unique_colors < 50:  # Very limited palette
        score += 0.25
        reasons.append("limited_colors")
    
    # Check 4: Edge density (logos have crisp edges)
    edges = cv2.Canny(gray, 100, 200)
    edge_density = np.sum(edges > 0) / edges.size
    if edge_density > 0.1:  # High edge density
        score += 0.15
        reasons.append("crisp_edges")
    
    # Check 5: Aspect ratio (logos often square-ish)
    aspect_ratio = img.width / img.height
    if 0.5 < aspect_ratio < 2.0:
        score += 0.1
        reasons.append("logo_aspect_ratio")
    
    return {
        "is_logo": score > 0.5,
        "confidence": min(score, 1.0),
        "reasons": reasons
    }
```

### **4.3 Cost Analysis**

| Operation | Service | Cost | Frequency |
|-----------|---------|------|-----------|
| GPT-4V Analysis | OpenAI | $0.01-0.03 per image | Once per upload |
| CLIP Embedding | Local | $0.00 | Once per upload |
| Dominant Colors | OpenCV | $0.00 | Once per upload |
| Logo Detection | OpenCV | $0.00 | Once per upload |
| **Total per upload** | - | **$0.01-0.03** | One-time |

---

## **5. Semantic Search System**

### **5.1 CLIP Embedding Generation**

```python
# File: backend/app/services/clip_embeddings.py

import torch
import clip
from PIL import Image

# Load CLIP model once at startup
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-L/14", device=device)

def generate_image_embedding(image_path: str) -> list:
    """
    Generate CLIP embedding for image
    
    Returns:
        768-dimensional vector (list of floats)
    """
    image = Image.open(image_path)
    image_input = preprocess(image).unsqueeze(0).to(device)
    
    with torch.no_grad():
        embedding = model.encode_image(image_input)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)  # Normalize
    
    return embedding.cpu().numpy()[0].tolist()


def generate_text_embedding(text: str) -> list:
    """
    Generate CLIP embedding for text query
    
    Returns:
        768-dimensional vector (list of floats)
    """
    text_input = clip.tokenize([text]).to(device)
    
    with torch.no_grad():
        embedding = model.encode_text(text_input)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)  # Normalize
    
    return embedding.cpu().numpy()[0].tolist()
```

### **5.2 Semantic Search Use Cases**

#### **Use Case 1: Find Assets by Natural Language Query**

```python
# File: backend/app/services/asset_search.py

from sqlalchemy import func

def search_assets_by_text(
    user_id: str,
    query: str,
    asset_type: AssetType = None,
    limit: int = 10
) -> list[ReferenceAsset]:
    """
    Search reference assets using natural language
    
    Examples:
        - "red Nike sneaker"
        - "minimalist logo with transparency"
        - "urban street environment at night"
    """
    
    # Generate query embedding
    query_embedding = generate_text_embedding(query)
    
    # Base query
    db_query = db.query(ReferenceAsset).filter_by(user_id=user_id)
    
    # Filter by type if specified
    if asset_type:
        db_query = db_query.filter_by(asset_type=asset_type)
    
    # Order by cosine similarity
    results = db_query.order_by(
        ReferenceAsset.embedding.cosine_distance(query_embedding)
    ).limit(limit).all()
    
    # Add similarity scores
    for asset in results:
        asset.similarity_score = 1 - cosine_distance(
            query_embedding, 
            asset.embedding
        )
    
    return results
```

**Example Usage:**
```python
# User prompt: "energetic Nike sneaker ad, urban style"
assets = search_assets_by_text(
    user_id="user123",
    query="Nike sneaker urban athletic",
    asset_type=AssetType.PRODUCT,
    limit=5
)

# Returns: [Nike_AirMax.png (0.92), Nike_Pegasus.png (0.87), ...]
```

#### **Use Case 2: Find Similar Assets (Visual Similarity)**

```python
def find_similar_assets(
    reference_asset_id: str,
    limit: int = 10,
    exclude_self: bool = True
) -> list[ReferenceAsset]:
    """
    Find visually similar assets to a given reference
    
    Use cases:
        - "Show me similar products"
        - De-duplication detection
        - Style consistency recommendations
    """
    
    # Get reference asset
    reference = db.query(ReferenceAsset).get(reference_asset_id)
    
    # Search by embedding
    query = db.query(ReferenceAsset).filter_by(
        user_id=reference.user_id
    )
    
    if exclude_self:
        query = query.filter(ReferenceAsset.id != reference_asset_id)
    
    results = query.order_by(
        ReferenceAsset.embedding.cosine_distance(reference.embedding)
    ).limit(limit).all()
    
    return results
```

#### **Use Case 3: Beat-Specific Asset Matching**

```python
def find_assets_for_beat(
    user_id: str,
    beat: dict,
    product_hint: str = None,
    limit: int = 3
) -> dict:
    """
    Find most appropriate assets for a specific beat
    
    Considers:
        - Shot type compatibility
        - Beat action/mood
        - Product mention in prompt
    """
    
    # Compose search query from beat characteristics
    search_components = []
    
    if product_hint:
        search_components.append(product_hint)
    
    search_components.extend([
        beat['shot_type'],
        beat['action'],
        beat.get('mood', '')
    ])
    
    search_query = ' '.join(search_components)
    
    # Semantic search
    all_matches = search_assets_by_text(user_id, search_query, limit=20)
    
    # Filter by recommended shot types
    filtered_matches = [
        asset for asset in all_matches
        if beat['shot_type'] in asset.recommended_shot_types
    ]
    
    # Separate by asset type
    return {
        'product_refs': [a for a in filtered_matches if a.asset_type == AssetType.PRODUCT][:limit],
        'logo_refs': [a for a in filtered_matches if a.is_logo][:1],
        'environment_refs': [a for a in filtered_matches if a.asset_type == AssetType.ENVIRONMENT][:limit]
    }
```

#### **Use Case 4: De-duplication on Upload**

```python
def check_duplicate_asset(
    user_id: str,
    new_image_embedding: list,
    similarity_threshold: float = 0.95
) -> list[ReferenceAsset]:
    """
    Check if user is uploading a duplicate/very similar asset
    
    Returns potential duplicates above similarity threshold
    """
    
    existing_assets = db.query(ReferenceAsset).filter_by(
        user_id=user_id
    ).order_by(
        ReferenceAsset.embedding.cosine_distance(new_image_embedding)
    ).limit(5).all()
    
    # Filter by threshold
    duplicates = []
    for asset in existing_assets:
        similarity = 1 - cosine_distance(new_image_embedding, asset.embedding)
        if similarity > similarity_threshold:
            asset.similarity_score = similarity
            duplicates.append(asset)
    
    return duplicates
```

#### **Use Case 5: Style-Consistent Asset Recommendations**

```python
def recommend_style_consistent_assets(
    user_id: str,
    selected_asset_ids: list[str],
    limit: int = 10
) -> list[ReferenceAsset]:
    """
    Recommend additional assets that match the style of already-selected assets
    
    Use case: User selects Nike sneaker → recommend matching environments/props
    """
    
    # Get selected assets
    selected = db.query(ReferenceAsset).filter(
        ReferenceAsset.id.in_(selected_asset_ids)
    ).all()
    
    # Average their embeddings (centroid)
    avg_embedding = np.mean([asset.embedding for asset in selected], axis=0).tolist()
    
    # Find similar style assets (excluding already selected)
    recommendations = db.query(ReferenceAsset).filter(
        ReferenceAsset.user_id == user_id,
        ~ReferenceAsset.id.in_(selected_asset_ids)
    ).order_by(
        ReferenceAsset.embedding.cosine_distance(avg_embedding)
    ).limit(limit).all()
    
    return recommendations
```

### **5.3 PostgreSQL Setup**

```sql
-- Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create index for fast similarity search
CREATE INDEX ON reference_assets 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Example query (from SQLAlchemy ORM)
SELECT id, name, asset_type, 
       1 - (embedding <=> '[0.1, 0.2, ...]') AS similarity
FROM reference_assets
WHERE user_id = 'user123'
ORDER BY embedding <=> '[0.1, 0.2, ...]'
LIMIT 10;
```

---

## **6. Auto-Matching Logic**

### **6.1 Overview**

Automatically match reference assets to beats based on:
1. **Semantic similarity** (CLIP embeddings)
2. **Shot type compatibility** (from AI analysis)
3. **Asset type appropriateness** (products for product shots, etc.)
4. **User preferences** (usage count, recently uploaded)

### **6.2 Implementation**

```python
# File: backend/app/services/auto_matching.py

from app.services.asset_search import find_assets_for_beat
from app.services.openai import openai_client
import json

def auto_match_references(
    user_id: str,
    prompt: str,
    spec: dict
) -> dict:
    """
    Automatically match reference assets to each beat in the spec
    
    Returns:
        {
            "beat_id_1": {
                "product_refs": [ReferenceAsset],
                "logo_refs": [ReferenceAsset],
                "environment_refs": [ReferenceAsset],
                "confidence": 0.85
            },
            ...
        }
    """
    
    # Step 1: Extract product/brand entities from prompt
    entities = extract_entities_from_prompt(prompt)
    
    # Step 2: Get all user's reference assets
    user_assets = db.query(ReferenceAsset).filter_by(user_id=user_id).all()
    
    if not user_assets:
        # No assets to match
        return {}
    
    # Step 3: Match assets to each beat
    beat_reference_map = {}
    
    for beat in spec['beats']:
        # Find relevant assets for this beat
        matched_assets = find_assets_for_beat(
            user_id=user_id,
            beat=beat,
            product_hint=entities.get('product'),
            limit=3
        )
        
        # Calculate confidence score
        confidence = calculate_match_confidence(
            beat=beat,
            matched_assets=matched_assets,
            entities=entities
        )
        
        beat_reference_map[beat['beat_id']] = {
            **matched_assets,
            'confidence': confidence
        }
    
    return beat_reference_map


def extract_entities_from_prompt(prompt: str) -> dict:
    """
    Extract product/brand entities from user prompt using GPT-4
    
    Returns:
        {
            "product": "Nike sneakers",
            "brand": "Nike",
            "product_category": "footwear",
            "style_keywords": ["energetic", "urban"]
        }
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {
                "role": "system",
                "content": "Extract product and brand mentions from advertising prompts. Return JSON."
            },
            {
                "role": "user",
                "content": f"""Extract entities from this prompt:
                
                "{prompt}"
                
                Return JSON:
                {{
                    "product": "specific product mentioned",
                    "brand": "brand name",
                    "product_category": "general category",
                    "style_keywords": ["keyword1", "keyword2"]
                }}
                """
            }
        ],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def calculate_match_confidence(
    beat: dict,
    matched_assets: dict,
    entities: dict
) -> float:
    """
    Calculate confidence score for asset matching
    
    Score based on:
        - Asset found (0.3)
        - Shot type compatibility (0.3)
        - Semantic similarity (0.2)
        - Product name match (0.2)
    """
    
    score = 0.0
    
    # Check if we found any product assets
    if matched_assets.get('product_refs'):
        score += 0.3
        
        # Check shot type compatibility
        product_ref = matched_assets['product_refs'][0]
        if beat['shot_type'] in product_ref.recommended_shot_types:
            score += 0.3
        else:
            score += 0.1  # Partial credit
        
        # Semantic similarity (from search)
        if hasattr(product_ref, 'similarity_score'):
            score += product_ref.similarity_score * 0.2
        
        # Product name match
        if entities.get('product'):
            if entities['product'].lower() in product_ref.primary_object.lower():
                score += 0.2
    
    return min(score, 1.0)
```

### **6.3 Manual Override**

```python
# API endpoint for manual selection
@app.post("/api/videos/{video_id}/reference-mapping")
async def set_reference_mapping(
    video_id: str,
    beat_id: str,
    asset_ids: list[str]
):
    """
    Allow user to manually override auto-matched references
    """
    
    # Validate assets belong to user
    assets = db.query(ReferenceAsset).filter(
        ReferenceAsset.id.in_(asset_ids),
        ReferenceAsset.user_id == current_user.id
    ).all()
    
    # Store mapping
    mapping = {
        "beat_id": beat_id,
        "asset_ids": asset_ids,
        "manually_selected": True
    }
    
    # Update video generation record
    video.custom_reference_mapping = video.custom_reference_mapping or {}
    video.custom_reference_mapping[beat_id] = mapping
    db.commit()
    
    return {"success": True}
```

---

## **7. Enhanced Image Generation (Phase 2)**

### **7.1 ControlNet Integration**

```python
# File: backend/app/phases/phase2_storyboard/task.py

from app.services.controlnet import generate_with_controlnet, preprocess_for_controlnet

@celery_app.task(bind=True)
def generate_storyboard_with_references(
    self,
    video_id: str,
    spec: dict,
    reference_mapping: dict,
    quality_tier: str = "standard"
) -> dict:
    """
    Enhanced Phase 2: Generate storyboard with ControlNet + references
    """
    
    start_time = time.time()
    beats = spec['beats']
    
    logger.info(f"Phase 2 starting for video {video_id} (quality: {quality_tier})")
    logger.info(f"Reference mapping: {len(reference_mapping)} beats with assets")
    
    try:
        storyboard_images = []
        total_cost = 0.0
        
        for i, beat in enumerate(beats):
            logger.info(f"Generating storyboard {i+1}/{len(beats)}: {beat['beat_id']}")
            
            # Get references for this beat
            beat_refs = reference_mapping.get(beat['beat_id'], {})
            
            # Generate image with references
            image_url, cost, metadata = generate_beat_image_with_references(
                video_id=video_id,
                beat=beat,
                references=beat_refs,
                quality_tier=quality_tier
            )
            
            storyboard_images.append({
                "beat_id": beat['beat_id'],
                "beat_name": beat['name'],
                "start": beat['start'],
                "duration": beat['duration'],
                "image_url": image_url,
                "shot_type": beat['shot_type'],
                "references_used": {
                    "product": [r.id for r in beat_refs.get('product_refs', [])],
                    "logo": [r.id for r in beat_refs.get('logo_refs', [])]
                },
                "metadata": metadata
            })
            
            total_cost += cost
        
        logger.info(f"Phase 2 complete: {len(storyboard_images)} images, ${total_cost:.4f}")
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase2_storyboard",
            status="success",
            output_data={"storyboard_images": storyboard_images},
            cost_usd=total_cost,
            duration_seconds=time.time() - start_time
        ).dict()
        
    except Exception as e:
        logger.error(f"Phase 2 failed: {str(e)}")
        return PhaseOutput(
            video_id=video_id,
            phase="phase2_storyboard",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        ).dict()


def generate_beat_image_with_references(
    video_id: str,
    beat: dict,
    references: dict,
    quality_tier: str
) -> tuple[str, float, dict]:
    """
    Generate single storyboard image with ControlNet + references
    
    Returns:
        (image_url, cost, metadata)
    """
    
    product_refs = references.get('product_refs', [])
    logo_refs = references.get('logo_refs', [])
    
    # Select model based on quality tier
    config = IMAGE_GEN_CONFIGS[quality_tier]
    
    if not product_refs:
        # No references → fallback to regular SDXL
        logger.warning(f"No product references for beat {beat['beat_id']}, using standard generation")
        return generate_without_references(video_id, beat, config)
    
    # Primary product reference
    product_ref = product_refs[0]
    
    # Download reference image
    product_image_path = download_from_s3(product_ref.image_url)
    
    # Preprocess for ControlNet (extract edges)
    control_image_path = preprocess_for_controlnet(
        product_image_path,
        method="canny"  # Edge detection
    )
    
    # Generate with ControlNet
    logger.info(f"Generating with {config['model']}, product_ref: {product_ref.name}")
    
    generated_image = generate_with_controlnet(
        prompt=beat['prompt_template'],
        control_image_path=control_image_path,
        conditioning_scale=0.75,  # Balance between reference and creativity
        model=config['model'],
        width=1280,
        height=720
    )
    
    # Apply logo overlay if logo reference exists
    if logo_refs:
        logger.info(f"Applying logo overlay: {logo_refs[0].name}")
        generated_image = apply_logo_overlay(
            image=generated_image,
            logo_asset=logo_refs[0],
            beat_composition=beat['shot_type']
        )
    
    # Upload to S3
    s3_key = f"videos/{video_id}/storyboard/{beat['beat_id']}.png"
    final_url = s3_client.upload_pil_image(generated_image, s3_key)
    
    metadata = {
        "product_ref_used": product_ref.id,
        "product_ref_name": product_ref.name,
        "logo_applied": len(logo_refs) > 0,
        "conditioning_scale": 0.75,
        "model": config['model']
    }
    
    return (final_url, config['cost_per_image'], metadata)
```

### **7.2 ControlNet Preprocessing**

```python
# File: backend/app/services/controlnet.py

import cv2
import numpy as np
from PIL import Image

def preprocess_for_controlnet(
    image_path: str,
    method: str = "canny"
) -> str:
    """
    Preprocess reference image for ControlNet
    
    Methods:
        - canny: Edge detection (best for products)
        - depth: Depth estimation (for 3D objects)
        - hed: Holistically-nested edge detection (softer edges)
    """
    
    image = cv2.imread(image_path)
    
    if method == "canny":
        # Canny edge detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        
        # Convert to 3-channel for ControlNet
        control_image = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    elif method == "depth":
        # TODO: Use depth estimation model (MiDaS, etc.)
        pass
    
    elif method == "hed":
        # TODO: Use HED model
        pass
    
    # Save preprocessed image
    output_path = image_path.replace('.png', '_control.png')
    cv2.imwrite(output_path, control_image)
    
    return output_path


def generate_with_controlnet(
    prompt: str,
    control_image_path: str,
    conditioning_scale: float,
    model: str,
    width: int,
    height: int
) -> Image:
    """
    Generate image using SDXL + ControlNet
    """
    
    if model == "sdxl-controlnet":
        # Replicate SDXL ControlNet
        output = replicate.run(
            "lucataco/sdxl-controlnet:59df80a53d99e5b569f1d0d8aad0f33b03a56cd3cd0ef80e76e00fcf4d62c7b9",
            input={
                "prompt": prompt,
                "image": open(control_image_path, 'rb'),
                "conditioning_scale": conditioning_scale,
                "width": width,
                "height": height,
                "num_inference_steps": 30,
                "controlnet_type": "canny"
            }
        )
    
    elif model == "flux-pro":
        # Flux Pro with reference
        # Note: Flux Pro uses different API
        output = replicate.run(
            "black-forest-labs/flux-pro",
            input={
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "output_format": "png",
                "safety_tolerance": 2
            }
        )
    
    # Download result
    image_url = output if isinstance(output, str) else output[0]
    image_data = requests.get(image_url).content
    
    return Image.open(io.BytesIO(image_data))
```

---

## **8. Logo Overlay System**

### **8.1 Smart Logo Placement**

```python
# File: backend/app/services/logo_overlay.py

from PIL import Image, ImageDraw
import cv2
import numpy as np

def apply_logo_overlay(
    image: Image,
    logo_asset: ReferenceAsset,
    beat_composition: str,
    opacity: float = 0.95
) -> Image:
    """
    Apply logo overlay with smart positioning
    
    NO AI NEEDED - pure computer vision
    """
    
    # Download logo
    logo_path = download_from_s3(logo_asset.image_url)
    logo = Image.open(logo_path)
    
    # Ensure logo has alpha channel
    if logo.mode != 'RGBA':
        logo = logo.convert('RGBA')
    
    # Determine optimal position
    position = find_optimal_logo_position(
        base_image=image,
        logo=logo,
        composition=beat_composition,
        user_preference=logo_asset.logo_position_preference
    )
    
    # Scale logo if needed (max 15% of image width)
    max_logo_width = int(image.width * 0.15)
    if logo.width > max_logo_width:
        scale_factor = max_logo_width / logo.width
        new_size = (
            int(logo.width * scale_factor),
            int(logo.height * scale_factor)
        )
        logo = logo.resize(new_size, Image.Resampling.LANCZOS)
    
    # Apply opacity
    if opacity < 1.0:
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        logo.putalpha(alpha)
    
    # Composite logo onto image
    image = image.convert('RGBA')
    image.paste(logo, position, logo)
    
    return image.convert('RGB')


def find_optimal_logo_position(
    base_image: Image,
    logo: Image,
    composition: str,
    user_preference: str = None
) -> tuple[int, int]:
    """
    Find best position for logo that doesn't obscure important content
    
    Strategy:
        1. Use user preference if specified
        2. Otherwise, detect empty/simple areas in corners
        3. Fallback to bottom-right
    """
    
    # If user specified preference, use it
    if user_preference:
        return get_position_from_preference(
            base_image.size,
            logo.size,
            user_preference
        )
    
    # Convert to CV2 format
    img_cv = cv2.cvtColor(np.array(base_image), cv2.COLOR_RGB2BGR)
    
    # Define candidate positions (with padding)
    padding = 30
    candidates = [
        ("bottom-right", (base_image.width - logo.width - padding, 
                         base_image.height - logo.height - padding)),
        ("bottom-left", (padding, base_image.height - logo.height - padding)),
        ("top-right", (base_image.width - logo.width - padding, padding)),
        ("top-left", (padding, padding))
    ]
    
    # Score each position (prefer simpler/darker areas)
    best_position = None
    best_score = -1
    
    for name, (x, y) in candidates:
        # Extract region where logo would be placed
        region = img_cv[y:y+logo.height, x:x+logo.width]
        
        # Calculate simplicity score (lower variance = simpler = better)
        gray_region = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        variance = np.var(gray_region)
        score = 1 / (1 + variance)  # Invert so lower variance = higher score
        
        if score > best_score:
            best_score = score
            best_position = (x, y)
    
    return best_position


def get_position_from_preference(
    image_size: tuple,
    logo_size: tuple,
    preference: str
) -> tuple[int, int]:
    """
    Convert user preference to actual coordinates
    """
    
    width, height = image_size
    logo_w, logo_h = logo_size
    padding = 30
    
    positions = {
        "bottom-right": (width - logo_w - padding, height - logo_h - padding),
        "bottom-left": (padding, height - logo_h - padding),
        "top-right": (width - logo_w - padding, padding),
        "top-left": (padding, padding),
        "center": ((width - logo_w) // 2, (height - logo_h) // 2),
        "bottom-center": ((width - logo_w) // 2, height - logo_h - padding)
    }
    
    return positions.get(preference, positions["bottom-right"])
```

### **8.2 Logo in Videos**

```python
# File: backend/app/services/video_logo_overlay.py

def apply_logo_to_video(
    video_path: str,
    logo_asset: ReferenceAsset,
    output_path: str,
    position: str = "bottom-right",
    opacity: float = 0.9
) -> str:
    """
    Apply logo overlay to video file using FFmpeg
    
    Much faster than frame-by-frame processing
    """
    
    # Download logo
    logo_path = download_from_s3(logo_asset.image_url)
    
    # Calculate position (FFmpeg coordinates)
    # Note: FFmpeg uses (x,y) from top-left
    # "overlay=W-w-30:H-h-30" = bottom-right with 30px padding
    
    position_filters = {
        "bottom-right": "W-w-30:H-h-30",
        "bottom-left": "30:H-h-30",
        "top-right": "W-w-30:30",
        "top-left": "30:30"
    }
    
    overlay_pos = position_filters.get(position, position_filters["bottom-right"])
    
    # FFmpeg command
    ffmpeg_command = [
        'ffmpeg',
        '-i', video_path,
        '-i', logo_path,
        '-filter_complex',
        f'[1:v]format=rgba,colorchannelmixer=aa={opacity}[logo];'
        f'[0:v][logo]overlay={overlay_pos}',
        '-c:a', 'copy',  # Copy audio unchanged
        output_path
    ]
    
    ffmpeg_service.run_command(ffmpeg_command)
    
    return output_path
```

---

## **9. Enhanced Video Generation (Phase 3)**

### **9.1 Model Testing Plan**

```python
# File: backend/app/common/video_model_configs.py

VIDEO_GEN_CONFIGS = {
    "hailuo": {
        "replicate_model": "hailuo/video-v2.3-fast",
        "cost_per_5s": 0.04,
        "quality": "good",
        "speed": "fast",
        "reference_support": "image_only",
        "notes": "Current default, fast and cheap"
    },
    "kling-1.5": {
        "replicate_model": "kling/v1.5",
        "cost_per_5s": 0.12,
        "quality": "excellent",
        "speed": "medium",
        "reference_support": "image_text",
        "notes": "Better product preservation, worth testing"
    },
    "minimax": {
        "replicate_model": "minimax/video-01",
        "cost_per_5s": 0.15,
        "quality": "very_good",
        "speed": "medium",
        "reference_support": "image_text",
        "notes": "Good motion quality"
    },
    "runway-gen3": {
        "replicate_model": "runway/gen-3",
        "cost_per_5s": 0.50,
        "quality": "exceptional",
        "speed": "slow",
        "reference_support": "image_text",
        "notes": "Premium quality for finals"
    },
    "veo": {
        "api": "google_vertex",
        "cost_per_5s": 0.08,
        "quality": "very_good",
        "speed": "medium",
        "reference_support": "text_image",
        "notes": "Google's model, good for variety"
    }
}
```

### **9.2 Enhanced Chunk Generation**

```python
# File: backend/app/phases/phase3_chunks/task.py

@celery_app.task(bind=True)
def generate_chunks_enhanced(
    self,
    video_id: str,
    spec: dict,
    storyboard: dict,
    quality_tier: str = "standard"
) -> dict:
    """
    Enhanced Phase 3 with configurable video models
    """
    
    start_time = time.time()
    
    # Select model based on quality tier
    model_name = VIDEO_QUALITY_TIERS[quality_tier]
    model_config = VIDEO_GEN_CONFIGS[model_name]
    
    logger.info(f"Phase 3 starting with model: {model_name} (quality: {quality_tier})")
    
    try:
        chunks = []
        total_cost = 0.0
        
        storyboard_images = {
            img['beat_id']: img
            for img in storyboard['storyboard_images']
        }
        
        for beat in spec['beats']:
            num_chunks = beat['duration'] // 5
            
            for chunk_idx_in_beat in range(num_chunks):
                chunk_start = beat['start'] + (chunk_idx_in_beat * 5)
                global_chunk_idx = len(chunks)
                
                # Determine input image
                if chunk_idx_in_beat == 0:
                    input_image = storyboard_images[beat['beat_id']]['image_url']
                    input_type = "storyboard"
                else:
                    input_image = extract_last_frame(chunks[-1]['url'], video_id, global_chunk_idx)
                    input_type = "previous_frame"
                
                logger.info(f"Chunk {global_chunk_idx}: {model_name}, input={input_type}")
                
                # Generate chunk with selected model
                chunk_url = generate_video_chunk_with_model(
                    video_id=video_id,
                    chunk_idx=global_chunk_idx,
                    input_image=input_image,
                    model_name=model_name,
                    model_config=model_config,
                    beat_context=beat  # Pass beat for additional prompting
                )
                
                chunks.append({
                    "chunk_idx": global_chunk_idx,
                    "beat_id": beat['beat_id'],
                    "start": chunk_start,
                    "duration": 5,
                    "url": chunk_url,
                    "input_type": input_type,
                    "model_used": model_name
                })
                
                total_cost += model_config['cost_per_5s']
        
        logger.info(f"Phase 3 complete: {len(chunks)} chunks, ${total_cost:.2f}")
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase3_chunks",
            status="success",
            output_data={"chunks": chunks},
            cost_usd=total_cost,
            duration_seconds=time.time() - start_time
        ).dict()
        
    except Exception as e:
        logger.error(f"Phase 3 failed: {str(e)}")
        return PhaseOutput(
            video_id=video_id,
            phase="phase3_chunks",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        ).dict()


def generate_video_chunk_with_model(
    video_id: str,
    chunk_idx: int,
    input_image: str,
    model_name: str,
    model_config: dict,
    beat_context: dict = None
) -> str:
    """
    Generate video chunk with specified model
    """
    
    input_path = download_from_s3(input_image)
    
    # Some models support text prompts in addition to image
    text_prompt = None
    if model_config.get('reference_support') in ['image_text', 'text_image']:
        # Use beat's motion description for better results
        text_prompt = f"{beat_context.get('action', '')} {beat_context.get('camera_movement', '')}"
    
    logger.info(f"Generating with {model_name}, prompt: {text_prompt or 'N/A'}")
    
    with open(input_path, 'rb') as f:
        if model_name == "hailuo":
            output = replicate.run(
                model_config['replicate_model'],
                input={"image": f}
            )
        
        elif model_name in ["kling-1.5", "minimax"]:
            output = replicate.run(
                model_config['replicate_model'],
                input={
                    "image": f,
                    "prompt": text_prompt or "",
                    "duration": 5
                }
            )
        
        elif model_name == "runway-gen3":
            output = replicate.run(
                model_config['replicate_model'],
                input={
                    "prompt": text_prompt,
                    "image": f,
                    "duration": 5,
                    "watermark": False
                }
            )
        
        elif model_name == "veo":
            # Google Veo uses different API
            output = google_veo_client.generate(
                image=f,
                prompt=text_prompt,
                duration_seconds=5
            )
    
    # Download and upload to S3
    video_url = output if isinstance(output, str) else output[0]
    video_data = requests.get(video_url).content
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(video_data)
        tmp_path = tmp.name
    
    s3_key = f"videos/{video_id}/chunks/chunk_{chunk_idx:02d}.mp4"
    s3_url = s3_client.upload_file(tmp_path, s3_key)
    
    return s3_url
```

---

## **10. Model Configuration System**

### **10.1 Quality Tiers**

```python
# File: backend/app/common/quality_tiers.py

IMAGE_QUALITY_TIERS = {
    "draft": "sdxl",                    # Fast, no references
    "standard": "sdxl-controlnet",      # Good quality, references
    "final": "flux-pro"                 # Best quality, references
}

VIDEO_QUALITY_TIERS = {
    "draft": "hailuo",                  # Fast, cheap
    "standard": "kling-1.5",            # Good balance
    "final": "runway-gen3"              # Premium
}

QUALITY_TIER_COSTS = {
    "draft": {
        "image_per": 0.0055,
        "video_per_5s": 0.04,
        "estimated_15s": 0.14,          # 3 images + 3 chunks + planning + music
        "estimated_30s": 0.44           # 6 images + 6 chunks + planning + music
    },
    "standard": {
        "image_per": 0.010,
        "video_per_5s": 0.12,
        "estimated_15s": 0.58,
        "estimated_30s": 1.14
    },
    "final": {
        "image_per": 0.040,
        "video_per_5s": 0.50,
        "estimated_15s": 1.82,
        "estimated_30s": 3.62
    }
}
```

### **10.2 API Configuration**

```python
# File: backend/app/api/video_generation.py

from app.common.quality_tiers import QUALITY_TIER_COSTS

@app.post("/api/videos/generate")
async def generate_video(
    prompt: str,
    duration: int = 30,
    reference_asset_ids: list[str] = None,
    quality_tier: str = "standard",
    current_user: User = Depends(get_current_user)
):
    """
    Enhanced video generation endpoint with quality tiers
    """
    
    # Validate quality tier
    if quality_tier not in ["draft", "standard", "final"]:
        raise HTTPException(400, "Invalid quality_tier. Must be: draft, standard, or final")
    
    # Estimate cost
    if duration <= 15:
        estimated_cost = QUALITY_TIER_COSTS[quality_tier]["estimated_15s"]
    else:
        estimated_cost = QUALITY_TIER_COSTS[quality_tier]["estimated_30s"]
    
    # Check user balance/credits
    if current_user.credits < estimated_cost:
        raise HTTPException(402, f"Insufficient credits. Need ${estimated_cost:.2f}")
    
    # Create video generation record
    video = VideoGeneration(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        prompt=prompt,
        duration=duration,
        quality_tier=quality_tier,
        estimated_cost=estimated_cost,
        status=VideoStatus.QUEUED
    )
    db.add(video)
    db.commit()
    
    # Queue generation
    orchestrate_video_generation.delay(
        video_id=video.id,
        prompt=prompt,
        duration=duration,
        reference_asset_ids=reference_asset_ids or [],
        quality_tier=quality_tier
    )
    
    return {
        "video_id": video.id,
        "status": "queued",
        "estimated_cost": estimated_cost,
        "quality_tier": quality_tier
    }
```

---

## **11. Data Models**

### **11.1 Updated Video Generation Model**

```python
# File: backend/app/common/models.py

class VideoGeneration(Base):
    """Enhanced video generation with references"""
    __tablename__ = "video_generations"
    
    # ... existing fields ...
    
    # NEW: Reference assets
    reference_asset_ids = Column(ARRAY(String), default=list)
    reference_mapping = Column(JSON)  # Auto-matched references per beat
    custom_reference_mapping = Column(JSON)  # Manual overrides
    
    # NEW: Quality tier
    quality_tier = Column(String, default="standard")  # draft | standard | final
    
    # NEW: Model tracking
    image_model_used = Column(String)  # "sdxl-controlnet", "flux-pro", etc.
    video_model_used = Column(String)  # "hailuo", "kling-1.5", "runway-gen3", etc.
    
    # ... existing fields ...
```

### **11.2 Complete Schema**

```sql
-- Reference Assets Table
CREATE TABLE reference_assets (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    asset_type VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    
    -- Storage
    image_url VARCHAR NOT NULL,
    thumbnail_url VARCHAR,
    file_size_bytes FLOAT,
    width FLOAT,
    height FLOAT,
    has_transparency BOOLEAN DEFAULT false,
    
    -- AI Analysis
    analysis JSONB,
    primary_object VARCHAR,
    colors VARCHAR[],
    dominant_colors_rgb JSONB,
    style_tags VARCHAR[],
    recommended_shot_types VARCHAR[],
    usage_contexts VARCHAR[],
    
    -- Logo
    is_logo BOOLEAN DEFAULT false,
    logo_position_preference VARCHAR,
    
    -- Semantic Search
    embedding vector(768),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    usage_count FLOAT DEFAULT 0
);

CREATE INDEX idx_reference_assets_user_id ON reference_assets(user_id);
CREATE INDEX idx_reference_assets_asset_type ON reference_assets(asset_type);
CREATE INDEX idx_reference_assets_is_logo ON reference_assets(is_logo);
CREATE INDEX idx_reference_assets_embedding ON reference_assets 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Video Generations Table (Enhanced)
ALTER TABLE video_generations ADD COLUMN reference_asset_ids VARCHAR[];
ALTER TABLE video_generations ADD COLUMN reference_mapping JSONB;
ALTER TABLE video_generations ADD COLUMN custom_reference_mapping JSONB;
ALTER TABLE video_generations ADD COLUMN quality_tier VARCHAR DEFAULT 'standard';
ALTER TABLE video_generations ADD COLUMN image_model_used VARCHAR;
ALTER TABLE video_generations ADD COLUMN video_model_used VARCHAR;
```

---

## **12. Cost Analysis**

### **12.1 Per-Operation Costs**

| Operation | Service | Cost | When |
|-----------|---------|------|------|
| **Asset Upload** |
| GPT-4V Analysis | OpenAI | $0.01-0.03 | Once per upload |
| CLIP Embedding | Local | $0.00 | Once per upload |
| **Video Generation (15s, 3 beats)** |
| Phase 1: Planning | GPT-4 | $0.02 | Always |
| Phase 1: Auto-matching | Local | $0.00 | Always |
| Phase 2: SDXL | Replicate | 3 × $0.0055 = $0.0165 | Draft |
| Phase 2: SDXL + ControlNet | Replicate | 3 × $0.010 = $0.030 | Standard |
| Phase 2: Flux Pro | Replicate | 3 × $0.040 = $0.120 | Final |
| Phase 3: Hailuo | Replicate | 3 × $0.04 = $0.12 | Draft |
| Phase 3: Kling 1.5 | Replicate | 3 × $0.12 = $0.36 | Standard |
| Phase 3: Runway Gen-3 | Replicate | 3 × $0.50 = $1.50 | Final |
| Phase 4: Stitching | FFmpeg | $0.00 | Always |
| Phase 5: Music | MusicGen | $0.15 | Optional |

### **12.2 Total Cost Comparison (15s Video)**

| Tier | Image Gen | Video Gen | Other | **Total** |
|------|-----------|-----------|-------|-----------|
| **Draft** | $0.0165 | $0.12 | $0.17 | **$0.31** |
| **Standard** | $0.030 | $0.36 | $0.17 | **$0.56** |
| **Final** | $0.120 | $1.50 | $0.17 | **$1.79** |

### **12.3 Total Cost Comparison (30s Video)**

| Tier | Image Gen | Video Gen | Other | **Total** |
|------|-----------|-----------|-------|-----------|
| **Draft** | $0.033 | $0.24 | $0.17 | **$0.44** |
| **Standard** | $0.060 | $0.72 | $0.17 | **$0.95** |
| **Final** | $0.240 | $3.00 | $0.17 | **$3.41** |

---

## **13. Testing Strategy**

### **13.1 Reference Asset Library Tests**

```python
# File: backend/app/tests/test_reference_assets.py

def test_upload_and_analysis():
    """Test asset upload with GPT-4V analysis"""
    # Upload Nike sneaker image
    # Verify analysis returns correct asset_type=product
    # Verify primary_object contains "sneaker" or "shoe"
    # Verify colors extracted
    # Verify embedding generated (768 dimensions)

def test_logo_detection():
    """Test automatic logo detection"""
    # Upload Nike logo (transparent PNG)
    # Verify is_logo=True
    # Verify has_transparency=True

def test_duplicate_detection():
    """Test semantic search finds duplicates"""
    # Upload same image twice
    # Verify duplicate detection triggers

def test_semantic_search_text_query():
    """Test finding assets by text query"""
    # Upload several Nike products
    # Search "red athletic shoe"
    # Verify relevant results returned

def test_semantic_search_visual_similarity():
    """Test finding visually similar assets"""
    # Upload Nike Air Max 270
    # Search for similar
    # Verify other Nike shoes ranked higher than non-shoes
```

### **13.2 Auto-Matching Tests**

```python
def test_auto_match_single_product():
    """Test auto-matching with single product"""
    # User has 1 Nike sneaker in library
    # Prompt: "15s Nike ad"
    # Verify sneaker matched to all beats

def test_auto_match_multiple_products():
    """Test auto-matching with multiple products"""
    # User has 3 Nike shoes
    # Prompt: "15s Nike Air Max ad"
    # Verify Air Max specifically matched (not other shoes)

def test_auto_match_logo():
    """Test logo automatically matched"""
    # User has Nike logo
    # Verify logo matched to all beats with logo_refs

def test_auto_match_confidence_scores():
    """Test confidence scoring"""
    # Good match should have confidence > 0.7
    # Poor match should have confidence < 0.5

def test_manual_override():
    """Test manual reference selection overrides auto-match"""
    # Auto-match selects Product A
    # User manually selects Product B
    # Verify Product B used in generation
```

### **13.3 Image Generation Tests**

```python
def test_controlnet_product_consistency():
    """Test ControlNet maintains product across beats"""
    # Generate 3 storyboards with same product reference
    # Manually verify product looks similar (visual QA)
    # Ideally: Run CLIP similarity between products in images

def test_logo_overlay_positioning():
    """Test logo overlay placement"""
    # Generate storyboard
    # Apply logo overlay
    # Verify logo in correct position
    # Verify logo not obscuring product

def test_quality_tier_selection():
    """Test different quality tiers use correct models"""
    # Generate draft → verify SDXL used
    # Generate standard → verify SDXL + ControlNet used
    # Generate final → verify Flux Pro used
```

### **13.4 Integration Tests**

```python
def test_end_to_end_with_references():
    """Full pipeline with references"""
    # 1. Upload Nike sneaker + logo
    # 2. Generate 15s video
    # 3. Verify auto-matching worked
    # 4. Verify storyboards show consistent product
    # 5. Verify logo appears in all storyboards
    # 6. Verify video preserves consistency
    # 7. Verify cost within expected range

def test_end_to_end_no_references():
    """Full pipeline without references (fallback)"""
    # User has no assets
    # Generate 15s video
    # Verify pipeline completes successfully
    # Verify no errors from missing references
```

---

## **14. Implementation Roadmap**

### **14.1 Week 1: Reference Asset Library Foundation**

**Days 1-2: Database & Storage**
- [ ] Create `reference_assets` table with pgvector
- [ ] Set up S3 bucket structure
- [ ] Implement upload endpoint
- [ ] Add thumbnail generation

**Days 3-4: AI Analysis**
- [ ] Integrate GPT-4 Vision API
- [ ] Implement CLIP embedding generation
- [ ] Add dominant color extraction
- [ ] Implement logo detection heuristics

**Days 5-7: UI & Testing**
- [ ] Build asset library page (grid view)
- [ ] Add upload modal with drag-drop
- [ ] Display AI-analyzed tags
- [ ] Unit tests for analysis functions

**Deliverable:** Users can upload, view, and browse reference assets with AI analysis

---

### **14.2 Week 2: Semantic Search & Auto-Matching**

**Days 1-2: Semantic Search**
- [ ] Implement text-to-embedding search
- [ ] Implement image-to-image similarity search
- [ ] Add search API endpoints
- [ ] Test search accuracy

**Days 3-4: Auto-Matching Logic**
- [ ] Implement entity extraction from prompts
- [ ] Build beat-to-asset matching algorithm
- [ ] Add confidence scoring
- [ ] Test with various prompts

**Days 5-7: UI & Integration**
- [ ] Add search bar to asset library
- [ ] Show auto-matched assets in video generation UI
- [ ] Allow manual override
- [ ] Integration tests

**Deliverable:** Automatic reference selection based on video prompt

---

### **14.3 Week 3: ControlNet & Logo Overlay**

**Days 1-2: ControlNet Setup**
- [ ] Deploy SDXL + ControlNet on Replicate
- [ ] Implement edge detection preprocessing
- [ ] Test product consistency
- [ ] Benchmark vs. regular SDXL

**Days 3-4: Logo Overlay**
- [ ] Implement smart logo positioning
- [ ] Add opacity/scaling controls
- [ ] Test on various compositions
- [ ] Optimize placement algorithm

**Days 5-7: Phase 2 Integration**
- [ ] Update Phase 2 to use ControlNet + references
- [ ] Add logo overlay step
- [ ] End-to-end testing
- [ ] Visual QA of storyboards

**Deliverable:** Storyboard generation with consistent products + pixel-perfect logos

---

### **14.4 Week 4: Video Model Testing & Quality Tiers**

**Days 1-2: Model Testing**
- [ ] Test Kling 1.5 vs. Hailuo
- [ ] Test Minimax video quality
- [ ] Benchmark Runway Gen-3 (if budget allows)
- [ ] Compare product preservation across models

**Days 3-4: Quality Tier System**
- [ ] Implement tier configuration
- [ ] Add tier selection to API
- [ ] Update cost estimation
- [ ] Add tier badges in UI

**Days 5-7: Integration & Polish**
- [ ] Full pipeline test with all tiers
- [ ] Cost tracking and analytics
- [ ] Documentation
- [ ] Prepare demo videos

**Deliverable:** Complete reference-guided video generation with configurable quality

---

### **14.5 Week 5: Polish & Launch**

**Days 1-2: Bug Fixes**
- [ ] Fix issues found in testing
- [ ] Optimize slow operations
- [ ] Handle edge cases

**Days 3-4: Analytics & Monitoring**
- [ ] Track reference usage
- [ ] Monitor auto-match accuracy
- [ ] Cost dashboards
- [ ] Error alerting

**Days 5-7: Launch Prep**
- [ ] User documentation
- [ ] Demo videos
- [ ] Beta testing with select users
- [ ] Marketing materials

**Deliverable:** Production-ready reference asset system

---

## **15. Success Metrics**

### **15.1 Technical Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| AI Analysis Accuracy | >90% | Manual review of 100 uploads |
| Semantic Search Precision | >80% | Top-5 results relevant to query |
| Auto-Match Confidence | >75% | Average confidence score |
| Product Consistency (ControlNet) | >85% | CLIP similarity between beats |
| Logo Placement Success | 100% | Automated check (logo in bounds) |
| Generation Time (15s video) | <5 min | P95 latency |

### **15.2 Business Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| Reference Asset Uploads | 50%+ users | % users with ≥1 asset |
| Auto-Match Usage | 70%+ videos | % videos using references |
| Manual Override Rate | <30% | % times user changes auto-match |
| Quality Tier Distribution | 60% standard, 30% draft, 10% final | Video generation records |
| User Satisfaction | >4.0/5.0 | Post-generation survey |

---

## **Appendix A: Example Workflow**

### **User Journey:**

```
1. User uploads Nike Air Max 270 image
   → GPT-4V analyzes: "Nike Air Max 270 sneaker, white/red colorway, athletic style"
   → CLIP generates embedding
   → Detected as product (not logo)
   → Recommended shot types: [close_up, hero_shot, product_in_motion]

2. User uploads Nike Swoosh logo (transparent PNG)
   → GPT-4V analyzes: "Nike swoosh logo, black, iconic branding"
   → Logo detection: is_logo=True, has_transparency=True
   → User sets preference: logo_position_preference="bottom-right"

3. User creates video: "15s energetic Nike ad, urban rooftop"
   → Phase 1: Intent extraction finds "Nike"
   → Semantic search: "Nike athletic urban" → finds Air Max 270 (0.89 similarity)
   → Auto-match: All 3 beats get Air Max + Swoosh logo

4. Phase 2: Storyboard generation
   → Beat 1 (action_montage): ControlNet with Air Max edges → consistent product
   → Logo overlay applied to bottom-right
   → Beat 2 (product_in_motion): Same product, different angle
   → Beat 3 (call_to_action): Clean product shot with logo

5. Phase 3: Video generation (standard tier = Kling 1.5)
   → Storyboards already have consistent product + logo
   → Video model preserves what's there
   → Final chunks show recognizable Air Max 270 throughout

6. Result:
   → 15s video with consistent product across all shots
   → Perfect logo placement in all frames
   → Cost: $0.56 (standard tier)
   → Generation time: 4.5 minutes
```

---

**END OF TDD**

Ready to implement? Let me know when you want to start and which week/component to tackle first!
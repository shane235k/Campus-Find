"""Service module for AI Semantic Matching Engine.

Implements:
1. Sentence Transformers embedding generation (384 dimensions, all-MiniLM-L6-v2)
2. Text serialization and SHA-256 caching
3. Structured candidate filtering
4. Cosine similarity and pgvector integration
5. Hybrid composite scoring (Description 45%, Title 20%, Category 15%, Location 10%, Date 10%)
6. Human-readable explainable AI match reasoning
7. Bi-directional matching workflow (LOST <-> FOUND)
"""
import difflib
import hashlib
import logging
import math
from datetime import date
from typing import Dict, List, Optional, Tuple, Any

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from apps.items.models import Item
from .models import ItemEmbedding, PotentialMatch, MatchStatus

ItemType = Item.ItemType
ItemStatus = Item.ItemStatus

logger = logging.getLogger(__name__)

# Constants & Configuration
MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

WEIGHT_DESCRIPTION = 0.45
WEIGHT_TITLE = 0.20
WEIGHT_CATEGORY = 0.15
WEIGHT_LOCATION = 0.10
WEIGHT_DATE = 0.10

# In-memory cached model instance
_CACHED_MODEL = None
_MODEL_LOAD_ATTEMPTED = False
_MODEL_AVAILABLE = False
_MODEL_ERROR_MESSAGE = ""


def get_sentence_transformer_model():
    """Lazily load and cache the SentenceTransformer model in memory.
    
    Handles missing libraries, network boundaries, or disk cache errors gracefully.
    """
    global _CACHED_MODEL, _MODEL_LOAD_ATTEMPTED, _MODEL_AVAILABLE, _MODEL_ERROR_MESSAGE
    if _MODEL_LOAD_ATTEMPTED:
        return _CACHED_MODEL

    _MODEL_LOAD_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading SentenceTransformer model '{MODEL_NAME}'...")
        _CACHED_MODEL = SentenceTransformer(MODEL_NAME)
        _MODEL_AVAILABLE = True
        logger.info(f"SentenceTransformer '{MODEL_NAME}' successfully loaded and cached in process.")
    except Exception as exc:
        _MODEL_AVAILABLE = False
        _MODEL_ERROR_MESSAGE = str(exc)
        logger.warning(
            f"SentenceTransformer model '{MODEL_NAME}' is unavailable: {exc}. "
            "Semantic matching will fall back to deterministic token-vector representations."
        )
        _CACHED_MODEL = None

    return _CACHED_MODEL


def is_model_available() -> Tuple[bool, str]:
    """Check if the sentence transformer model is currently operational."""
    get_sentence_transformer_model()
    return _MODEL_AVAILABLE, _MODEL_ERROR_MESSAGE


def serialize_item_text(item: Item) -> Tuple[str, str]:
    """Build canonical narrative representation for embedding generation.
    
    Returns (serialized_text, sha256_hash).
    """
    category_name = item.category.name if item.category else "Uncategorized"
    location_name = item.location.name if item.location else "Campus"
    
    text = (
        f"Title: {item.title}. "
        f"Category: {category_name}. "
        f"Location: {location_name}. "
        f"Details: {item.description}"
    ).strip()
    
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return text, text_hash


def generate_embedding_vector(text: str) -> List[float]:
    """Generate normalized 384-dimensional vector embedding for the given text.
    
    If SentenceTransformer is available, generates deep semantic embedding.
    If unavailable due to network/environment limitations, produces a normalized
    hashed token-frequency projection of 384 dimensions to maintain vector algebra
    integrity without hardcoding arbitrary similarity scores.
    """
    model = get_sentence_transformer_model()
    if model is not None:
        try:
            # Model inference: encode returns numpy array
            vector = model.encode(text, normalize_embeddings=True)
            return vector.tolist()
        except Exception as exc:
            logger.error(f"Error during SentenceTransformer inference: {exc}")

    # Fallback deterministic pseudo-embedding (384 dimensions)
    # Uses modular hashing over character n-grams and tokens to generate
    # a dense vector, then L2-normalizes it.
    tokens = text.lower().split()
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for i, token in enumerate(tokens):
        # Primary token hash
        h1 = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % EMBEDDING_DIMENSIONS
        # Secondary bi-gram hash
        h2 = int(hashlib.sha1(f"{token}_{i}".encode("utf-8")).hexdigest(), 16) % EMBEDDING_DIMENSIONS
        vector[h1] += 1.0
        vector[h2] += 0.5

    # L2 Normalization
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0.0:
        vector = [x / norm for x in vector]
    else:
        vector[0] = 1.0

    return vector


def get_or_create_item_embedding(item: Item, force: bool = False) -> Optional[ItemEmbedding]:
    """Retrieve or generate embedding for an item.
    
    Skips generation if text_hash is unchanged, unless force=True.
    """
    text, text_hash = serialize_item_text(item)
    
    existing = ItemEmbedding.objects.filter(item=item).first()
    if existing and not force and existing.text_hash == text_hash:
        return existing

    try:
        vector = generate_embedding_vector(text)
        embedding_obj, _ = ItemEmbedding.objects.update_or_create(
            item=item,
            defaults={
                "embedding": vector,
                "model_name": MODEL_NAME if _MODEL_AVAILABLE else f"{MODEL_NAME}-fallback",
                "text_hash": text_hash,
            },
        )
        return embedding_obj
    except Exception as exc:
        logger.error(f"Failed to generate/save embedding for item {item.id}: {exc}")
        return None


def compute_vector_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two float vectors.
    
    Returns float clamped between 0.0 and 1.0.
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    similarity = dot / (norm1 * norm2)
    # Clamp cosine similarity from [-1.0, 1.0] to [0.0, 1.0]
    return max(0.0, min(1.0, float(similarity)))


def compute_title_similarity(title1: str, title2: str) -> float:
    """Calculate title similarity using SequenceMatcher and token Jaccard overlap.
    
    Handles word permutations (e.g. 'AirPods Pro' vs 'Pro AirPods').
    """
    if not title1 or not title2:
        return 0.0

    s1 = title1.strip().lower()
    s2 = title2.strip().lower()
    
    if s1 == s2:
        return 1.0

    # Sequence character ratio
    seq_ratio = difflib.SequenceMatcher(None, s1, s2).ratio()

    # Token-level Jaccard overlap
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    if tokens1 and tokens2:
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        jaccard = len(intersection) / len(union)
    else:
        jaccard = 0.0

    # Composite title similarity
    combined = (0.5 * seq_ratio) + (0.5 * jaccard)
    return max(0.0, min(1.0, round(combined, 4)))


def compute_category_score(cat1_id: Optional[int], cat2_id: Optional[int]) -> float:
    """Exact category match receives 1.0; mismatch receives 0.0."""
    if cat1_id is not None and cat2_id is not None and cat1_id == cat2_id:
        return 1.0
    return 0.0


def compute_location_score(loc1, loc2) -> float:
    """Calculate location proximity score based on campus buildings/names.
    
    - Same location ID: 1.0
    - Related location (shares common building keywords): 0.6
    - Otherwise: 0.0
    """
    if not loc1 or not loc2:
        return 0.0

    if loc1.id == loc2.id:
        return 1.0

    # Inspect names for shared building/area markers
    keywords = ["library", "hostel", "hall", "cafeteria", "sports", "lab", "auditorium", "center", "complex", "gate"]
    n1 = loc1.name.lower()
    n2 = loc2.name.lower()
    
    for kw in keywords:
        if kw in n1 and kw in n2:
            return 0.6

    return 0.0


def compute_date_score(d1: date, d2: date) -> float:
    """Calculate temporal proximity using exponential/linear decay formula.
    
    - Same day: 1.0
    - Within 1 day: 0.95
    - Within 3 days: 0.85
    - Within 7 days: 0.70
    - Within 14 days: 0.50
    - Within 30 days: linear decay to 0.05
    - Greater than 30 days: 0.0
    """
    if not d1 or not d2:
        return 0.0

    delta = abs((d1 - d2).days)
    if delta == 0:
        return 1.0
    elif delta <= 1:
        return 0.95
    elif delta <= 3:
        return 0.85
    elif delta <= 7:
        return 0.70
    elif delta <= 14:
        return 0.50
    elif delta <= 30:
        return max(0.05, round(1.0 - (delta / 30.0), 4))
    else:
        return 0.0


def compute_hybrid_match_score(
    desc_sim: float,
    title_sim: float,
    cat_score: float,
    loc_score: float,
    date_score: float,
) -> float:
    """Calculate weighted composite match score according to Phase 3 specification.
    
    Final Score = (Desc * 0.45) + (Title * 0.20) + (Category * 0.15) + (Loc * 0.10) + (Date * 0.10)
    All components in [0.0, 1.0].
    """
    final = (
        (desc_sim * WEIGHT_DESCRIPTION) +
        (title_sim * WEIGHT_TITLE) +
        (cat_score * WEIGHT_CATEGORY) +
        (loc_score * WEIGHT_LOCATION) +
        (date_score * WEIGHT_DATE)
    )
    return max(0.0, min(1.0, round(final, 4)))


def generate_match_explanation(
    lost_item: Item,
    found_item: Item,
    desc_sim: float,
    title_sim: float,
    cat_score: float,
    loc_score: float,
    date_score: float,
    final_score: float,
) -> str:
    """Generate explainable, human-readable match summary derived from actual scoring components."""
    pct = int(round(final_score * 100))
    if final_score >= 0.70:
        strength = f"Strong potential match ({pct}%)"
    elif final_score >= 0.45:
        strength = f"Moderate potential match ({pct}%)"
    else:
        strength = f"Possible partial match ({pct}%)"

    reasons = []
    
    # Description semantic similarity explanation
    if desc_sim >= 0.75:
        reasons.append("high semantic similarity in item descriptions")
    elif desc_sim >= 0.50:
        reasons.append("contextually aligned item descriptions")

    # Title similarity
    if title_sim >= 0.70:
        reasons.append(f"closely matching item names ('{lost_item.title}' vs '{found_item.title}')")
    elif title_sim >= 0.40:
        reasons.append("overlapping keywords in title")

    # Category
    if cat_score == 1.0 and lost_item.category:
        reasons.append(f"both classified under '{lost_item.category.name}'")

    # Location
    if loc_score == 1.0 and lost_item.location:
        reasons.append(f"reported at the identical campus location ({lost_item.location.name})")
    elif loc_score > 0.0 and lost_item.location and found_item.location:
        reasons.append(f"reported in related campus areas ({lost_item.location.name} and {found_item.location.name})")

    # Date
    delta = abs((lost_item.date_lost_or_found - found_item.date_lost_or_found).days)
    if delta == 0:
        reasons.append("occurred on the exact same date")
    elif delta <= 3:
        reasons.append(f"reported within {delta} day(s) of each other")
    elif delta <= 14:
        reasons.append(f"reported within two weeks ({delta} days apart)")

    if not reasons:
        reasons.append("general attribute correlation across campus reports")

    reasons_str = "; ".join(reasons)
    return (
        f"{strength} identified by AI matching engine because {reasons_str}. "
        "Ranking score is heuristic and does not constitute proof of ownership."
    )


def find_candidate_items(target_item: Item, max_candidates: int = 50) -> List[Item]:
    """Retrieve opposite-type candidate reports for comparison.
    
    Rules:
    - LOST compares only against FOUND.
    - FOUND compares only against LOST.
    - Excludes self.
    - Excludes RESOLVED and CLOSED items.
    """
    opposite_type = ItemType.FOUND if target_item.item_type == ItemType.LOST else ItemType.LOST
    
    queryset = (
        Item.objects.filter(item_type=opposite_type)
        .exclude(id=target_item.id)
        .exclude(status__in=[ItemStatus.RESOLVED, ItemStatus.CLOSED])
        .select_related("category", "location", "reported_by")
        .order_by("-created_at")[:max_candidates]
    )
    return list(queryset)


def find_and_generate_matches_for_item(
    target_item: Item,
    min_score: float = 0.35,
    max_results: int = 20,
) -> List[PotentialMatch]:
    """Execute end-to-end matching workflow for a target item.
    
    1. Ensures target item has an embedding.
    2. Identifies opposite-type active candidates.
    3. Retrieves or generates embeddings for candidates.
    4. Computes semantic description similarity and heuristic scores.
    5. Computes hybrid composite scores.
    6. Filters and ranks matches above min_score threshold.
    7. Atomically creates or updates PotentialMatch records.
    8. Returns the ordered list of PotentialMatch objects.
    """
    if target_item.status in [ItemStatus.RESOLVED, ItemStatus.CLOSED]:
        logger.info(f"Skipping match generation for inactive item {target_item.id} (status: {target_item.status})")
        return []

    target_embedding = get_or_create_item_embedding(target_item)
    candidates = find_candidate_items(target_item)
    if not candidates:
        return []

    generated_matches: List[PotentialMatch] = []

    for candidate in candidates:
        # Determine which item is LOST and which is FOUND
        if target_item.item_type == ItemType.LOST:
            lost_item, found_item = target_item, candidate
        else:
            lost_item, found_item = candidate, target_item

        # Retrieve candidate embedding
        candidate_embedding = get_or_create_item_embedding(candidate)

        # 1. Description Semantic Similarity
        if target_embedding and candidate_embedding:
            desc_sim = compute_vector_cosine_similarity(
                target_embedding.embedding,
                candidate_embedding.embedding,
            )
        else:
            # Fallback text similarity if embedding unavailable
            desc_sim = difflib.SequenceMatcher(
                None,
                target_item.description.lower(),
                candidate.description.lower(),
            ).ratio()

        # 2. Title Similarity
        title_sim = compute_title_similarity(target_item.title, candidate.title)

        # 3. Category Score
        cat_score = compute_category_score(
            target_item.category_id,
            candidate.category_id,
        )

        # 4. Location Proximity Score
        loc_score = compute_location_score(target_item.location, candidate.location)

        # 5. Date Proximity Score
        date_score = compute_date_score(
            target_item.date_lost_or_found,
            candidate.date_lost_or_found,
        )

        # Final Composite Score
        final_score = compute_hybrid_match_score(
            desc_sim=desc_sim,
            title_sim=title_sim,
            cat_score=cat_score,
            loc_score=loc_score,
            date_score=date_score,
        )

        if final_score < min_score:
            continue

        explanation = generate_match_explanation(
            lost_item=lost_item,
            found_item=found_item,
            desc_sim=desc_sim,
            title_sim=title_sim,
            cat_score=cat_score,
            loc_score=loc_score,
            date_score=date_score,
            final_score=final_score,
        )

        # Persist or update match record atomically
        with transaction.atomic():
            match_obj, created = PotentialMatch.objects.update_or_create(
                lost_item=lost_item,
                found_item=found_item,
                defaults={
                    "description_similarity": desc_sim,
                    "title_similarity": title_sim,
                    "category_score": cat_score,
                    "location_score": loc_score,
                    "date_score": date_score,
                    "final_score": final_score,
                    "explanation": explanation,
                },
            )
            generated_matches.append(match_obj)

    # Sort generated matches descending by final_score
    generated_matches.sort(key=lambda m: m.final_score, reverse=True)
    return generated_matches[:max_results]


def run_system_wide_matching(min_score: float = 0.35) -> Dict[str, Any]:
    """Execute platform-wide matching across all active LOST items."""
    open_lost_items = Item.objects.filter(
        item_type=ItemType.LOST,
        status__in=[ItemStatus.OPEN, ItemStatus.CLAIM_PENDING],
    )
    
    total_processed = 0
    total_matches_generated = 0

    for item in open_lost_items:
        matches = find_and_generate_matches_for_item(item, min_score=min_score)
        total_processed += 1
        total_matches_generated += len(matches)

    return {
        "processed_items": total_processed,
        "total_matches": total_matches_generated,
        "active_potential_matches": PotentialMatch.objects.count(),
        "timestamp": timezone.now().isoformat(),
    }

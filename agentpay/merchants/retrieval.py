import re
import json
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from agentpay.database.models import Product, Merchant

# Cache for the loaded model and vector embeddings
_EMBEDDER_INSTANCE = None
_CATALOG_VECTORS_CACHE = {}  # {tuple_of_product_ids: np.ndarray}


def get_embedder():
    """
    Singleton loader for semantic search engine.
    If LOW_MEMORY_MODE=true or running in cloud containers (e.g. Render free tier 512MB RAM),
    uses fast TF-IDF vectorizer (<25MB RAM).
    Otherwise, loads SentenceTransformers (all-MiniLM-L6-v2).
    """
    global _EMBEDDER_INSTANCE
    if _EMBEDDER_INSTANCE is None:
        import os
        # Automatically detect Render or memory-constrained container environments
        is_cloud_constrained = (
            os.getenv("LOW_MEMORY_MODE", "").lower() in ["true", "1", "yes"] or
            os.getenv("RENDER") is not None or
            os.getenv("RENDER_SERVICE_ID") is not None
        )
        if is_cloud_constrained:
            from sklearn.feature_extraction.text import TfidfVectorizer
            _EMBEDDER_INSTANCE = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            return _EMBEDDER_INSTANCE

        try:
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            from sentence_transformers import SentenceTransformer
            try:
                _EMBEDDER_INSTANCE = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
            except Exception:
                _EMBEDDER_INSTANCE = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            print(f"[SemanticSearch] Could not load SentenceTransformer: {e}. Falling back to TF-IDF vectorizer.")
            from sklearn.feature_extraction.text import TfidfVectorizer
            _EMBEDDER_INSTANCE = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    return _EMBEDDER_INSTANCE


class SemanticSearchEngine:
    """
    Hybrid Vector + Constraint-Aware Search Engine for Multi-Merchant Product Catalogs.
    Combines:
    1. 384-dimensional dense semantic vector similarity (SentenceTransformers all-MiniLM-L6-v2)
    2. Automatic query price ceiling/floor constraint detection & enforcement
    3. Category and brand affinity scoring
    4. Exact keyword & technical specification boosts
    """

    STOP_WORDS = {
        "find", "search", "show", "get", "buy", "me", "a", "an", "the", "for",
        "in", "with", "and", "or", "to", "of", "under", "below", "less", "than",
        "above", "over", "more", "budget", "need", "want", "good", "best", "top",
        "cheap", "expensive", "looking", "please", "can", "you", "i", "like"
    }

    @classmethod
    def _build_product_doc(cls, p: Product) -> str:
        specs_parts = []
        if hasattr(p, "specs") and p.specs:
            if isinstance(p.specs, dict):
                specs_parts = [f"{k.replace('_', ' ')}: {v}" for k, v in p.specs.items()]
            elif isinstance(p.specs, list):
                specs_parts = [str(x) for x in p.specs]
        specs_str = " | ".join(specs_parts)
        return (
            f"{p.name}. "
            f"Brand: {getattr(p, 'brand', '') or ''}. "
            f"Category: {p.category}. "
            f"Price: INR {p.price}. "
            f"{p.description or ''}. "
            f"Specs: {specs_str}"
        )

    @classmethod
    def extract_price_constraints(cls, query: str) -> Dict[str, Optional[float]]:
        """
        Extracts implicit or explicit price constraints from query text.
        e.g. 'headphones under 5000', 'monitor below 30k', 'above 1000'
        """
        max_price = None
        min_price = None
        q_lower = query.lower()

        # Match 'under/below/less than 5000' or '5k' or '5,000'
        max_match = re.search(
            r'(?:under|below|less than|within|budget of|max(?:imum)? of?|<=|<)\s*(?:₹|rs\.?|inr)?\s*([0-9,]+(?:\.[0-9]+)?)\s*(k|lakh)?',
            q_lower
        )
        if max_match:
            try:
                val = float(max_match.group(1).replace(",", ""))
                unit = (max_match.group(2) or "").lower()
                if unit == "k":
                    val *= 1000
                elif unit == "lakh":
                    val *= 100000
                max_price = val
            except Exception:
                pass

        # Match 'above/more than/at least 1000'
        min_match = re.search(
            r'(?:above|more than|at least|over|min(?:imum)? of?|>=|>)\s*(?:₹|rs\.?|inr)?\s*([0-9,]+(?:\.[0-9]+)?)\s*(k|lakh)?',
            q_lower
        )
        if min_match:
            try:
                val = float(min_match.group(1).replace(",", ""))
                unit = (min_match.group(2) or "").lower()
                if unit == "k":
                    val *= 1000
                elif unit == "lakh":
                    val *= 100000
                min_price = val
            except Exception:
                pass

        return {"max_price": max_price, "min_price": min_price}

    @classmethod
    def _detect_sub_type(cls, text: str) -> Optional[str]:
        t = text.lower()

        def has_word(words: List[str]) -> bool:
            return any(bool(re.search(rf'\b{re.escape(w)}\b', t)) for w in words)

        # 1. Wearables sub-types (checked before displays/screens because smartwatches have AMOLED screens)
        if has_word(["smartwatch", "smart watch", "apple watch", "galaxy watch", "pixel watch", "colorfit", "wave call", "watch"]):
            return "smartwatch"
        if has_word(["fitness band", "smart band", "activity tracker"]):
            return "fitness_band"

        # 2. Audio sub-types
        if has_word(["earbud", "earbuds", "tws", "airdopes", "airpod", "airpods", "in-ear", "in ear"]):
            return "earbuds"
        if has_word(["headphone", "headphones", "over-ear", "over ear", "on-ear", "on ear", "headset"]):
            return "headphones"
        if has_word(["microphone", "mic", "vocal mic", "sm7b"]):
            return "microphone"
        if has_word(["speaker", "speakers", "soundbar"]):
            return "speaker"

        # 3. Accessories sub-types
        if has_word(["mouse", "mice", "trackpad", "vertical mouse", "lift"]):
            return "mouse"
        if has_word(["keyboard", "keyboards", "mechanical keyboard"]):
            return "keyboard"
        if has_word(["webcam", "camera", "brio"]):
            return "webcam"
        if has_word(["charger", "charging station", "fast charger", "gan charger", "wall charger"]):
            return "charger"
        if has_word(["power bank", "powerbank", "battery pack"]):
            return "power_bank"
        if has_word(["dock", "docking station", "usb hub", "hub"]):
            return "dock"

        # 4. Displays sub-types
        if "portable" in t and has_word(["monitor", "display", "screen"]):
            return "portable_monitor"
        if has_word(["monitor", "monitors"]) or (has_word(["display", "screen"]) and not has_word(["tablet", "kindle", "paperwhite", "watch", "laptop"])):
            return "monitor"

        # 5. Electronics sub-types
        if has_word(["laptop", "laptops", "macbook", "notebook", "ultrabook"]):
            return "laptop"
        if has_word(["mini pc", "workstation", "minisforum", "desktop"]):
            return "desktop"
        if "raspberry pi" in t or "single board" in t:
            return "single_board"
        if has_word(["tablet", "ipad"]):
            return "tablet"

        # 6. Books sub-types
        if has_word(["kindle", "paperwhite", "scribe", "e-reader", "ereader", "remarkable"]):
            return "ereader"

        return None

    @classmethod
    def _detect_product_sub_type(cls, p: Product) -> Optional[str]:
        specs_text = json.dumps(p.specs) if hasattr(p, "specs") and p.specs else ""
        combined = f"{p.name} {getattr(p, 'brand', '')} {p.description or ''} {specs_text}"
        return cls._detect_sub_type(combined)

    @classmethod
    def _is_sub_type_conflict(cls, query_sub_type: str, prod_sub_type: Optional[str]) -> bool:
        if not query_sub_type or not prod_sub_type:
            return False
        if query_sub_type == prod_sub_type:
            return False
        # Audio family conflicts (e.g. earbuds requested, got over-ear headphones or microphone)
        audio_types = {"earbuds", "headphones", "microphone", "speaker"}
        if query_sub_type in audio_types and prod_sub_type in audio_types:
            return True
        # Accessories family conflicts (e.g. mouse requested, got webcam or keyboard or charger)
        acc_types = {"mouse", "keyboard", "webcam", "charger", "power_bank", "dock"}
        if query_sub_type in acc_types and prod_sub_type in acc_types:
            return True
        # Displays vs Computers
        if query_sub_type in {"monitor", "portable_monitor"} and prod_sub_type in {"laptop", "desktop"}:
            return True
        if query_sub_type in {"laptop", "desktop"} and prod_sub_type in {"monitor", "portable_monitor"}:
            return True
        # Wearables vs others
        wearable_types = {"smartwatch", "fitness_band"}
        if query_sub_type in wearable_types and prod_sub_type not in wearable_types:
            return True
        if prod_sub_type in wearable_types and query_sub_type not in wearable_types:
            return True
        return False

    @classmethod
    def search(
        cls,
        query: Optional[str] = None,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        brand: Optional[str] = None,
        feature_keywords: Optional[List[str]] = None,
        db: Session = None,
        top_k: int = 250
    ) -> List[Dict[str, Any]]:
        if db is None:
            return []

        # 1. Base Query with Active Merchants
        q = db.query(Product).join(Merchant).filter(Merchant.status == "ACTIVE")

        # Soft category filtering: only apply hard SQL filter if it matches active products
        if category:
            q_cat = q.filter(Product.category.ilike(f"%{category.strip()}%"))
            # If products exist in this category, filter; otherwise fall back to all active products
            if q_cat.first() is not None:
                q = q_cat

        if brand:
            q_brand = q.filter(Product.brand.ilike(f"%{brand.strip()}%"))
            if q_brand.first() is not None:
                q = q_brand

        products = q.all()
        if not products:
            # Fallback to all active products if filters were overly restrictive
            products = db.query(Product).join(Merchant).filter(Merchant.status == "ACTIVE").all()
            if not products:
                return []

        # 2. Extract implicit constraints from raw query string if not already supplied
        if query:
            implicit = cls.extract_price_constraints(query)
            if max_price is None and implicit["max_price"] is not None:
                max_price = implicit["max_price"]
            if min_price is None and implicit["min_price"] is not None:
                min_price = implicit["min_price"]

        # If no query and no features, return simple product list
        if not query and not feature_keywords:
            filtered = products
            if max_price is not None:
                filtered = [p for p in filtered if p.price <= max_price]
            if min_price is not None:
                filtered = [p for p in filtered if p.price >= min_price]
            return [cls._format_product(p, 1.0, []) for p in filtered[:top_k]]

        # Detect requested sub-type from the query text
        full_query = query or " ".join(feature_keywords or [])
        query_sub_type = cls._detect_sub_type(full_query)

        # 3. Dense Vector Embeddings
        embedder = get_embedder()
        query_for_embed = full_query
        if feature_keywords:
            query_for_embed += " " + " ".join(feature_keywords)

        cache_key = tuple(p.id for p in products)
        product_docs = [cls._build_product_doc(p) for p in products]

        is_transformer = hasattr(embedder, "encode")
        if is_transformer:
            # SentenceTransformers Dense Search with in-memory catalog vector caching
            if cache_key in _CATALOG_VECTORS_CACHE:
                product_vectors = _CATALOG_VECTORS_CACHE[cache_key]
            else:
                product_vectors = embedder.encode(product_docs, normalize_embeddings=True, show_progress_bar=False)
                _CATALOG_VECTORS_CACHE[cache_key] = product_vectors

            query_vector = embedder.encode([query_for_embed], normalize_embeddings=True, show_progress_bar=False)[0]
            vector_sims = np.dot(product_vectors, query_vector)
        else:
            # Fallback TF-IDF
            all_texts = product_docs + [query_for_embed]
            tfidf_matrix = embedder.fit_transform(all_texts)
            query_vec = tfidf_matrix[-1]
            prod_matrix = tfidf_matrix[:-1]
            from sklearn.metrics.pairwise import cosine_similarity
            vector_sims = cosine_similarity(prod_matrix, query_vec).flatten()

        # 4. Token Analysis & Feature Matches
        clean_tokens = []
        model_tokens = []
        if query:
            raw_tokens = re.findall(r'\b[a-zA-Z0-9-]+\b', query.lower())
            clean_tokens = [t for t in raw_tokens if t not in cls.STOP_WORDS and len(t) > 1]
            # Extract alphanumeric model tokens (e.g. 770nc, 550, 141, k2, xps15, g9, m27q, sm7b, 4k, 240hz, 32gb)
            model_tokens = [t for t in clean_tokens if re.search(r'[0-9]', t)]
        if feature_keywords:
            clean_tokens.extend([f.lower().strip() for f in feature_keywords])

        scored_results = []

        for idx, (p, sim) in enumerate(zip(products, vector_sims)):
            dense_score = float(sim)
            lexical_boost = 0.0
            matched_features = []

            name_lower = p.name.lower()
            desc_lower = (p.description or "").lower()
            brand_lower = (p.brand or "").lower()
            cat_lower = p.category.lower()
            specs_text = json.dumps(p.specs).lower() if hasattr(p, "specs") else ""
            prod_sub_type = cls._detect_product_sub_type(p)

            # A. Sub-Type Form-Factor Discriminator
            if query_sub_type:
                if prod_sub_type == query_sub_type:
                    lexical_boost += 0.35  # Major boost for matching exact requested form-factor
                    matched_features.append(f"Target Form-Factor: {query_sub_type.replace('_', ' ').title()}")
                elif cls._is_sub_type_conflict(query_sub_type, prod_sub_type):
                    lexical_boost -= 0.40  # Significant penalty for conflicting form-factor

            # B. Alphanumeric Model Code Exact Matching
            for m_tok in model_tokens:
                pattern = rf'\b{re.escape(m_tok)}\b'
                if re.search(pattern, name_lower) or re.search(pattern, p.id.lower()):
                    lexical_boost += 0.30
                    matched_features.append(f"Model Match: {m_tok.upper()}")
                elif re.search(pattern, specs_text):
                    lexical_boost += 0.25
                    matched_features.append(f"Spec Match: {m_tok.upper()}")
                elif re.search(pattern, desc_lower):
                    lexical_boost += 0.20
                    matched_features.append(f"Spec Match: {m_tok.upper()}")

            # C. Keyword Presence with word boundaries
            for token in clean_tokens:
                if token in model_tokens:
                    continue  # Already handled with high precision above
                pattern = rf'\b{re.escape(token)}\b'

                # Brand match (only boost brand if not in sub-type conflict)
                if re.search(pattern, brand_lower):
                    if query_sub_type and cls._is_sub_type_conflict(query_sub_type, prod_sub_type):
                        lexical_boost += 0.02  # Muted brand boost if form-factor conflicts
                    else:
                        lexical_boost += 0.18

                if re.search(pattern, name_lower):
                    lexical_boost += 0.14
                if re.search(pattern, cat_lower):
                    lexical_boost += 0.08
                if re.search(pattern, specs_text):
                    lexical_boost += 0.06
                    matched_features.append(token)
                elif re.search(pattern, desc_lower):
                    lexical_boost += 0.04

            # D. Domain Synergy Boosts
            q_lower = (query or "").lower()
            if any(k in q_lower for k in ["anc", "noise cancel", "noise-cancel"]):
                if "anc" in specs_text or "noise cancel" in desc_lower or "anc" in name_lower:
                    lexical_boost += 0.15
                    matched_features.append("Active Noise Cancellation")

            if any(k in q_lower for k in ["oled", "amoled"]):
                if "oled" in name_lower or "oled" in desc_lower or "amoled" in name_lower or "amoled" in desc_lower:
                    lexical_boost += 0.15
                    matched_features.append("OLED / AMOLED Display")

            if "vertical" in q_lower or "ergonomic" in q_lower:
                if "vertical" in name_lower or "ergonomic" in desc_lower or "vertical" in desc_lower:
                    lexical_boost += 0.15
                    matched_features.append("Ergonomic Vertical Design")

            if "mechanical" in q_lower:
                if "mechanical" in name_lower or "mechanical" in desc_lower:
                    lexical_boost += 0.15
                    matched_features.append("Mechanical Switches")

            if any(k in q_lower for k in ["4k", "uhd"]):
                if "4k" in name_lower or "4k" in specs_text or "uhd" in name_lower:
                    lexical_boost += 0.15
                    matched_features.append("4K UHD Resolution")

            # 5. Composite Base Score
            composite_score = dense_score + lexical_boost

            # 6. Strict Price Ceiling/Floor Constraints
            violates_budget = False
            if max_price is not None:
                if p.price > max_price:
                    violates_budget = True
                    composite_score -= 1.0  # Heavy penalty so items over budget never rank ahead of valid options
                else:
                    composite_score += 0.20  # Explicit reward for matching budget ceiling

            if min_price is not None:
                if p.price < min_price:
                    violates_budget = True
                    composite_score -= 0.5
                else:
                    composite_score += 0.10

            formatted = cls._format_product(p, composite_score, list(set(matched_features)), sub_type=prod_sub_type)
            formatted["similarity"] = round(dense_score, 4)
            formatted["violates_budget"] = violates_budget
            formatted["relevance_score"] = round(max(0.0, composite_score) * 100, 1)
            formatted["composite_score"] = composite_score
            scored_results.append(formatted)

        # 7. Sort: Valid budget first, then by composite_score descending, then break ties
        is_cheapest = any(k in clean_tokens for k in ["cheapest", "cheaper", "budget", "lowest", "low"])
        is_best = any(k in clean_tokens for k in ["best", "flagship", "top", "premium"])

        scored_results.sort(key=lambda item: (
            not item["violates_budget"],
            round(item["composite_score"], 2),
            item["price"] if is_best else (-item["price"] if is_cheapest else getattr(item, "rating", 4.5))
        ), reverse=True)

        return scored_results[:top_k]

    @classmethod
    def _format_product(cls, p: Product, score: float, matched_features: List[str], sub_type: Optional[str] = None) -> Dict[str, Any]:
        return {
            "id": p.id,
            "merchant_id": p.merchant_id,
            "merchant_name": p.merchant.name if p.merchant else "OmniTech India",
            "name": p.name,
            "brand": getattr(p, "brand", ""),
            "description": p.description,
            "category": p.category,
            "sub_type": sub_type or cls._detect_product_sub_type(p),
            "price": p.price,
            "currency": p.currency,
            "stock": p.stock,
            "rating": getattr(p, "rating", 4.8),
            "specs": p.specs if hasattr(p, "specs") else {},
            "in_stock": p.stock > 0,
            "matched_features": matched_features,
            "relevance_score": round(score * 100, 1)
        }

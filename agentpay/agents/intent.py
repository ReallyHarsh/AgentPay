import re
from typing import Dict, Any, Optional, List


class IntentAgent:
    """
    Sub-Agent 1: Intent Agent
    Responsible for deconstructing user requests into structured e-commerce parameters.
    Keeps the user in the loop by default by detecting underspecified goals, formulating
    clarifying questions, identifying choice dimensions, and only enabling autonomous direct
    checkout when explicitly instructed by the user.
    """

    @staticmethod
    def parse_intent(user_message: str) -> Dict[str, Any]:
        msg_lower = user_message.lower().strip()

        # 1. Autonomy vs Human-in-the-Loop Mode
        autonomous_mode = any(
            w in msg_lower
            for w in [
                "auto-buy", "autobuy", "auto buy", "buy immediately",
                "buy now without asking", "skip confirmation", "autonomous",
                "execute directly without asking", "auto purchase", "direct checkout"
            ]
        )

        # 2. Price Ceiling & Floor
        max_price: Optional[float] = None
        min_price: Optional[float] = None

        price_match = re.search(
            r'(?:under|below|less than|within|<=|<|budget(?: of)?)\s*(?:₹|rs\.?|inr)?\s*([0-9,]+)',
            msg_lower
        )
        if price_match:
            try:
                max_price = float(price_match.group(1).replace(",", ""))
            except Exception:
                max_price = None

        min_match = re.search(
            r'(?:above|more than|at least|>=|>)\s*(?:₹|rs\.?|inr)?\s*([0-9,]+)',
            msg_lower
        )
        if min_match:
            try:
                min_price = float(min_match.group(1).replace(",", ""))
            except Exception:
                min_price = None

        # Helper for whole-word boundary matching
        def word_match(keywords: List[str]) -> bool:
            return any(bool(re.search(rf'\b{re.escape(k)}\b', msg_lower)) for k in keywords)

        # 3. Product Sub-Type / Form-Factor Detection
        detected_sub_type: Optional[str] = None
        # Audio sub-types
        if word_match(["earbud", "earbuds", "tws", "airdopes", "airpod", "airpods", "in-ear", "in ear"]):
            detected_sub_type = "earbuds"
        elif word_match(["headphone", "headphones", "over-ear", "over ear", "on-ear", "on ear", "headset"]):
            detected_sub_type = "headphones"
        elif word_match(["microphone", "mic", "vocal mic", "sm7b"]):
            detected_sub_type = "microphone"
        elif word_match(["speaker", "speakers", "soundbar"]):
            detected_sub_type = "speaker"
        # Accessories sub-types
        elif word_match(["mouse", "mice", "trackpad", "vertical mouse"]):
            detected_sub_type = "mouse"
        elif word_match(["keyboard", "keyboards", "mechanical keyboard"]):
            detected_sub_type = "keyboard"
        elif word_match(["webcam", "camera", "brio"]):
            detected_sub_type = "webcam"
        elif word_match(["charger", "fast charger", "gan charger", "wall charger"]):
            detected_sub_type = "charger"
        elif word_match(["power bank", "powerbank", "battery pack"]):
            detected_sub_type = "power_bank"
        elif word_match(["dock", "docking station", "hub", "usb hub"]):
            detected_sub_type = "dock"
        # Displays sub-types
        elif word_match(["portable monitor", "portable display", "zenscreen"]):
            detected_sub_type = "portable_monitor"
        elif word_match(["monitor", "monitors", "display", "displays", "screen", "screens"]):
            detected_sub_type = "monitor"
        # Electronics sub-types
        elif word_match(["laptop", "laptops", "macbook", "notebook", "ultrabook"]):
            detected_sub_type = "laptop"
        elif word_match(["desktop", "workstation", "mini pc", "minisforum"]):
            detected_sub_type = "desktop"
        elif word_match(["raspberry pi", "single board"]):
            detected_sub_type = "single_board"
        elif word_match(["tablet", "ipad"]):
            detected_sub_type = "tablet"
        # Wearables sub-types
        elif word_match(["smartwatch", "smart watch", "apple watch", "galaxy watch", "pixel watch"]):
            detected_sub_type = "smartwatch"
        elif word_match(["fitness band", "smart band", "activity tracker"]):
            detected_sub_type = "fitness_band"
        # Books sub-types
        elif word_match(["kindle", "paperwhite", "scribe", "e-reader", "ereader", "remarkable"]):
            detected_sub_type = "ereader"

        # 4. Category Detection (inferred from sub_type or keywords)
        detected_category: Optional[str] = None
        if detected_sub_type in ("earbuds", "headphones", "microphone", "speaker") or word_match(["audio", "music", "anc"]):
            detected_category = "audio"
        elif detected_sub_type in ("mouse", "keyboard", "webcam", "charger", "power_bank", "dock") or word_match(["accessories", "cable"]):
            detected_category = "accessories"
        elif detected_sub_type in ("monitor", "portable_monitor") or word_match(["displays", "screen", "4k monitor", "ultrawide"]):
            detected_category = "displays"
        elif detected_sub_type in ("laptop", "desktop", "single_board", "tablet") or word_match(["computer", "computers"]):
            detected_category = "electronics"
        elif detected_sub_type in ("smartwatch", "fitness_band") or word_match(["wearable", "wearables", "smartwatch", "watch"]):
            detected_category = "wearables"
        elif word_match(["desk", "desk mat", "screenbar", "stream deck", "office chair", "monitor arm"]):
            detected_category = "office"
        elif detected_sub_type == "ereader" or word_match(["book", "books", "e-ink"]):
            detected_category = "books"

        # 5. Merchant Preference Detection
        preferred_merchant_id: Optional[str] = None
        if word_match(["croma"]):
            preferred_merchant_id = "merchant_001"
        elif word_match(["reliance"]):
            preferred_merchant_id = "merchant_002"
        elif word_match(["amazon"]):
            preferred_merchant_id = "merchant_003"

        # 6. Brand Detection with word boundaries
        extracted_brand: Optional[str] = None
        known_brands = [
            "sony", "apple", "dell", "bose", "jbl", "boat", "logitech",
            "anker", "keychron", "asus", "lenovo", "lg", "samsung",
            "sandisk", "benq", "elgato", "amazon", "remarkable", "shure",
            "baseus", "caldigit", "gigabyte", "onyx boox", "minisforum",
            "noise", "oneplus", "nothing", "realme", "xiaomi",
            "razer", "sennheiser", "audio-technica", "belkin", "rode", "fifine",
            "marshall", "garmin", "amazfit", "fitbit", "viewsonic", "kobo",
            "sihoo", "grovemade", "hp", "intel", "beelink", "redragon", "arzopa"
        ]
        for b in known_brands:
            if b == "noise" and any(k in msg_lower for k in ["noise cancel", "noise-cancel", "noise cancelling", "noise cancellation", "noise reduction", "noise isolation"]):
                if not re.search(r'\bnoise\s+(colorfit|icon|pulse|crew|vibe|fit|smartwatch|watch|brand)\b', msg_lower) and not re.search(r'\bbrand\s+noise\b', msg_lower):
                    continue
            if bool(re.search(rf'\b{re.escape(b)}\b', msg_lower)):
                extracted_brand = b.capitalize()
                break

        # 7. Feature Keywords Extraction with word boundaries
        feature_keywords: List[str] = []
        if word_match(["anc", "noise cancel", "noise-cancel", "noise cancelling"]):
            feature_keywords.append("anc")
        if word_match(["vertical", "ergonomic"]):
            feature_keywords.extend(["vertical", "ergonomic"])
        if word_match(["mechanical"]):
            feature_keywords.append("mechanical")
        if word_match(["oled", "amoled"]):
            feature_keywords.append("oled")
        if word_match(["4k", "uhd"]):
            feature_keywords.append("4k")
        if word_match(["usb-c", "type-c", "usbc", "thunderbolt"]):
            feature_keywords.append("usb-c")
        if word_match(["waterproof", "water resistant", "ipx", "ip54", "ip65", "ip68", "5atm"]):
            feature_keywords.append("waterproof")
        if word_match(["32gb", "16gb", "64gb", "ram"]):
            feature_keywords.append("ram")
        if word_match(["1tb", "2tb", "512gb", "ssd"]):
            feature_keywords.append("ssd")
        if word_match(["warranty", "extended warranty", "2-year", "2 year"]):
            feature_keywords.append("warranty")

        # 8. Clean Query Keyword (Strip intent verbs and price triggers, but PRESERVE model numbers & specs)
        # First remove explicit price clauses (e.g. 'under 5000', 'below ₹30,000')
        query_text = re.sub(r'(?:under|below|less than|within|above|more than|at least|budget(?: of)?)\s*(?:₹|rs\.?|inr)?\s*[0-9,]+(?:\.[0-9]+)?\s*(?:k|lakh)?', '', msg_lower)
        query_text = re.sub(r'(?:₹|rs\.?|inr)\s*[0-9,]+(?:\.[0-9]+)?', '', query_text)

        # Remove filler command words and stop words, but PRESERVE alphanumeric tokens like 770nc, 550, 141, k2, xps15, 4k
        clean_query = re.sub(
            r'\b(buy|purchase|find|search|get|order|for me|for|me|some|the|a|an|good|best|cheapest|deal|switch to|prefer|confirm|checkout|pay|authorize|auto-buy|autobuy|auto buy|immediately|without asking|show|recommend|suggest|looking|want|need|i|any)\b',
            '',
            query_text
        )
        clean_query = re.sub(r'\s+', ' ', clean_query).strip()

        if not clean_query:
            clean_query = detected_sub_type or detected_category or "electronics"

        # 9. Action Intent
        is_buy_command = any(
            w in msg_lower
            for w in ["buy", "purchase", "order", "get me", "checkout", "procure", "acquire", "confirm", "proceed", "pay", "authorize"]
        )

        # 10. Clarifying Questions & Interactive Options Generation
        # Trigger clarification ONLY if query is truly broad (no budget, no brand, no specific sub-type, no features)
        needs_clarification = False
        clarifying_question: Optional[str] = None
        clarification_options: List[Dict[str, str]] = []

        is_broad = (
            max_price is None
            and not extracted_brand
            and len(feature_keywords) == 0
            and not autonomous_mode
            and not is_buy_command
            and (
                not detected_sub_type
                or detected_sub_type in ("headphones", "monitor", "laptop", "smartwatch")
            )
            and clean_query in (
                "headphones", "headphone", "audio", "earphones", "earphone",
                "monitor", "monitors", "display", "displays", "screen", "screens",
                "laptop", "laptops", "computer", "computers",
                "accessories", "books", "book",
                "smartwatch", "smartwatches", "watch", "watches", "wearable", "wearables"
            )
        )

        if is_broad and detected_category:
            needs_clarification = True
            if detected_sub_type == "mouse":
                clarifying_question = "What type of mouse do you prefer?"
                clarification_options = [
                    {"label": "🖱️ Ergonomic Vertical Mouse (Logitech Lift)", "prompt": "Show ergonomic vertical mouse"},
                    {"label": "🖱️ Precision Productivity Mouse (Logitech MX Master 3S)", "prompt": "Show Logitech MX Master 3S mouse"}
                ]
            elif detected_category == "audio":
                clarifying_question = "What form-factor and listening preference do you have?"
                clarification_options = [
                    {"label": "🎧 Over-Ear ANC Headphones (₹4.3k - ₹26.9k)", "prompt": "Show over-ear headphones with active noise cancellation"},
                    {"label": "🎵 True Wireless Earbuds (₹1.2k - ₹22.9k)", "prompt": "Show true wireless earbuds with ANC"},
                    {"label": "🎙️ Studio Vocal Microphone (₹34.5k)", "prompt": "Show professional studio microphones"}
                ]
            elif detected_category == "displays":
                clarifying_question = "What primary display capability do you need?"
                clarification_options = [
                    {"label": "🖥️ 4K UHD with 96W USB-C Hub (₹27.4k - ₹48.5k)", "prompt": "Show 27-inch 4K UHD monitors with USB-C power delivery"},
                    {"label": "⚡ 240Hz OLED Gaming Monitor (₹78.9k)", "prompt": "Show 240Hz OLED gaming monitors"},
                    {"label": "📱 15.6\" Portable USB-C Display (₹16.9k)", "prompt": "Show portable USB-C monitors"}
                ]
            elif detected_category == "electronics":
                clarifying_question = "What compute workflow or form-factor do you need?"
                clarification_options = [
                    {"label": "💻 MacBook Air/Pro with Apple M3 (₹114k+)", "prompt": "Show Apple MacBook M3 laptops"},
                    {"label": "⚡ High Performance OLED Workstation (32GB RAM)", "prompt": "Show high performance laptop with 32GB RAM and OLED"},
                    {"label": "🥧 Raspberry Pi 5 8GB / Mini PC (₹7.4k - ₹56.9k)", "prompt": "Show Raspberry Pi 5 single board computers and mini PCs"}
                ]
            elif detected_category == "accessories":
                clarifying_question = "Which desk peripheral are you looking to add?"
                clarification_options = [
                    {"label": "🖱️ Ergonomic / Productivity Mouse (₹5.4k - ₹8.9k)", "prompt": "Show ergonomic and vertical productivity mice"},
                    {"label": "⌨️ Custom Mechanical Keyboard (₹8.4k - ₹17.9k)", "prompt": "Show wireless mechanical keyboards with hot-swappable switches"},
                    {"label": "⚡ 140W GaN Fast Charger / Power Bank", "prompt": "Show GaN fast chargers and high capacity power banks"}
                ]
            elif detected_category == "wearables":
                clarifying_question = "What wearable device or ecosystem are you looking for?"
                clarification_options = [
                    {"label": "⌚ Premium Smartwatch (Apple Watch / Galaxy Watch)", "prompt": "Show premium smartwatches"},
                    {"label": "🏃 Fitness Smartwatch with AMOLED under ₹5,000", "prompt": "Show smartwatches under 5000"},
                    {"label": "⚡ Long Battery Smartwatch with GPS", "prompt": "Show smartwatches with long battery life"}
                ]
            elif detected_category == "books":
                clarifying_question = "What digital reading or note-taking experience do you want?"
                clarification_options = [
                    {"label": "📖 6.8\" Glare-Free Paperwhite (₹14.4k - ₹14.9k)", "prompt": "Show Kindle Paperwhite e-readers"},
                    {"label": "✍️ 10.2\" Digital Notebook & Pen (₹36.9k - ₹39.9k)", "prompt": "Show Kindle Scribe and reMarkable 2 paper tablets"},
                    {"label": "🌈 Color E-Ink Android Tablet (₹49.9k)", "prompt": "Show color e-ink Android tablets with stylus"}
                ]

        return {
            "clean_query": clean_query,
            "category": detected_category,
            "sub_type": detected_sub_type,
            "max_price": max_price,
            "min_price": min_price,
            "brand": extracted_brand,
            "preferred_merchant_id": preferred_merchant_id,
            "feature_keywords": list(set(feature_keywords)),
            "is_buy_command": is_buy_command,
            "autonomous_mode": autonomous_mode,
            "needs_clarification": needs_clarification,
            "clarifying_question": clarifying_question,
            "clarification_options": clarification_options,
            "prefer_best": "best" in msg_lower or "flagship" in msg_lower or "top" in msg_lower,
            "prefer_cheapest": "cheapest" in msg_lower or "budget" in msg_lower or "lowest" in msg_lower or "cheaper" in msg_lower
        }

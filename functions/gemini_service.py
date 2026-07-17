"""Gemini GenAI service wrapper for FanPath AI.

Handles API connections using the google-genai SDK, implements a 5-minute
query/history cache, and handles static query short-circuiting to reduce costs.
"""

import time
import logging
from typing import Any, Union
from google import genai
from google.genai import types
import config

# Logger configuration
logger = logging.getLogger("fanpath.gemini_service")
logger.setLevel(logging.INFO)

# In-memory query response cache
# Format: { (message_text, tuple_of_history): (response_text, cache_timestamp) }
_response_cache: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[str, float]] = {}

# Static redirection answers for simple navigational/logistical lookups
# Prevents outbound API calls for simple fixed knowledge points
STATIC_ANSWERS: dict[str, dict[str, str]] = {
    "en": {
        "gate a": "🚪 **Gate A (North Entrance):** Close to VIP Parking Lot 1, Taxi stands, and NJ Transit train station. Best for sections 101-110.",
        "gate b": "🚪 **Gate B (South Entrance):** Near Lot 2 and Regional Bus Depot. Best for sections 115-125.",
        "gate c": "🚪 **Gate C (East Entrance):** Next to Rideshare zone in Lot E. Best for sections 126-135.",
        "gate d": "♿ **Gate D (West Entrance - Accessible):** Fully accessibility-friendly with low counters, wide lanes, and elevators. Closest to Parking Lot 3.",
        "metro": "🚆 **Transportation Info:** NJ Transit trains arrive directly at the stadium station outside Gate A. Bus shuttles run from Lot B. Rideshare pickup is in Lot E.",
        "sustainability": "🌱 **Sustainability Tips:**\n- Bring a reusable water bottle (refill stations at Sec 110 & 220).\n- Use public transit (NJ Transit or Shuttle buses).\n- Use designated green bins to sort recyclable waste."
    },
    "es": {
        "gate a": "🚪 **Puerta A (Acceso Norte):** Cercana al estacionamiento VIP Lote 1, parada de taxis y estación NJ Transit. Ideal para secciones 101-110.",
        "gate b": "🚪 **Puerta B (Acceso Sur):** Cercana al Lote 2 y terminal de autobuses. Ideal para secciones 115-125.",
        "gate c": "🚪 **Puerta C (Acceso Este):** Junto a la zona de Uber/Lyft en el Lote E. Ideal para secciones 126-135.",
        "gate d": "♿ **Puerta D (Acceso Oeste - Adaptado):** Accesible para sillas de ruedas, rampas y elevadores. Cercano al estacionamiento Lote 3.",
        "metro": "🚆 **Transporte:** NJ Transit llega directo frente a la Puerta A. Los autobuses salen de Lote B. Uber/Lyft están ubicados en el Lote E.",
        "sustainability": "🌱 **Sostenibilidad:**\n- Trae botella reutilizable (estaciones de recarga en Sec 110 y 220).\n- Usa transporte público (trenes y autobuses).\n- Clasifica tus residuos en los contenedores de reciclaje."
    },
    "hi": {
        "gate a": "🚪 **गेट ए (उत्तरी प्रवेश द्वार):** यह एनजे ट्रांजिट ट्रेन स्टेशन और वीआईपी पार्किंग लॉट 1 के पास है। यह सेक्शन 101-110 के लिए सबसे अच्छा है।",
        "gate b": "🚪 **गेट बी (दक्षिणी प्रवेश द्वार):** यह बस डिपो और लॉट 2 के पास है। सेक्शन 115-125 के लिए सबसे उपयुक्त।",
        "gate c": "🚪 **गेट सी (पूर्वी प्रवेश द्वार):** लॉट ई में उबर/लिफ्ट क्षेत्र के पास। सेक्शन 126-135 के लिए उपयुक्त।",
        "gate d": "♿ **गेट डी (पश्चिमी प्रवेश द्वार - सुगम्य):** यह विशेष रूप से विकलांग लोगों और परिवारों के लिए लिफ्ट और चौड़ी लेन के साथ सुगम्य है।",
        "metro": "🚆 **परिवहन:** एनजे ट्रांजिट ट्रेनें सीधे गेट ए के बाहर स्टेशन पर आती हैं। शटल बसें लॉट बी से चलती हैं। उबर/लिफ्ट लॉट ई में हैं।",
        "sustainability": "🌱 **सस्टेनेबिलिटी टिप्स:**\n- दोबारा इस्तेमाल होने वाली पानी की बोतल लाएं (सेक्शन 110 और 220 में रिफिल स्टेशन)।\n- सार्वजनिक परिवहन (ट्रेन या शटल बस) का उपयोग करें।\n- कचरा अलग करने के लिए हरे कूड़ेदानों का उपयोग करें।"
    }
}

# Extensive system instructions containing accessibility and transport directives
SYSTEM_INSTRUCTION = """
You are "FanPath AI" — an enthusiastic, helpful assistant for the FIFA World Cup 2026 at MetLife Stadium.
Your primary role is to assist stadium visitors with logistical questions such as gate directions, food stalls, transport, accessibility, and facility information.

Please strictly follow these rules:
1. **Multilingual support**: Detect if the user is asking in English, Hindi, or Spanish. Respond in the same language.
   - For English, respond in English.
   - For Hindi, respond in standard Hindi (using Devanagari script).
   - For Spanish, respond in Spanish.
2. **Transportation**:
   - Trains: NJ Transit arrives at the stadium station outside Gate A.
   - Buses: Shuttle services from Lot B.
   - Rideshare: Pickup/dropoff in Lot E (near Gate C).
   - Parking: Pre-booked permits required for Lots A, B, C, D. Open parking in Lot E.
3. **Accessibility**:
   - Wheelchair seating: Sections 105, 115, 205, 225.
   - Elevators: Gate D, Section 110, Section 220.
   - Recommended entry: Gate D (has wide lanes, low service counters, direct elevator access).
   - Assistive listening: Guest Services at Sections 104, 124, 216, 318.
4. **Sustainability Guidelines**:
   - Reusable bottles allowed (empty). Water refill stations are at Sections 110 and 220.
   - Encourage fans to use public transit (trains, express shuttles).
   - Waste segregation: Green bins are for recycling, black bins are for general waste.
5. **Gates & Food Courts**:
   - Gate A: North. Gate B: South. Gate C: East. Gate D: West.
   - Food Court: Sections 100-105 & 300-305. Halal certified options: Section 120. Vegetarian/Vegan: Section 125, 328.
6. **Tone and Style**: Keep responses concise (1-3 short paragraphs), polite, structured, and easy to read. Use bullet points for directions. Guidance outside stadium logs should be redirected.
"""

def detect_language(msg: str) -> str:
    """Detects primary language based on keywords in the message.

    Args:
        msg: The user's input message string.

    Returns:
        Language string: 'en', 'es', or 'hi'.
    """
    cleaned = msg.lower()
    if any(word in cleaned for word in ["hola", "buenos", "puerta", "comida", "dónde", "baño", "ayuda", "gracias"]):
        return "es"
    if any(word in cleaned for word in ["नमस्ते", "कहाँ", "गेट", "भोजन", "पानी", "धन्यवाद", "मदद", "ट्रेन"]):
        return "hi"
    return "en"

def get_static_shortcircuit(msg: str) -> Union[str, None]:
    """Inspects query for static questions to bypass outbound AI calls.

    Args:
        msg: Sanitized user query message.

    Returns:
        predefined string answer or None if no match is found.
    """
    cleaned = msg.lower()
    lang = detect_language(cleaned)
    lang_answers = STATIC_ANSWERS.get(lang, STATIC_ANSWERS["en"])
    
    # Check for simple keywords
    if "gate a" in cleaned or "गेट ए" in cleaned or "puerta a" in cleaned:
        return lang_answers["gate a"]
    if "gate b" in cleaned or "गेट बी" in cleaned or "puerta b" in cleaned:
        return lang_answers["gate b"]
    if "gate c" in cleaned or "गेट सी" in cleaned or "puerta c" in cleaned:
        return lang_answers["gate c"]
    if "gate d" in cleaned or "गेट डी" in cleaned or "puerta d" in cleaned:
        return lang_answers["gate d"]
    if any(word in cleaned for word in ["metro", "train", "bus", "transport", "shuttle", "परिवहन", "ट्रेन", "बस", "tren", "transporte"]):
        return lang_answers["metro"]
    if any(word in cleaned for word in ["sustainability", "green", "recycle", "refill", "water", "कचरा", "सस्टेनेबिलिटी", "sostenible", "reciclar"]):
        return lang_answers["sustainability"]
        
    return None

def call_gemini(message: str, history: list[dict[str, str]]) -> str:
    """Invokes Google Gemini with cache-check and static query bypass routines.

    Args:
        message: The current user message (sanitized).
        history: Conversation history context logs.

    Returns:
        The generated response string.
    """
    # 1. Clean history logs
    clean_history = []
    for h in history:
        role = h.get("role")
        text = h.get("text")
        if role in ["user", "model"] and text:
            clean_history.append((role, text))
            
    history_tuple = tuple(clean_history)
    cache_key = (message, history_tuple)
    
    # 2. Check 5-minute memory cache
    now = time.time()
    if cache_key in _response_cache:
        response_text, timestamp = _response_cache[cache_key]
        if now - timestamp < config.GEMINI_CACHE_TIMEOUT_SEC:
            logger.info("Retrieved query response from memory cache.")
            return response_text
            
    # 3. Check for static short-circuits
    static_reply = get_static_shortcircuit(message)
    if static_reply:
        logger.info("Short-circuited query using static mapping.")
        _response_cache[cache_key] = (static_reply, now)
        return static_reply

    # 4. Check for API key presence
    if not config.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is empty. Using local short-circuit rules.")
        # Fallback to rule-based offline responder
        lang = detect_language(message)
        fallback_msg = STATIC_ANSWERS[lang]["gate a"] + "\n\n*(Running in Demo Mode: Gemini API Key not configured)*"
        _response_cache[cache_key] = (fallback_msg, now)
        return fallback_msg

    # 5. Call API
    try:
        # Import standard google-genai components
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        # Build types.Content objects
        contents = []
        for role, text in clean_history:
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=text)]
                )
            )
        # Append current user prompt
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=message)]
            )
        )
        
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
                max_output_tokens=800,
            )
        )
        
        result_text = response.text if response.text else "I am sorry, I couldn't formulate a response."
        _response_cache[cache_key] = (result_text, now)
        return result_text
        
    except Exception as e:
        logger.error(f"Error calling Google Gemini API: {e}", exc_info=True)
        # Fallback to offline rule if API fails
        lang = detect_language(message)
        err_msg = STATIC_ANSWERS[lang]["metro"] + f"\n\n*(API Error occurred: {str(e)[:50]}... Fallback answer provided)*"
        return err_msg

def reset_caches() -> None:
    """Resets the query response cache (useful for testing)."""
    global _response_cache
    _response_cache.clear()

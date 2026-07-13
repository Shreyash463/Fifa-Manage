import os
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fanpath_ai_secret_key_12345")

# Initialize Gemini Client if API Key is available
gemini_available = False
client = None
model_name = "gemini-3.1-flash-lite"  # standard fast model

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    try:
        from google import genai
        from google.genai import types
        # Initialize client with explicit API key
        client = genai.Client(api_key=api_key)
        gemini_available = True
        print("Gemini client successfully initialized.")
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")
else:
    print("WARNING: GEMINI_API_KEY not found in environment. Running in Demo/Offline mode.")

# Stadium knowledge base for system instruction or fallback responses
STADIUM_INFO = """
You are "FanPath AI" — an enthusiastic, helpful GenAI-powered assistant for the FIFA World Cup 2026 at MetLife Stadium.
Your primary role is to assist stadium visitors with logistical questions such as gate directions, food stalls, transport, accessibility, and facility information.

Please strictly follow these rules:
1. **Multilingual support**: Detect if the user is asking in English, Hindi, or Spanish. Respond in the same language.
   - For English, respond in English.
   - For Hindi, respond in standard Hindi (using Devanagari script).
   - For Spanish, respond in Spanish.
   - For any other language, respond politely in that language if possible, or request clarification.
2. **Stadium Information**:
   - **Gates**:
     - *Gate A (North Entrance)*: Located near VIP Parking Lot 1, Taxi stand, and NJ Transit train station. Best entry for sections 101-110, 201-208, 301-308.
     - *Gate B (South Entrance)*: Located near Parking Lot 2 and Regional Bus Depot. Best entry for sections 115-125, 215-225, 315-325.
     - *Gate C (East Entrance)*: Located near Rideshare (Uber/Lyft) zone in Lot E. Best entry for sections 126-135, 226-235, 326-335.
     - *Gate D (West Entrance - Accessibility & Families)*: Fully accessibility-friendly with wide lanes, low counters, and elevators. Closest to Parking Lot 3 (Accessibility Parking). Best entry for sections 136-148, 236-248, 336-348.
   - **Facilities**:
     - *Elevators*: Accessible at Gate D, Section 110, and Section 220.
     - *Restrooms*: Available on all levels. Family/gender-neutral restrooms are at Section 104, 118, 208, 224, 305, 332.
     - *Sensory Room*: Quiet space for neurodivergent visitors or families located at Section 212.
     - *First Aid Stations*: Found at Section 109, 131, 219, and 311.
     - *Merchandise Shops*: Main Fan Shop is near Gate A (North). Smaller kiosks are at sections 112, 134, 205, 227, 314, 338.
   - **Food Court (Concessions)**:
     - *Main Food Courts*: Sections 100-105 and 300-305 (Burgers, hot dogs, fries, soda).
     - *Tacos & Burritos*: Sections 114, 138, 210, and 319.
     - *Halal & Kosher Food*: Section 120 (Certified food options).
     - *Vegetarian & Vegan Corner*: Section 125 and Section 328 (Wraps, salads, and plant-based burgers).
     - *Beverages*: Stands are present at every section. Valid ID required for alcohol purchases.
   - **Accessibility**:
     - Wheelchair seating: Sections 105, 115, 205, and 225.
     - Assistive listening devices: Available at Guest Services (Sections 104, 124, 216, 318).
     - Recommended entry: Gate D.
   - **Transport**:
     - *Train*: NJ Transit trains arrive directly at the stadium station outside Gate A.
     - *Buses*: Express shuttle services depart from Lot B (near Gate B).
     - *Rideshare*: Uber/Lyft pickup/dropoff zone is in Lot E (near Gate C).
     - *Parking*: Lots A, B, C, D require pre-booked permits. Lot E is open parking.
3. **Tone and Style**: Keep responses relatively concise (usually 1-3 short paragraphs), warm, structured, and easy to read on a mobile screen. Use bullet points for directions.
4. **General Scope**: If the user asks general questions or questions unrelated to stadium operations/logistics, guide them back to stadium information or help. Mention that they can view the Crowd Dashboard or Report an Issue using the site's navigation menu.
"""

FALLBACK_PROMPTS = {
    "en": "I am currently running in Demo Mode (without a Gemini API Key). How can I assist you with stadium information? (e.g., Gate A details, food locations, transport)",
    "es": "Actualmente estoy ejecutándome en Modo Demo (sin clave de API de Gemini). ¿Cómo puedo ayudarle con la información del estadio? (por ejemplo, detalles de la Puerta A, comida, transporte)",
    "hi": "मैं वर्तमान में डेमो मोड (बिना जेमिनी एपीआई कुंजी) में चल रहा हूँ। मैं स्टेडियम की जानकारी में आपकी क्या मदद कर सकता हूँ? (जैसे, गेट ए का विवरण, भोजन स्थल, परिवहन)"
}

# Helpers for loading/saving data
def load_issues():
    issues_path = os.path.join(app.root_path, 'issues.json')
    if not os.path.exists(issues_path):
        with open(issues_path, 'w') as f:
            json.dump([], f)
        return []
    try:
        with open(issues_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading issues: {e}")
        return []

def save_issues(issues):
    issues_path = os.path.join(app.root_path, 'issues.json')
    try:
        with open(issues_path, 'w', encoding='utf-8') as f:
            json.dump(issues, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving issues: {e}")

def load_crowd_data():
    crowd_path = os.path.join(app.root_path, 'mock_crowd_data.json')
    if not os.path.exists(crowd_path):
        default_data = {
            "Gate A": "Medium",
            "Gate B": "Low",
            "Food Court": "High",
            "Parking": "Medium",
            "Main Stand": "Low"
        }
        with open(crowd_path, 'w') as f:
            json.dump(default_data, f)
        return default_data
    try:
        with open(crowd_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading crowd data: {e}")
        return {}

def save_crowd_data(data):
    crowd_path = os.path.join(app.root_path, 'mock_crowd_data.json')
    try:
        with open(crowd_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving crowd data: {e}")


# Simple rule-based chatbot fallback when API key is missing
def get_offline_response(user_message):
    msg = user_message.lower()
    
    # Detect language
    lang = "en"
    if any(word in msg for word in ["hola", "buenos", "puerta", "comida", "dónde", "baño", "ayuda", "gracias"]):
        lang = "es"
    elif any(word in msg for word in ["नमस्ते", "कहाँ", "गेट", "भोजन", "पानी", "धन्यवाद", "मदद", "ट्रेन"]):
        lang = "hi"
    
    if lang == "es":
        if "puerta a" in msg or "gate a" in msg:
            return "🚪 **Puerta A (Entrada Norte):** Cerca de la estación de tren NJ Transit y estacionamiento VIP Lote 1. Ideal para secciones 101-110."
        elif "puerta b" in msg or "gate b" in msg:
            return "🚪 **Puerta B (Entrada Sur):** Cerca de la terminal de autobuses y Lote 2. Ideal para secciones 115-125."
        elif "puerta c" in msg or "gate c" in msg:
            return "🚪 **Puerta C (Entrada Este):** Cerca de la zona de Uber/Lyft en el Lote E. Ideal para secciones 126-135."
        elif "puerta d" in msg or "gate d" in msg:
            return "♿ **Puerta D (Entrada Oeste):** Accesible para personas con discapacidad y familias. Cerca del estacionamiento adaptado Lote 3."
        elif any(word in msg for word in ["comida", "comer", "restaurante", "hamburguesa"]):
            return "🍔 **Alimentos:** El patio principal está en las secciones 100-105. Hay comida Halal en la sección 120 y opciones vegetarianas en la sección 125."
        elif any(word in msg for word in ["transporte", "tren", "bus", "autobus", "estacionamiento", "parqueo"]):
            return "🚌 **Transporte:**\n- **Tren:** Estación NJ Transit frente a la Puerta A.\n- **Rideshare (Uber/Lyft):** Lote E cerca de la Puerta C.\n- **Autobuses:** Estación en Lote B."
        else:
            return f"Hola! {FALLBACK_PROMPTS['es']}\n\nPuedo informarte sobre accesibilidad, puertas (A, B, C, D), comida y transporte en el estadio."
    elif lang == "hi":
        if "गेट ए" in msg or "gate a" in msg:
            return "🚪 **गेट ए (उत्तरी प्रवेश द्वार):** यह एनजे ट्रांजिट ट्रेन स्टेशन और वीआईपी पार्किंग लॉट 1 के पास है। यह सेक्शन 101-110 के लिए सबसे अच्छा है।"
        elif "गेट बी" in msg or "gate b" in msg:
            return "🚪 **गेट बी (दक्षिणी प्रवेश द्वार):** यह बस डिपो और लॉट 2 के पास है। सेक्शन 115-125 के लिए आदर्श।"
        elif "गेट सी" in msg or "gate c" in msg:
            return "🚪 **गेट सी (पूर्वी प्रवेश द्वार):** लॉट ई में उबर/लिफ्ट राइडशेयर क्षेत्र के पास। सेक्शन 126-135 के लिए उपयुक्त।"
        elif "गेट डी" in msg or "gate d" in msg:
            return "♿ **गेट डी (पश्चिमी प्रवेश द्वार - सुगम्य):** यह विशेष रूप से विकलांग लोगों और परिवारों के लिए है, जिसमें लिफ्ट और चौड़ी लेन हैं।"
        elif any(word in msg for word in ["भोजन", "खाना", "शाकाहारी", "समोसा", "बर्गर"]):
            return "🍔 **भोजन विकल्प:** मुख्य फूड कोर्ट सेक्शन 100-105 में है। हलाल भोजन सेक्शन 120 में और शाकाहारी/वेगन भोजन सेक्शन 125 में उपलब्ध है।"
        elif any(word in msg for word in ["ट्रेन", "बस", "गाड़ी", "पार्किंग", "यातायात"]):
            return "🚆 **परिवहन:**\n- **ट्रेन:** गेट ए के ठीक बाहर एनजे ट्रांजिट स्टेशन।\n- **बस:** लॉट बी (गेट बी के पास) से बस सेवाएं।\n- **पार्किंग:** लॉट ए, बी, सी, डी के लिए पहले से बुक पास आवश्यक हैं।"
        else:
            return f"नमस्ते! {FALLBACK_PROMPTS['hi']}\n\nमैं आपको स्टेडियम के गेट, भोजन स्थल, परिवहन और विकलांग सहायता के बारे में बता सकता हूँ।"
    else:
        # English fallback
        if "gate a" in msg:
            return "🚪 **Gate A (North Entrance):** Located near the NJ Transit train station and VIP Parking Lot 1. Best entry for sections 101-110."
        elif "gate b" in msg:
            return "🚪 **Gate B (South Entrance):** Located near the Bus Depot and Parking Lot 2. Best entry for sections 115-125."
        elif "gate c" in msg:
            return "🚪 **Gate C (East Entrance):** Located near the Rideshare (Uber/Lyft) zone in Lot E. Best entry for sections 126-135."
        elif "gate d" in msg:
            return "♿ **Gate D (West Entrance - Accessible):** Fully accessibility-friendly with elevators, wide lanes, and close to Accessibility Parking Lot 3."
        elif any(word in msg for word in ["food", "eat", "concession", "burger", "vegan", "halal"]):
            return "🍔 **Food Stalls:** Main Food Courts are at Sections 100-105 & 300-305. Halal food is at Section 120, and Vegetarian/Vegan options are at Section 125."
        elif any(word in msg for word in ["transport", "train", "bus", "uber", "taxi", "parking"]):
            return "🚆 **Transport Info:**\n- **Train:** NJ Transit station directly outside Gate A.\n- **Buses:** Shuttle depot at Lot B (near Gate B).\n- **Rideshare:** Pickup/dropoff zone is in Lot E (near Gate C).\n- **Parking:** Lots A, B, C, D require pre-booked permits."
        elif any(word in msg for word in ["sensory", "quiet"]):
            return "🧩 **Sensory Room:** Located at Section 212 for neurodivergent visitors or families needing a quiet space."
        else:
            return f"Hello! {FALLBACK_PROMPTS['en']}\n\nI can help you locate gates, food courts, accessibility spaces, and transport hubs around the stadium."


# Routes
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/chat', methods=['POST'])
def chat():
    user_data = request.json or {}
    history = user_data.get('history', [])
    user_message = user_data.get('message', '')

    if not user_message:
        return jsonify({"reply": "I did not receive a message. Please try again."})

    # If Gemini is not available, run offline fallback
    if not gemini_available:
        reply = get_offline_response(user_message)
        # Append some notification about Demo Mode
        demo_suffix = "\n\n*(Running in Demo Mode: Gemini API Key not configured)*"
        return jsonify({"reply": reply + demo_suffix})

    try:
        # Build contents from history to support conversation context
        # We parse the history list passed from UI
        # History format: [{"role": "user"|"model", "text": "..."}]
        from google.genai import types
        
        contents = []
        for h in history:
            role = h.get('role')
            text = h.get('text')
            if role in ['user', 'model'] and text:
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=text)]
                    )
                )
        
        # Add the current user message at the end
        contents.append(
            types.Content(
                role='user',
                parts=[types.Part.from_text(text=user_message)]
            )
        )

        # Call Gemini API
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=STADIUM_INFO,
                temperature=0.7,
                max_output_tokens=800,
            )
        )
        
        return jsonify({"reply": response.text})
    except Exception as e:
        print(f"Gemini API Error: {e}")
        # Fallback to rule-based response in case of API failure
        fallback_reply = get_offline_response(user_message)
        error_suffix = f"\n\n*(Error calling Gemini API: {str(e)[:50]}... Fallback answer provided)*"
        return jsonify({"reply": fallback_reply + error_suffix})


@app.route('/dashboard')
def dashboard():
    crowd_data = load_crowd_data()
    return render_template('dashboard.html', crowd=crowd_data)


@app.route('/api/crowd/update', methods=['POST'])
def update_crowd():
    # Simulate changing crowd density
    zones = ["Gate A", "Gate B", "Food Court", "Parking", "Main Stand"]
    densities = ["Low", "Medium", "High"]
    
    # Generate random updates
    new_data = {zone: random.choice(densities) for zone in zones}
    save_crowd_data(new_data)
    
    return jsonify({"status": "success", "data": new_data})


@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        # Retrieve form data
        reporter_name = request.form.get('reporter_name', 'Anonymous')
        zone = request.form.get('zone', '')
        category = request.form.get('category', 'Other')
        description = request.form.get('description', '')

        if not zone or not description:
            flash("Please fill in all required fields (Zone and Description).", "danger")
            return redirect(url_for('report'))

        issues = load_issues()
        
        # Create a new issue object
        new_issue = {
            "id": str(uuid.uuid4())[:8],
            "reporter_name": reporter_name,
            "zone": zone,
            "category": category,
            "description": description,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Open"
        }
        
        issues.append(new_issue)
        save_issues(issues)
        
        flash("Thank you! The issue has been reported successfully.", "success")
        return redirect(url_for('report'))
        
    return render_template('report.html')


@app.route('/admin')
def admin():
    issues = load_issues()
    # Sort issues so Open ones are on top, and order by timestamp descending
    issues_sorted = sorted(issues, key=lambda x: (x['status'] != 'Open', x['timestamp']), reverse=True)
    return render_template('admin.html', issues=issues_sorted)


@app.route('/admin/resolve/<issue_id>', methods=['POST'])
def resolve_issue(issue_id):
    issues = load_issues()
    found = False
    for issue in issues:
        if issue['id'] == issue_id:
            # Toggle or set to Resolved
            issue['status'] = 'Resolved' if issue['status'] == 'Open' else 'Open'
            found = True
            break
            
    if found:
        save_issues(issues)
        flash(f"Issue {issue_id} status updated.", "success")
    else:
        flash(f"Issue {issue_id} not found.", "danger")
        
    return redirect(url_for('admin'))


@app.route('/admin/delete/<issue_id>', methods=['POST'])
def delete_issue(issue_id):
    issues = load_issues()
    original_len = len(issues)
    issues = [issue for issue in issues if issue['id'] != issue_id]
    
    if len(issues) < original_len:
        save_issues(issues)
        flash(f"Issue {issue_id} deleted successfully.", "success")
    else:
        flash(f"Issue {issue_id} not found.", "danger")
        
    return redirect(url_for('admin'))


if __name__ == '__main__':
    # Run locally on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)

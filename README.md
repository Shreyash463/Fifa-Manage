# FanPath AI — FIFA World Cup 2026 Stadium Visitor Assistant

FanPath AI is a GenAI-powered web application built using Python Flask and Google Gemini. It is designed to assist visitors navigating stadium directions, concession stalls, transport hubs, accessibility structures, and live crowd situations during the FIFA World Cup 2026 games.

## 🌟 Key Features

1. **AI Chatbot Assistant**:
   - Seeded with comprehensive stadium knowledge (gates, restrooms, food, sensory rooms, transport options).
   - Dynamic multilingual support (automatically detects and responds in English, Español, or हिंदी).
   - Utilizes the new official **Google GenAI Python SDK** (`google-genai`) with the `gemini-3.1-flash-lite` model.
   - Built-in stateless conversation context manager.
   - Offline/Demo fallback capability in case the API key is not configured.

2. **Real-time Crowd Density Dashboard**:
   - Visualizes crowd load (Low, Medium, High) across 5 stadium zones (Gate A, Gate B, Food Court, Parking, Main Stand).
   - Features color-coded status badges with pulsing animation lights (green for Low, yellow/orange for Medium, and red for High).
   - Integrates an interactive "Simulate Crowd Update" AJAX action to trigger mock density changes without page reloads.

3. **Volunteer Issue Reporting & Admin Console**:
   - Simple form letting volunteers/staff log facility or safety issues (e.g., broken escalators, spills, lines).
   - Automatically saves reports to a local `issues.json` database.
   - Admin console to list, toggle resolution state, or delete issue logs.

4. **Premium Responsive UI**:
   - Sleek dark theme with vibrant soccer-orange accents.
   - Modern glassmorphism card panels with Outfit typography.
   - High contrast ratios (fully accessible for visual scanners) and `aria-label` tags for screen readers.

---

## 🛠️ Project Structure

```
d:\Fifa manage\
  ├─ app.py               # Main Flask server and APIs
  ├─ test_app.py          # Unit test suite
  ├─ requirements.txt     # Dependency listing
  ├─ Dockerfile           # Docker image setup for Cloud Run
  ├─ firebase.json        # Firebase Hosting & functions routing
  ├─ .firebaserc          # Firebase project configuration
  ├─ static/
  │    └─ css/style.css   # Theme styles, grids, pulses, and responsiveness
  └─ templates/           # Jinja2 HTML templates
       ├─ base.html       # Structural frame, nav bar, mobile scripts
       ├─ home.html       # Chatbot view & AJAX chat client
       ├─ dashboard.html  # Crowd density status & simulator
       ├─ report.html     # Issue reporting form
       └─ admin.html      # Admin dashboard console
```

---

## 🚀 Installation & Local Setup

### 1. Clone the Project
```bash
git clone https://github.com/Shreyash463/Fifa-Manage.git
cd Fifa-Manage
```

### 2. Set Up Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Create a `.env` file in the project root:
```env
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Run the Application
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser.

---

## 🧪 Running Automated Tests

A comprehensive test suite is provided to verify all routes, API integrations, and forms:

```bash
python -m unittest test_app.py
```

---

## ☁️ Deployment

### 1. Google Cloud Run (Recommended Container Deployment)
Deploy using the provided `Dockerfile`:
```bash
gcloud run deploy fanpath-ai --source . --env-vars="GEMINI_API_KEY=YOUR_KEY" --allow-unauthenticated
```

### 2. Firebase Hosting (With Serverless Python Functions)
1. Ensure your Firebase project is upgraded to the **Blaze (pay-as-you-go) plan** (required for Cloud Build APIs).
2. Install tools: `npm install -g firebase-tools`
3. Run `firebase login` and authenticate.
4. Deploy the functions and hosting rules:
   ```bash
   firebase deploy --only functions,hosting
   ```

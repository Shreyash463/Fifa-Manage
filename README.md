# FanPath AI — FIFA World Cup 2026 Stadium Assistant

FanPath AI is a premium, GenAI-powered web application built using Python Flask and Google Gemini. It is designed to assist visitors navigating stadium directions, concession stalls, transport hubs, accessibility structures, and live crowd situations during the FIFA World Cup 2026 games.

---

## 🗺️ Challenge Focus Area Mapping

The following table maps the 8 challenge focus areas to the specific features built into FanPath AI:

| Focus Area | Feature in FanPath AI |
| :--- | :--- |
| **1. Navigation** | Real-time interactive AI Chatbot with stadium gate/seating maps and quick static direction short-circuits. |
| **2. Crowd Management** | Pulse-colored Live Crowd Density Dashboard monitoring Gate A, Gate B, Food Court, Parking, and Main Stand. |
| **3. Accessibility** | "Skip to Main Content" links, keyboard Tab focus outline highlights, `aria-live="polite"` screen readers for chatbot logs and crowd status updates, high-contrast WCAG AA grey styles, and Gate D recommended entryways. |
| **4. Transportation** | Dedicated `/transport` details guide listing NJ Transit Rail routes, express shuttle bus locations, and public parking lots. |
| **5. Sustainability** | Waste segregation sorting bins guidelines, public transit benefits messaging, and water refill station details (at Sections 110 and 220). |
| **6. Multilingual Assistance** | Automated language-detection algorithms handling English, Español (Spanish), and हिंदी (Hindi) dynamically for both static lookups and GenAI models. |
| **7. Operational Intelligence** | Secure Admin Console allowing staff to track, toggle resolution state, or delete issues logged by volunteers. |
| **8. Real-time Decision Support** | Alternate routing instructions triggered on High density cards for fans, coupled with warning banners on the Admin page. |

---

## 🛠️ Refactored Architecture

The codebase has been refactored from a single file to a clean, modular design:
```
d:\Fifa manage\
  ├─ app.py               # Main Flask server initialization
  ├─ config.py            # Hardcoded config parameters and secrets loader
  ├─ data_service.py      # Database loaders, in-memory caches, and HTML sanitizers
  ├─ gemini_service.py    # GenAI connectors, 5-min caching, and short-circuits
  ├─ extensions.py        # Shared Flask extensions (Flask-Limiter)
  ├─ routes.py            # Blueprint endpoint routing, auth guards, and decision rules
  ├─ requirements.txt     # Third-party libraries
  ├─ Dockerfile           # Docker image setup for Cloud Run
  ├─ firebase.json        # Firebase Hosting & functions routing
  ├─ .firebaserc          # Firebase default project
  ├─ static/
  │    └─ css/style.css   # Accessibility outlines, pulses, and minified theme
  ├─ templates/           # Accessibility-compliant Jinja2 templates
  │    ├─ base.html       # Skip-to-content links and navigation headers
  │    ├─ home.html       # Chat client with aria-live updates
  │    ├─ dashboard.html  # Live crowd grid and alternates decision panels
  │    ├─ transport.html  # Transit and green sustainability tips
  │    ├─ report.html     # Secure volunteer issue reporting form
  │    ├─ admin.html      # Token-guarded staff console and high-density alerts
  │    └─ error.html      # Safe generic error screens (400, 403, 404, 429, 500)
  └─ tests/               # pytest test suite
       ├─ test_data_service.py
       ├─ test_gemini_service.py
       └─ test_routes.py
```

---

## 🔒 Security Enhancements
1. **Secrets Security**: `GEMINI_API_KEY` and security tokens are loaded securely from `.env` and never hardcoded in files.
2. **XSS / Injection Protection**: All data inputs (chat messages, issues) and database loads are HTML-escaped using `html.escape` during save validations.
3. **Secure Headers**: Integrated `Flask-Talisman` to set strict headers (Content Security Policy, X-Frame-Options, X-Content-Type-Options).
4. **Rate Limiting**: Rate-limited the chatbot API `/chat` using `Flask-Limiter` (15 requests/minute limit to prevent quota spam).
5. **Auth Guards**: The Admin Console `/admin` is guarded by token verification matching the token in `.env`.
6. **Error Safeguards**: Custom application errors return generic screens (`templates/error.html`), masking internal stack traces from users.

## ⚡ Efficiency Optimizations
1. **Gemini Memory Caching**: 5-minute memory cache mapping user queries and conversation histories to previous replies to avoid redundant API cost.
2. **Disk I/O Bypass**: Cached JSON loads in-memory, updating from disk only when `os.path.getmtime` reflects file modifications.
3. **Static Query Short-Circuits**: Simple logistical checks (e.g. "Gate A directions") are mapped locally in code, responding instantly without contacting the Gemini API.
4. **Gzip Compression**: Gzipped static resources on-the-fly using `Flask-Compress`.

## ♿ Accessibility Compliance
- **Skip Link**: Added a hidden "Skip to Main Content" link at the top of the body for keyboard users.
- **Focus Indicators**: Standardized visible, orange `:focus-visible` outlines on all links and interactive inputs.
- **Screen Reader Announcers**: Wrapped chat histories and status indicators in `aria-live="polite"` blocks.
- **Contrast**: Contrast meets WCAG AA guidelines with soft bright-grey fonts on the premium dark theme.

---

## 🚀 Installation & Local Setup

### 1. Clone & Install
```bash
git clone https://github.com/Shreyash463/Fifa-Manage.git
cd Fifa-Manage
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file in the project root:
```env
FLASK_APP=app.py
FLASK_ENV=development
GEMINI_API_KEY=your_gemini_api_key_here
ADMIN_TOKEN=admin_secure_token_123
```

### 3. Run the App
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 🧪 Running Automated Tests

To execute the unit and integration test suite, run:

```bash
python -m pytest tests/
```
*(All 17 tests covering mock services, JSON loaders, edge inputs, rate limit checks, and token auth guards will execute).*

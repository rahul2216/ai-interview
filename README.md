# AI Mock Interview — Professional Job Interview Platform

An enterprise-grade, responsive full-stack Python web application engineered for job seekers, freshers, experienced professionals, and career switchers to simulate realistic job interviews, evaluate competency responses, and receive rubric-based AI feedback.

---

## 🚀 Key Highlights & Exclusions

- **Exclusively Professional Focus**: Specializes strictly in professional corporate & tech hiring:
  - Technical Interviews (System Design, Frameworks, Architecture, Concurrency, Caching)
  - Coding & Algorithmic Problem-Solving (with Big-O analysis and edge case validation)
  - HR & Behavioral Interviews (STAR Method — Situation, Task, Action, Result)
  - Technical + HR Combo Interviews
  - Company-Specific Job Role Simulations
- **Zero Academic Viva / Exam Bloat**: No BCA viva, no academic semester syllabi, no college practicals, and no resume ATS scorers.
- **Dual Voice & Text Interaction**:
  - **SpeechSynthesis API**: Natural voice question reading with play, pause, and instant audio-stop controls.
  - **SpeechRecognition API (Web Speech API)**: Hands-free microphone dictation with editable real-time transcripts.
  - **Code Editor Mode**: Monospace syntax-friendly answering for coding problem-solving rounds.
- **Transparent, Voluntary Camera Preview**:
  - Local MediaDevices video stream for candidate poise and eye-contact practice.
  - Completely voluntary — users can complete full interviews without enabling the camera.
  - Zero permanent server-side video recording or pseudo-scientific deceit detection claims.
- **Centralized Version-Controlled System Prompt**:
  - Embedded version 2.1.0 backend prompt template adhering strictly to structured JSON schemas.
- **Objective 100-Point Rubric Engine**:
  - Technical: Correctness (40), Understanding (25), Completeness (15), Reasoning (10), Examples (10).
  - Coding: Algorithmic Logic (30), Correctness (25), Complexity (20), Edge Cases (15), Code Quality (10).
  - HR / Behavioral: Relevance (30), Clarity (25), STAR Structure (20), Reasoning (15), Impact & Metrics (10).
- **Official ReportLab PDF Reports**: Downloadable, beautifully formatted evaluation PDF reports for each interview attempt.
- **Guest Mode & Account Linking**: Try immediately without signup; seamless transfer of guest results upon registration.

---

## 🛠 Technology Stack

- **Backend**: Python 3, Flask, Flask-SQLAlchemy, Flask-Login, Flask-Migrate, Flask-WTF (CSRF Protection), ReportLab (PDF generation).
- **AI Integration**: Official OpenAI Python SDK (`openai>=1.20.0`) with intelligent fallback rubric engine.
- **Database**: SQLAlchemy supporting SQLite (local development) and PostgreSQL (production).
- **Frontend**: Semantic HTML5, Modern CSS3 (CSS Custom Properties, responsive Grid & Flexbox, light/dark themes), Vanilla JavaScript (ES6+, Fetch API, Web Speech API, MediaDevices API). *No React or bulky JS frameworks.*

---

## 📂 Project Architecture

```
ai-mock-interview/
├── app.py                     # Flask application factory and error handlers
├── config.py                  # Environment and database configuration
├── extensions.py              # SQLAlchemy, LoginManager, CSRFProtect, Migrate
├── models.py                  # Database models (users, interviews, questions, answers, progress)
├── requirements.txt           # Python dependencies
├── .env.example               # Example environment configuration
├── README.md                  # Comprehensive documentation
├── services/
│   ├── __init__.py
│   ├── ai_service.py          # Centralized OpenAI prompt engine & rubric fallback
│   └── pdf_service.py         # ReportLab PDF report generator
├── routes/
│   ├── __init__.py
│   ├── auth.py                # Authentication, registration, guest transfer
│   ├── main.py                # Homepage, tracks, dashboard, profile, legal
│   ├── interview.py           # Setup form, consent, live room, report view
│   └── api.py                 # RESTful endpoints for question flow & answer scoring
├── static/
│   ├── css/
│   │   └── style.css          # Design system (navy & white, dark mode, responsive)
│   └── js/
│       ├── main.js            # Global theme toggle, mobile menu, CSRF fetch helper
│       ├── audio_camera.js    # SpeechSynthesis, SpeechRecognition, Camera controller
│       └── interview.js       # Live interview coordinator & retry resilience
├── templates/
│   ├── base.html              # Master layout with navigation, alerts, and footer
│   ├── index.html             # Homepage with workflow and feature tracks
│   ├── interview_types.html   # Dedicated tracks landing page
│   ├── profile.html           # Profile settings and user statistics
│   ├── privacy.html           # Transparent privacy & audio/video terms
│   ├── terms.html             # Practice scope and employment disclaimer
│   ├── auth/
│   │   ├── login.html         # Sign in with guest transfer notice
│   │   └── register.html      # Account creation
│   ├── interview/
│   │   ├── setup.html         # 14-field candidate configuration form
│   │   ├── consent.html       # Rules, consent, and employment disclaimer
│   │   ├── live.html          # Live question-by-question interview room
│   │   └── report.html        # Final results dashboard with review filters
│   ├── dashboard/
│   │   ├── dashboard.html     # Analytics, topic strengths, and track progress
│   │   └── history.html       # Historical session logs with PDF download & deletion
│   └── errors/
│       ├── 403.html           # Forbidden access
│       ├── 404.html           # Not found
│       └── 500.html           # Internal server error
└── tests/
    ├── __init__.py
    └── test_app.py            # Complete unit test suite (9 test cases)
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- `pip` package manager

### 2. Setup Virtual Environment
```bash
cd ai-mock-interview
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your keys:
```ini
SECRET_KEY=your-secure-random-secret-key
DATABASE_URL=sqlite:///mock_interview.db
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
PORT=5000
```
> **Note:** If `OPENAI_API_KEY` is omitted, the application automatically uses the built-in rubric engine to evaluate candidate responses, ensuring 100% functionality out of the box in offline/development settings.

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to: `http://localhost:5000`

---

## 🧪 Running the Test Suite

Execute the unit test suite with:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
All tests verify:
- Registration, login, and session preservation
- Guest mode creation and account linking
- Candidate details configuration validation
- Question generation and sequential delivery (one-by-one)
- Voice/text answer evaluation and rubric grading
- ReportLab PDF report generation
- Authorized access and 403 boundary enforcement

---

## 🌐 Production Deployment

### Production WSGI (Gunicorn)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

### PostgreSQL Setup
In production, point `DATABASE_URL` in `.env` to your PostgreSQL database:
```ini
DATABASE_URL=postgresql://user:password@localhost:5432/aimockinterview
```
SQLAlchemy handles table schemas automatically on initialization.

---

## 🔒 Security & Privacy Practices

1. **CSRF Protection**: All form submissions and Fetch API calls pass CSRF tokens generated via `Flask-WTF`.
2. **Session Isolation**: Every interview session is strictly guarded by ownership checks. Guests and registered users cannot access another user's session data.
3. **No Secret Recording**: The camera preview is browser-local (`getUserMedia`), and explicit consent is required. No video media is recorded or saved.
4. **Untrusted Input Sanitation**: Candidate answers and pasted job descriptions are treated as untrusted strings, never as raw executable system prompt instructions.
5. **Employment Disclaimer**: Transparent notices across setup, consent, and report pages clarify that evaluations are developmental benchmarks and do not guarantee hiring offers.

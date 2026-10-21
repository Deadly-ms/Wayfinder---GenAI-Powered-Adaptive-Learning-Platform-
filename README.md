# Wayfinder: GenAI-Powered Adaptive Learning Platform

An adaptive learning platform that uses generative AI (Google Gemini) to personalize learning content and guide learners along a path that fits their level and goals.

---

## Features

- [e.g. AI-generated lessons, explanations, or quizzes powered by the Gemini API]
- [e.g. adaptive difficulty or recommendations based on learner performance]
- [e.g. user accounts and progress tracking]
- Clean server-rendered UI built with Flask templates

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | Python, Flask |
| **AI** | Google Gemini API |
| **Database** | SQLite |
| **Frontend** | HTML, CSS, Jinja2 templates |
| **Deployment** | Render |

---

## Project Structure

```
├── app.py              # Flask application entry point
├── modules/            # Application modules (AI, learning logic, etc.)
├── templates/          # HTML templates
├── static/css/         # Stylesheets
├── instance/           # SQLite database (generated at runtime)
├── db_setup.py         # Creates database tables
├── migrate_db.py       # Database migrations
├── seed.py             # Seeds initial data
├── test_ai.py          # Tests the Gemini integration
├── list_models.py      # Lists available Gemini models
├── requirements.txt
└── render.yaml         # Render deployment config
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/)

### Setup

```bash
git clone https://github.com/Deadly-ms/Wayfinder---GenAI-Powered-Adaptive-Learning-Platform-.git
cd Wayfinder---GenAI-Powered-Adaptive-Learning-Platform-

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:
```env
GEMINI_API_KEY=your_api_key_here
SECRET_KEY=your_secret_key
```

Initialize and seed the database:
```bash
python db_setup.py
python seed.py
```

Run the app:
```bash
python app.py
```

Open `http://localhost:5000`.

---

## Deployment

Deployed on Render using the included `render.yaml`. Set `GEMINI_API_KEY` and `SECRET_KEY` as environment variables in the Render dashboard.

---

## Author

**Sriram** · [LinkedIn](https://linkedin.com/in/sriram-s-12b80626b)

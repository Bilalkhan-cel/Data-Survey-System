import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

from Data_extraction_XML import extract_columns, extract_full_survey

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
XML_PATH = os.path.join(BASE_DIR, "data.xml")

app = Flask(__name__)

# Preserve the legacy database logic. Default to a local SQLite file so the app
# runs out-of-the-box, but honour DATABASE_URL exactly like the old project.
database_url = os.getenv("DATABASE_URL") or f"sqlite:///{os.path.join(BASE_DIR, 'survey.db')}"
# SQLAlchemy expects the "postgresql://" scheme (some providers emit "postgres://").
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SESSION_SECRET_KEY", "dev-secret-key")
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True

db = SQLAlchemy(app)

# ---------------------------------------------------------------------------
# XML-driven survey content + dynamic model (legacy dynamic-column approach)
# ---------------------------------------------------------------------------
cols = extract_columns(XML_PATH)
survey = extract_full_survey(XML_PATH)
questions = survey.get("questions", [])


class survey_data(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    is_bad = db.Column(db.Integer, default=0)


# One string column per question id, created dynamically from the XML.
for col in cols:
    setattr(
        survey_data,
        col,
        db.Column(db.String(250), nullable=True, default=""),
    )


def init_db():
    try:
        db.create_all()
        print("DB initialized")
    except Exception as e:
        print("DB error:", e)
        raise


with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Allow embedding inside the v0 preview iframe (legacy behaviour)
# ---------------------------------------------------------------------------
@app.after_request
def allow_iframe(response):
    response.headers.pop("X-Frame-Options", None)
    response.headers["Content-Security-Policy"] = "frame-ancestors *;"
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    # Drive the start/intro/outro copy from the XML survey metadata.
    return render_template(
        "index.html",
        title="SURVEY:",
        subtitle=survey.get("title", "Survey"),
        intro=survey.get("description", ""),
        outro_title="THANK YOU FOR PARTICIPATING!",
        outro_text=(
            "Your responses have been recorded. The data you provided remains "
            "strictly private and will not be shared with anyone."
        ),
    )


@app.route("/api/survey")
def api_survey():
    """Return the XML-driven questions/options for the front-end."""
    return jsonify(
        {
            "title": survey.get("title"),
            "description": survey.get("description"),
            "questions": questions,
        }
    )


@app.route("/api/submit", methods=["POST"])
def api_submit():
    """Persist a completed survey using the legacy dynamic-column + 3-second rule logic."""
    data = request.get_json(silent=True) or {}
    answers = data.get("answers", [])
    if not isinstance(answers, list) or not answers:
        return jsonify({"error": "No answers provided"}), 400

    # Map answers (keyed by question id) onto the dynamic columns.
    row_data = {}
    fast_answers = 0
    for ans in answers:
        if not isinstance(ans, dict):
            continue
        qid = ans.get("id")
        if qid not in cols:
            continue
        row_data[qid] = "" if ans.get("value") is None else str(ans.get("value"))

        # 3-second rule: an answer given in <= 3 seconds counts as "fast".
        try:
            response_time = float(ans.get("response_time", 0))
        except (TypeError, ValueError):
            response_time = 0.0
        if response_time <= 3:
            fast_answers += 1

    if not row_data:
        return jsonify({"error": "No valid answers provided"}), 400

    # is_bad flag preserved from the legacy logic: flagged when more than half
    # of the questions were answered suspiciously fast.
    total_questions = len(questions) if questions else len(row_data)
    is_bad = 1 if fast_answers > total_questions / 2 else 0

    record = survey_data(is_bad=is_bad, **row_data)
    db.session.add(record)
    db.session.commit()

    return jsonify({"saved": True, "id": record.id, "is_bad": is_bad})


@app.route("/api/results")
def api_results():
    """Aggregate counts per question/value across all saved responses."""
    rows = survey_data.query.all()
    results = {}
    for col in cols:
        counts = {}
        for r in rows:
            val = getattr(r, col, None)
            if val is None or val == "":
                continue
            counts[val] = counts.get(val, 0) + 1
        results[col] = counts
    return jsonify({"total_responses": len(rows), "results": results})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)

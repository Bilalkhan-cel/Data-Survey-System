# Data Survey System

A dynamic, XML-driven survey application built with **Flask** and **SQLAlchemy**. Instead of hard-coding survey questions into a database schema, the entire questionnaire — sections, questions, options, images, and even Likert scales — is defined in a single `data.xml` file. The app parses that file on startup, builds the database table on the fly, and renders the survey through a JSON API consumed by the front-end.

**Live demo:** [data-survey-system-ruddy.vercel.app](https://data-survey-system-ruddy.vercel.app)

## Overview

This project was built to support an independent research study (in collaboration with IST and NUST) but is generic enough to be reused for any questionnaire. Its core idea is **"XML in, dynamic schema out"**:

1. You describe your survey — sections, questions, question types, and answer options — in `data.xml`.
2. `Data_extraction_XML.py` parses that file into a structured survey object.
3. `app.py` reads the parsed questions and dynamically creates one database column per question, so no manual migration is needed when the survey changes.
4. The front-end fetches the structured survey from `/api/survey` and renders it question by question.
5. Submitted responses are validated, checked for low-effort/fast answers, and persisted; aggregated results are available via `/api/results`.

## Features

- **XML-defined surveys** — add, remove, or reorder questions by editing `data.xml`; no code or schema changes required.
- **Dynamic database schema** — one string column is created per question `id` at startup via SQLAlchemy.
- **Multiple question types** — single-choice, free text, and 5-point Likert scale (`likert-5`) questions.
- **Section-level and question-level options** — define an option set once per section (e.g. a Likert scale) and reuse it across all questions, or override it per question.
- **Image-backed options** — attach an image to any option, either as an XML attribute (`image="..."`) or a child `<Image>` element (e.g. emoji/mood scales).
- **"Other" free-text options** — flag any option with `allowsOtherText="true"` to let respondents add custom text.
- **Low-effort response detection** — a "3-second rule" flags a submission as `is_bad` when more than half of its answers were given in 3 seconds or less.
- **Aggregated results endpoint** — get per-question, per-value response counts for quick analysis.
- **Optional AI-assisted question negation** — questions can be marked with `<AI>yes</AI>` to have an LLM agent (via OpenRouter) automatically rewrite them as a negated statement, useful for balancing Likert-scale questionnaires with reverse-coded items.
- **Embeddable** — response headers are relaxed to allow the survey to be embedded inside an iframe (e.g. a v0/Genially-style preview).
- **Deploy-ready** — ships with a `vercel.json` for one-click deployment to Vercel's Python runtime.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask-SQLAlchemy |
| Database | SQLAlchemy ORM (Postgres via `psycopg2-binary`, or any SQLAlchemy-supported DB) |
| Survey definition | XML (`xml.etree.ElementTree`) |
| Optional AI feature | [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) via [OpenRouter](https://openrouter.ai/) |
| Front-end | Server-rendered Jinja templates (`templates/`) + static assets (`static/`) |
| Deployment | Vercel (`@vercel/python` runtime) |

## Project Structure

```
Data-Survey-System/
├── app.py                   # Flask app: routes, dynamic model, request handling
├── Data_extraction_XML.py   # XML parsing utilities (legacy + extended extractors)
├── AI_integration.py        # Optional LLM-based question negation via OpenRouter
├── data.xml                 # The survey definition (edit this to change the survey)
├── templates/                # Jinja HTML templates (survey UI)
├── static/                   # CSS/JS/images for the front-end
├── instance/                  # Flask instance folder (local SQLite/config, if used)
├── requirements.txt          # Python dependencies
├── package.json              # Convenience npm scripts that just run the Flask app
└── vercel.json                # Vercel deployment configuration
```

## Getting Started

### Prerequisites

- Python 3.10+
- A database URL (Postgres recommended — `psycopg2-binary` is included), or point `DATABASE_URL` at a local SQLite file for quick testing
- (Optional) An [OpenRouter](https://openrouter.ai/) API key if you want the AI question-negation feature

### Installation

```bash
git clone https://github.com/Bilalkhan-cel/Data-Survey-System.git
cd Data-Survey-System

python -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
SESSION_SECRET_KEY=some-long-random-string
OPEN_ROUTER=your-openrouter-api-key   # only needed if any <AI>yes</AI> questions are used
```

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes | SQLAlchemy connection string. Must use the `postgresql://` scheme if using Postgres. |
| `SESSION_SECRET_KEY` | Recommended | Flask session/cookie signing key (defaults to a dev key if unset). |
| `OPEN_ROUTER` | Only if using AI negation | API key used by `AI_integration.py` to call an LLM via OpenRouter. |
| `PORT` | No | Port the app listens on (defaults to `3000`). |

### Run locally

```bash
python app.py
# or, using the provided npm script:
npm run dev
```

The app starts on `http://localhost:3000` and creates the database tables automatically on first run.

## API Reference

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Renders the survey page (intro/outro copy pulled from `data.xml`). |
| `GET` | `/api/survey` | Returns the parsed survey as JSON: title, description, and the full list of questions/options. |
| `POST` | `/api/submit` | Accepts `{ "answers": [{ "id": "...", "value": "...", "response_time": 0 }] }`, validates it, applies the 3-second "bad response" rule, and saves a row. |
| `GET` | `/api/results` | Returns aggregated counts per question/value across all saved responses. |

## Defining a Survey (`data.xml`)

Every survey is a `<Survey>` document with one or more `<Section>` elements, each containing `<Question>` elements:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Survey>
  <Title>Survey Questionnaire</Title>
  <Description>A short description shown on the intro screen.</Description>

  <Section id="1" name="Demographics">
    <Question id="gender" type="single-choice">
      <Text>Gender</Text>
      <Options>
        <Option value="1" image="opt_male.png">Male</Option>
        <Option value="2">
          <Text>Female</Text>
          <Image>opt_female.png</Image>
        </Option>
      </Options>
    </Question>

    <Question id="age" type="text">
      <Text>Name/Reg No.</Text>
    </Question>
  </Section>

  <Section id="2" name="Entrepreneurial Intention">
    <!-- Section-level options are shared by every question below
         that doesn't define its own <Options> -->
    <Options>
      <Option value="1" image="scale_1.png">Strongly Disagree</Option>
      <Option value="2" image="scale_2.png">Disagree</Option>
      <Option value="3" image="scale_3.png">Neutral</Option>
      <Option value="4" image="scale_4.png">Agree</Option>
      <Option value="5" image="scale_5.png">Strongly Agree</Option>
    </Options>

    <Question id="EI1" type="likert-5">
      <Text>I am ready to do anything to be an entrepreneur</Text>
    </Question>
  </Section>
</Survey>
```

Key rules:

- **`id`** on each `<Question>` becomes both the JSON key and the database column name — keep it short and unique.
- **`type`** can be `single-choice`, `text`, `likert-5`, or any custom type your front-end knows how to render.
- **Options** can be defined once per `<Section>` and inherited by all its questions, or overridden per-question by nesting `<Options>` inside a `<Question>`.
- **Images** on an option can use either `image="file.png"` as an attribute or a nested `<Image>file.png</Image>` element.
- **`allowsOtherText="true"`** on an `<Option>` marks it as an "Other, please specify" choice.
- **`<Instruction>`** inside a `<Section>` adds helper text shown above that section's questions.
- **`<AI>yes</AI>`** inside a `<Question>` runs the question text through the optional AI negation agent (see below).

## Data Quality: the 3-Second Rule

When a response is submitted, each answer includes a `response_time` (in seconds). If **more than half** of the answers in a submission were given in **3 seconds or less**, the whole response is flagged with `is_bad = 1` in the database — a simple heuristic for catching respondents who click through without reading the questions. Flagged rows are still saved (not discarded), so you can filter them out during analysis rather than losing data.

## Optional: AI-Assisted Question Negation

`AI_integration.py` wires up an [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) agent that runs against a free model on [OpenRouter](https://openrouter.ai/). When a question in `data.xml` contains `<AI>yes</AI>`, its text is passed through this agent, which is instructed to negate the sentence without breaking its Likert-scale structure — useful for adding reverse-coded items to a scale without writing them by hand. This feature is entirely optional: questions without `<AI>yes</AI>` are unaffected, and the app degrades gracefully (returns `None`/leaves the text unchanged) if `OPEN_ROUTER` isn't set or the call fails.

## Deployment

The repo includes a `vercel.json` configured to deploy `app.py` using the `@vercel/python` runtime, with all routes proxied to the Flask app. To deploy:

1. Push the repo to GitHub.
2. Import it into [Vercel](https://vercel.com/).
3. Add `DATABASE_URL`, `SESSION_SECRET_KEY`, and (optionally) `OPEN_ROUTER` as environment variables in the Vercel project settings.
4. Deploy — Vercel will route all traffic to `app.py`.


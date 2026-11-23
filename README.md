# Hostel Complaint Bot

A chatbot that takes a hostel complaint, works out which team should handle it
and how urgent it is, saves it to a CSV file, and gives the student a complaint
ID.

## Problem statement

Complaints written in a paper register get lost, and nobody knows which ones are
urgent. This bot collects the complaint in a short chat (name, room, problem),
uses an LLM (Claude) to classify it by category and urgency, appends it to a CSV
file the hostel office can open in Excel, and shows the student a complaint ID.

## How it works

1. **The bot asks three questions**, one at a time: name, room, and the problem.
   Answers that are empty, too short or too long get a follow-up question.
2. **The student reviews the details** and presses **Submit complaint**.
3. **The Django API validates the request** and sends only the complaint text to
   Claude with the prompt in [server/complaints/prompts.py](server/complaints/prompts.py).
   The name and room are not sent.
4. **Claude returns JSON**: a category, an urgency and a one-line summary. The
   request uses structured output, so the category and urgency are always one
   of the allowed values.
5. **The complaint is appended to `server/data/complaints.csv`** with the next
   complaint ID (`CMP-0001`, `CMP-0002`, ...).
6. **The bot shows the ID, category and urgency.** For a high-urgency complaint
   it also tells the student to contact the warden or security directly.

If Claude cannot be reached, the complaint is still saved, marked
`unclassified`, so that nothing is lost.

### Categories and urgency

| Category | Covers |
| --- | --- |
| `electrical` | lights, fans, sockets, wiring, power cuts, geysers |
| `water` | no water, leaks, taps, drainage, water quality |
| `mess` | food quality, hygiene, menu, timings |
| `internet` | Wi-Fi, LAN, slow or no connection |
| `cleanliness` | rooms, corridors, toilets, garbage, pests |
| `maintenance` | furniture, doors, locks, windows, lifts |
| `security` | theft, ragging, harassment, personal safety |
| `other` | anything else, and messages that are not a complaint |

| Urgency | Meaning |
| --- | --- |
| `high` | someone could get hurt or fall ill, or an essential service is down for many people |
| `medium` | daily life is disrupted for a room or a few people, with no danger |
| `low` | a minor inconvenience, a suggestion or a request |

### The saved file

`server/data/complaints.csv` is created on the first complaint:

```
complaint_id,submitted_at,name,room,category,urgency,summary,complaint
CMP-0001,2026-11-21 20:29:39,Asha Rao,B-204,electrical,high,Switchboard near bed sparks when charger is plugged in,There are sparks coming from the switchboard near my bed whenever I plug in my charger.
```

## Tech stack

| Part | Used |
| --- | --- |
| LLM | Claude (`claude-opus-5-5` by default), Anthropic Python SDK |
| Server | Python, Django, Django REST Framework, CSV file storage |
| Client | React, TypeScript, Vite, plain CSS |
| Tooling | Django test runner, Ruff, ESLint, npm scripts |

## Requirements

- **Python 3.12 or newer**
- **Node.js 20.19 or newer** (includes npm)
- A **Claude API key** from <https://console.anthropic.com/>

Installing them:

- **Windows:** install Python from <https://www.python.org/downloads/> and tick
  **Add python.exe to PATH** in the installer. Install Node.js (LTS) from
  <https://nodejs.org/>. Then open a new PowerShell window.
- **Ubuntu / Debian:** `sudo apt install python3 python3-venv`, and install
  Node.js from <https://nodejs.org/> or with `nvm` (the version in `apt` is
  often too old).

Check with `python --version` (Linux: `python3 --version`) and `node --version`.

## Quick start (same commands on Linux and Windows)

Run these in a terminal (Linux) or PowerShell (Windows), inside the
`complaint-bot` folder:

```bash
npm run setup
```

This creates the Python environment in `server/.venv`, installs all Python and
Node packages, and creates `server/.env`.

Open `server/.env` and paste your key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Start the app:

```bash
npm run dev
```

Open <http://localhost:5173> and answer the bot's questions. Press `Ctrl+C` in
the terminal to stop. The saved complaints are in `server/data/complaints.csv`.

## Commands

All of these are run from the `complaint-bot` folder and work the same on Linux
and Windows.

| Command | What it does |
| --- | --- |
| `npm run setup` | One-time setup: Python environment, packages, `server/.env` |
| `npm run dev` | Starts the **server and the client together** |
| `npm run server` | Starts only the Django server on <http://localhost:8000> |
| `npm run client` | Starts only the React client on <http://localhost:5173> |
| `npm test` | Runs the server tests (30 tests, no API key or internet needed) |
| `npm run lint` | Checks the Python code (Ruff) and the client code (ESLint, TypeScript) |
| `npm run build` | Builds the client for production into `client/dist` |

## Manual setup

Use this if you prefer to run each step yourself instead of `npm run setup`.

### Linux

Terminal 1, the server:

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then paste your key into .env
python manage.py runserver 8000
```

Terminal 2, the client:

```bash
cd client
npm install
npm run dev
```

### Windows (PowerShell)

Window 1, the server:

```powershell
cd server
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # then paste your key into .env
python manage.py runserver 8000
```

If PowerShell refuses to run `Activate.ps1`, run this once in the same window
and try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

In Command Prompt, the activation command is `.venv\Scripts\activate.bat`.

Window 2, the client:

```powershell
cd client
npm install
npm run dev
```

Then open <http://localhost:5173>.

## Sample complaints to try

| Complaint | Result when tested |
| --- | --- |
| There are sparks coming from the switchboard near my bed | electrical, high |
| Fan is making noise and running very slow since 2 days | electrical, medium |
| No water in the entire C block since morning | water, high |
| mess ka khana aaj bahut kharab tha, dal me keeda mila | mess, high |
| wifi not working on 3rd floor | internet, medium |
| URGENT!!!! please add paneer to the sunday menu | mess, low |

## Settings

Set these in `server/.env`. Only the API key is required.

| Variable | Default | What it does |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | none | Your Claude API key. Required for classification. |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Model to use. `claude-sonnet-5-5` and `claude-haiku-5-5` are cheaper and faster. |
| `TIME_ZONE` | `UTC` | Time zone for the times in the CSV. `.env.example` sets `Asia/Kolkata`. |
| `COMPLAINTS_FILE` | `data/complaints.csv` | Where complaints are saved, relative to `server/`. |
| `DJANGO_DEBUG` | `False` | `True` for local development. `.env.example` sets it to `True`. |
| `DJANGO_SECRET_KEY` | none | Required when `DJANGO_DEBUG` is not `True`. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Host names the server may be reached at. |
| `COMPLAINT_RATE_LIMIT` | `30/min` | How many complaints one network address may send. |

## API

| Method and path | Body | Returns |
| --- | --- | --- |
| `GET /api/v1/health/` | none | `{"status", "model", "api_key_configured"}` |
| `POST /api/v1/complaints/` | `{"name", "room", "complaint"}` | `201` with `{"id", "submitted_at", "category", "urgency", "summary", "classified"}` |

Errors are JSON: `{"detail": "message"}`, or `{"field": ["message"]}` when a
field is invalid.

## Project structure

```
complaint-bot/
├── package.json            the commands in the table above
├── scripts/                setup and start scripts (work on Linux and Windows)
├── server/                 Django API
│   ├── config/             settings, URL routing
│   ├── complaints/
│   │   ├── prompts.py      the prompt sent to Claude
│   │   ├── llm.py          the Claude call and its error handling
│   │   ├── storage.py      appends complaints to the CSV, assigns IDs
│   │   ├── serializers.py  request validation
│   │   ├── views.py        the two endpoints
│   │   └── tests/          tests for all of the above
│   ├── data/               complaints.csv is created here (git-ignored)
│   ├── requirements.txt    pinned runtime packages
│   └── .env.example        template for the settings file
└── client/                 React app
    └── src/
        ├── App.tsx             page layout, submits the complaint
        ├── conversation.ts     the chat as a state machine: what the bot asks and replies
        ├── api.ts              the call to the server
        ├── components/         message bubbles, the input box
        └── styles.css
```

## Engineering practices used

- **A complaint is never lost because the LLM failed.** If Claude is down, slow
  or misconfigured, the complaint is saved as `unclassified` and the student
  still gets an ID.
- **Only the complaint text goes to the LLM.** The student's name and room stay
  on the server, and the server log records IDs and categories, not names or
  complaint text.
- **Safe writes to the file.** A file lock makes "read the last ID, write the
  next row" one step, so two complaints arriving together cannot get the same
  ID or corrupt the file. A test submits 24 complaints at once to check this.
- **The CSV is safe to open in a spreadsheet.** Text that looks like a formula
  is written as plain text (CSV injection protection), and the file has a UTF-8
  byte-order mark so Excel shows Hindi and Marathi text correctly.
- **The LLM reply is structured output** with fixed category and urgency values,
  so nothing unexpected can end up in the file.
- **Secrets and settings come from the environment.** `.env` and the complaints
  file are git-ignored, and the API key never reaches the browser.
- **Input is validated on the server**, and the endpoint is rate limited.
- **Tests do not call the real API.** The Claude call is replaced by a fake, so
  tests are fast, free and repeatable.
- **Pinned dependencies, a linter and a formatter** on both sides, and TypeScript
  in strict mode on the client.

## Limitations

- **There is no login.** Anyone who can open the page can file a complaint under
  any name. A real deployment would sign students in with their college account.
- **There is no screen for staff.** The hostel office reads the CSV file
  directly. Showing complaints in the app would need a login first, because the
  file holds names and room numbers.
- **A CSV file suits one server and a modest number of complaints.** A database
  would be the next step for anything larger.
- **Classification can be wrong.** Staff should treat the category and urgency
  as a first sort, not a final decision.
- **On Windows, close the CSV in Excel before complaints are filed.** Excel
  locks an open file, and the server cannot append to it until it is closed.
- In the CSV, a cell that starts with `=`, `+`, `-` or `@` gets a leading
  apostrophe so spreadsheets do not treat it as a formula.
- If Claude's safety filters decline a complaint, the API re-runs the request on
  a fallback model automatically. This uses a beta feature of the Claude API.

## Troubleshooting

| Message or problem | Fix |
| --- | --- |
| `The Python environment has not been created yet` | Run `npm run setup`. |
| `Python was not found` during setup | Install Python 3.12+ and open a new terminal. On Windows, tick "Add python.exe to PATH". |
| The bot says it can't reach the server | The Django server is not running. Use `npm run dev`, or `npm run server` in another terminal. |
| Complaints are saved as "Not sorted yet" | Claude could not be reached. With `DJANGO_DEBUG=True` the bot shows the reason; usually the key in `server/.env` is missing or wrong. Restart the server after fixing it. |
| "Your complaint could not be saved" | The CSV file is locked or not writable. Close it in Excel and submit again. |
| `Port 5173 is already in use` or `That port is already in use` | Another copy is still running. Close it, or stop the old terminal with `Ctrl+C`. |
| `DJANGO_SECRET_KEY is not set` | `server/.env` is missing. Run `npm run setup`, or copy `server/.env.example` to `server/.env`. |
# complaint-bot

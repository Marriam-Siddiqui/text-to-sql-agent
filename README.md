# Text to SQL Analytics Agent

This is a small app for exploring New York City taxi trips by asking questions in plain English. It shows the SQL behind each answer, so you can see exactly how the data was queried.

The interface is built with React. A FastAPI service passes each question to a LangGraph agent, which uses Groq to write a DuckDB query. The agent checks that the query is a `SELECT` before running it against the trip data.

## Getting started

You will need Python, Node.js with npm, and a Groq API key.

Create and activate a Python environment, then install the backend packages:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` file in the project folder and add your key:

```text
GROQ_API_KEY=your_groq_api_key
```

Prepare the taxi data and start the backend:

```powershell
python build_lakehouse.py
uvicorn main:app
```

The data script downloads the January 2024 Yellow Taxi trip file the first time it runs and builds the DuckDB tables. Keep the backend running in this terminal.

Open another terminal to start the web app:

```powershell
cd frontend
npm install
npm run dev
```

Open the local address printed by Vite, usually `http://localhost:5173`. The API runs at `http://127.0.0.1:8000`.

## A little context

The agent uses the `gold_taxi_trips` table, which is prepared from the raw trip data. Ask a question such as “What is the average trip distance?” and the app will show the generated SQL alongside the result.

Your API key, downloaded trip data, generated database, and exported CSV stay out of the Git repository. The data and database can be recreated by running `build_lakehouse.py`.
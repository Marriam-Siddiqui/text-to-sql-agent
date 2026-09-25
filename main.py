from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sql_agent import app as agent_graph  # reuse the compiled LangGraph app

app = FastAPI(title="Text-to-SQL Analytics Agent")

# Why CORS: React (running on localhost:3000/5173) and FastAPI (localhost:8000)
# are different origins in the browser's eyes. Without this, the browser
# blocks the request before it even reaches your API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Question(BaseModel):
    question: str


@app.post("/ask")
def ask_question(payload: Question):
    initial_state = {
        "question": payload.question,
        "schema": "",
        "sql": "",
        "result": None,
        "error": None,
        "retries": 0,
        "final_answer": ""
    }
    final_state = agent_graph.invoke(initial_state)
    return {
        "question": payload.question,
        "sql": final_state["sql"],
        "result": final_state["result"],
        "error": final_state["error"],
        "final_answer": final_state["final_answer"]
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
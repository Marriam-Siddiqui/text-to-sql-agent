import os
import duckdb
from dotenv import load_dotenv
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq

load_dotenv()

DB_FILE = "lakehouse.duckdb"
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

# --- STATE: what flows through the graph, node to node ---
class AgentState(TypedDict):
    question: str
    schema: str
    sql: str
    result: Optional[str]
    error: Optional[str]
    retries: int
    final_answer: str


# --- NODE 1: get schema ---
# Why: the LLM can't guess column names correctly. We hand it the real
# schema every time so it grounds its SQL in what actually exists.
def get_schema(state: AgentState) -> AgentState:
    con = duckdb.connect(DB_FILE, read_only=True)
    cols = con.execute("DESCRIBE gold_taxi_trips").fetchall()
    con.close()
    schema_str = "Table: gold_taxi_trips\nColumns:\n"
    for col_name, col_type, *_ in cols:
        schema_str += f"  - {col_name} ({col_type})\n"
    state["schema"] = schema_str
    return state


# --- NODE 2: generate SQL ---
# Why: this is the actual "text-to-SQL" step. We give strict instructions
# so the model returns raw SQL only, not markdown or explanations.
def generate_sql(state: AgentState) -> AgentState:
    error_context = ""
    if state.get("error"):
        error_context = f"\nYour previous SQL failed with this error:\n{state['error']}\nFix it."

    prompt = f"""You are a DuckDB SQL expert. Given this schema:

{state['schema']}

Write a SINGLE valid DuckDB SELECT query to answer this question:
"{state['question']}"

Rules:
- Only SELECT statements. Never write/modify data.
- Return ONLY the raw SQL, no markdown, no explanation, no ```sql fences.
{error_context}
"""
    response = llm.invoke(prompt)
    sql = response.content.strip().strip("```sql").strip("```").strip()
    state["sql"] = sql
    return state


# --- NODE 3: validate SQL ---
# Why: a safety guardrail. Even with prompt instructions, never trust
# an LLM to self-police. We hard-block anything that isn't a SELECT.
def validate_sql(state: AgentState) -> AgentState:
    sql_upper = state["sql"].strip().upper()
    forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]
    if not sql_upper.startswith("SELECT") or any(word in sql_upper for word in forbidden):
        state["error"] = "Blocked: only SELECT queries are allowed."
        state["result"] = None
    else:
        state["error"] = None
    return state


# --- NODE 4: execute SQL ---
# Why: actually run it against DuckDB. If it fails, capture the error
# so generate_sql can see it and fix itself on the next loop.
def execute_sql(state: AgentState) -> AgentState:
    if state.get("error"):  # already blocked in validation
        state["retries"] += 1
        return state
    try:
        con = duckdb.connect(DB_FILE, read_only=True)
        result = con.execute(state["sql"]).fetchdf()
        con.close()
        state["result"] = result.to_string(index=False)
        state["error"] = None
    except Exception as e:
        state["error"] = str(e)
        state["result"] = None
        state["retries"] += 1
    return state


# --- NODE 5: decide whether to retry or finish ---
# Why: this is the loop-back logic. Max 3 retries so a bad question
# doesn't cause an infinite loop.
def should_retry(state: AgentState) -> str:
    if state["error"] and state["retries"] < 3:
        return "retry"
    return "finish"


# --- NODE 6: format final answer ---
def format_answer(state: AgentState) -> AgentState:
    if state["error"]:
        state["final_answer"] = f"Couldn't get a valid answer after {state['retries']} tries.\nLast error: {state['error']}"
    else:
        state["final_answer"] = f"SQL used:\n{state['sql']}\n\nResult:\n{state['result']}"
    return state


# --- BUILD THE GRAPH ---
graph = StateGraph(AgentState)
graph.add_node("get_schema", get_schema)
graph.add_node("generate_sql", generate_sql)
graph.add_node("validate_sql", validate_sql)
graph.add_node("execute_sql", execute_sql)
graph.add_node("format_answer", format_answer)

graph.set_entry_point("get_schema")
graph.add_edge("get_schema", "generate_sql")
graph.add_edge("generate_sql", "validate_sql")
graph.add_edge("validate_sql", "execute_sql")
graph.add_conditional_edges("execute_sql", should_retry, {
    "retry": "generate_sql",
    "finish": "format_answer"
})
graph.add_edge("format_answer", END)

app = graph.compile()


# --- TEST RUN ---
if __name__ == "__main__":
    question = input("Ask a question about the taxi data: ")
    initial_state = {
        "question": question,
        "schema": "",
        "sql": "",
        "result": None,
        "error": None,
        "retries": 0,
        "final_answer": ""
    }
    final_state = app.invoke(initial_state)
    print("\n" + final_state["final_answer"])
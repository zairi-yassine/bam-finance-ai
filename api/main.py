from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent.graph import agent
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BAM Financial AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], # L'adresse de ton frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask")
def ask(request: QuestionRequest):
    try:
        result = agent.invoke({"question": request.question})
        return {
            "answer": result.get("answer"),
            "sql": result.get("sql_query")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
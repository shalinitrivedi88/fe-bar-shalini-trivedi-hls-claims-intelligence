from fastapi import APIRouter
from pydantic import BaseModel
from .. import db

router = APIRouter()

SYSTEM = ("You answer claims-operations questions for a health-plan claims processor "
          "concisely and factually. If asked to triage a specific claim, return the risk "
          "and the next action with a one-line rationale.")


class Ask(BaseModel):
    question: str


@router.post("/api/chat")
def chat(body: Ask):
    return {"answer": db.chat(SYSTEM, body.question)}

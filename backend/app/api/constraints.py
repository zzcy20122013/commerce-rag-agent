from fastapi import APIRouter
from pydantic import BaseModel

from app.services.constraint_parser import parse_constraints


router = APIRouter(prefix="/api/constraints", tags=["constraints"])


class ConstraintParseRequest(BaseModel):
    query: str


@router.post("/parse")
def parse_constraint_request(payload: ConstraintParseRequest) -> dict:
    return {"success": True, "data": parse_constraints(payload.query), "message": "ok"}

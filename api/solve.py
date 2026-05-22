from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from api.solver import solve_schedule

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PreAssignment(BaseModel):
    doctor_index: int
    area: str
    period: int

class Doctor(BaseModel):
    id: str
    name: str
    is_exempt: bool = False
    target_total_minutes: Optional[int] = None

class ScheduleRequest(BaseModel):
    doctors: List[Doctor]
    pre_assignments: List[PreAssignment] = []

@app.post("/api/solve")
def solve_endpoint(request: ScheduleRequest):
    data = request.model_dump()
    result = solve_schedule(data)
    if result["status"] == "success":
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("message", "No solution found"))

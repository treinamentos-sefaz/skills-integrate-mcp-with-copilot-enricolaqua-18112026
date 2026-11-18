"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import logging
import os
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

if __package__:
    from .auth import verify_teacher
else:
    from auth import verify_teacher

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

logger = logging.getLogger(__name__)
sessions: dict[str, float] = {}
sessions_lock = threading.Lock()
SESSION_SECONDS = 8 * 60 * 60


class LoginCredentials(BaseModel):
    username: str
    password: str


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).netloc != request.headers.get("host"):
        raise HTTPException(status_code=403, detail="Invalid request origin")
    if origin and urlsplit(origin).scheme != request.url.scheme:
        raise HTTPException(status_code=403, detail="Invalid request origin")


def require_teacher(request: Request) -> None:
    check_origin(request)
    token = request.cookies.get("teacher_session")
    with sessions_lock:
        expires = sessions.get(token, 0) if token else 0
        if expires <= time.monotonic():
            if token:
                sessions.pop(token, None)
            raise HTTPException(status_code=401, detail="Teacher login required")


@app.post("/auth/login")
def login(credentials: LoginCredentials, request: Request, response: Response):
    check_origin(request)
    try:
        valid = verify_teacher(credentials.username, credentials.password)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        logger.exception("Could not read teacher credentials")
        raise HTTPException(status_code=503, detail="Teacher login is not configured") from exc
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = secrets.token_urlsafe(32)
    with sessions_lock:
        now = time.monotonic()
        for expired in [key for key, expiry in sessions.items() if expiry <= now]:
            del sessions[expired]
        sessions[token] = now + SESSION_SECONDS
    response.set_cookie(
        "teacher_session", token, max_age=SESSION_SECONDS, httponly=True,
        samesite="strict", secure=request.url.scheme == "https",
    )
    return {"message": "Logged in"}


@app.get("/auth/session")
def session_status(request: Request):
    try:
        require_teacher(request)
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
        return {"authenticated": False}
    return {"authenticated": True}


@app.post("/auth/logout", dependencies=[Depends(require_teacher)])
def logout(request: Request, response: Response):
    token = request.cookies.get("teacher_session")
    with sessions_lock:
        if token:
            sessions.pop(token, None)
    response.delete_cookie("teacher_session")
    return {"message": "Logged out"}


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup", dependencies=[Depends(require_teacher)])
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister", dependencies=[Depends(require_teacher)])
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}

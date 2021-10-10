""" Main API module """
import logging
from typing import List, Dict

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from apscheduler.schedulers.background import BackgroundScheduler

from auth import authenticate_user, create_token, create_new_user, get_current_user, \
    check_user_by_permissions, OAUTH_2_SCHEME
from config import NOTIFICATION_CHECK_DURATION
from database.queries.user_queries import (
    get_user_by_username_with_permissions,
    get_users_by_institution_with_roles
)
from database.queries.prescriptions_queries import (
    get_prescriptions_by_user
)
from models.auth import BaseUser, User, BaseUserWithPermissions, UserWithRoles
from models.base import Response
from permissions import PermissionsChecker
from jobs.prescription_notification import process_prescription_notifications

from routers import (
    roles,
    users,
    medical_practices,
    pending_users,
    pharmacies,
    prescriptions,
    medication,
    bloodwork_requests
)

LOGGER = logging.getLogger(__name__)

SCHEDULER = BackgroundScheduler()

SCHEDULER.add_job(process_prescription_notifications, 'interval', minutes=NOTIFICATION_CHECK_DURATION)
SCHEDULER.start()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roles.router, prefix="/roles", tags=['user-management'])
app.include_router(users.router, prefix="/users", tags=['user-management'])
app.include_router(medical_practices.router, prefix="/medical-practices", tags=['medical-practices'])
app.include_router(pending_users.router, prefix='/pending-users', tags=['pending-users'])
app.include_router(pharmacies.router, prefix='/pharmacies', tags=['pharmacies'])
app.include_router(prescriptions.router, prefix='/prescriptions', tags=['prescriptions'])
app.include_router(medication.router, prefix='/medication', tags=['medication'])
app.include_router(bloodwork_requests.router, prefix='/bloodwork-requests', tags=['bloodwork-requests'])
@app.get("/")
async def root():
    """ Health check endpoint """
    LOGGER.info('Test endpoint')
    return {"message": "ok"}

@app.post("/token", tags=['authentication'])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """ Login a user and return a token if correct """
    if (user := authenticate_user(username=form_data.username, password=form_data.password)) is None:
        LOGGER.debug("User auth failed for %s", form_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")
    access_token = create_token(username=user.username)
    LOGGER.info("Token generated for user %s", form_data.username)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=Response[Dict], status_code=status.HTTP_201_CREATED)
async def register(form_data: User):
    if  (username := create_new_user(form_data)) is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating new user")
    LOGGER.info("New user created %s", username)
    return {"data": {"username": username}}

@app.get("/users",
    response_model=Response[List[UserWithRoles]],
)
def list_users(user: User = Depends(PermissionsChecker(['users.list']))):
    """ List all users with roles for the given users institution. """
    return {'data': [UserWithRoles(**user)
            for user in get_users_by_institution_with_roles(institution_id=user.institution_id)]}

@app.get("/me",
    response_model=Response[BaseUserWithPermissions]
)
def me(user: User = Depends(get_current_user)):
    if (user_and_permissions := next(get_user_by_username_with_permissions(user.username), None)) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or permissions not found.")

    return {'data': user_and_permissions}


@app.get("/dashboard")
def patient_dashboard(user: User = Depends(get_current_user)):
    """ Get patient information for display on a dashboard """
    def _format_object(prescription):
        return {
            'prescription_id': prescription['prescription_id'],
            'pharmacy_name': prescription['pharmacy_name'],
            'medication_name': prescription['medication_name'],
            'approved_at': prescription['approved_at'],
            'issued_at': prescription['issued_at'],
            'bloodwork_completed_at': prescription['bloodwork_completed_at'],
            'bloodwork_requirement': prescription['bloodwork_requirement']
        }
    formatted_prescriptions = [_format_object(rp) for rp in get_prescriptions_by_user(user.username)]
    return {
        'repeat_prescriptions': formatted_prescriptions
    }

""" Endpoints relating to medications """
from typing import List
from fastapi import APIRouter, Depends

from database.queries.medication_queries import get_medications
from models.medication import Medication
from models.base import Response
from permissions import PermissionsChecker

router = APIRouter()

@router.get("",
    dependencies=[Depends(PermissionsChecker(['medications.get-all']))],
    response_model=Response[List[Medication]]
)
def get_all_medication():
    """ Get a list of all stored medicines. """
    return {"data": [Medication(**m) for m in get_medications()]}

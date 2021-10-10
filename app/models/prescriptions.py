from datetime import datetime

from pydantic import BaseModel, validator, Field

from helpers import check_valid_uuid

def check_uuid(value: str) -> str:
    if not check_valid_uuid(value):
        raise ValueError('Must be UUID type')
    return str(value)

class BasePrescription(BaseModel):
    medication_id: str
    time_statement: str
    _normalize_medication_id = validator('medication_id', allow_reuse=True)(check_uuid)

class Prescription(BasePrescription):
    prescription_id: str
    username: str
    approved_at: datetime = Field(None)
    issued_at: datetime = Field(None)
    issued_by: str = Field(None)
    institution_id: str
    short_code: str = Field(None)
 
class PrescriptionModifyRequest(BaseModel):
    time_statement: str = Field(None)
    medication_id: str = Field(None)

    _normalize_medication_id = validator('medication_id', allow_reuse=True)(check_uuid)


class PrescriptionCreatedResponse(BaseModel):
    prescription_id: str
    bloodwork_request_id: str = Field(None)


class PrescriptionListing(Prescription):
    medication_name: str
    bloodwork_requirement: int = Field(None)
    name: str
    request_id: str = Field(None)

from pydantic import BaseModel, Field
from datetime import datetime

from models.medication import MedicationBloodworkTypes

class BloodworkRequest(BaseModel):
    request_id: str
    practice_id: str
    prescription_id: str
    request_type: MedicationBloodworkTypes
    completed_at: datetime = Field(None)

class BloodworkListing(BloodworkRequest):
    username: str
    name: str
    pharmacy_name: str
    medication_name: str
    pharmacy_name: str

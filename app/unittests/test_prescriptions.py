import unittest
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from models.base import Institution, InstitutionTypes, PharmacyPreference
from models.bloodwork import BloodworkRequest
from models.medication import Medication, MedicationBloodworkTypes
from models.prescriptions import BasePrescription, Prescription, PrescriptionListing
from metomi.isodatetime.exceptions import ISO8601SyntaxError
from metomi.isodatetime.parsers import TimeRecurrenceParser


from main import app
from routers.prescriptions import _get_prescription

from unittests.common_test_utils import MOCK_USER, MOCK_BASE_USER

client = TestClient(app)

# Disable permission and authentication checking.
@patch('permissions.check_user_by_permissions', return_value=MOCK_USER)
@patch('permissions.get_current_user', return_value=MOCK_USER)
class TestPrescriptions(unittest.TestCase):
    def setUp(self):
        self.mock_prescription = BasePrescription(
            medication_id='3724e951-7e07-4aab-9060-fdf6b23034c3',
            time_statement='R/2021-01-01/P30D',
        )
        self.mock_medical_practice = Institution(
            name='Test Medical Practice',
            address_line_1='31 Spooner Street',
            address_line_2='Quahog',
            address_line_3='Newport County',
            address_line_4='Tiverton',
            city='Quahog',
            state='Rhode Island',
            postcode='000093',
            institution_id='a894fd80-aa24-4b89-a480-b6f55997eb76',
            institution_type=InstitutionTypes.MEDICAL_PRACTICE
        )
        self.mock_stored_pharmacy = Institution(
            name='Test Pharmacy',
            address_line_1='31 Spooner Street',
            address_line_2='Quahog',
            address_line_3='Newport County',
            address_line_4='Tiverton',
            city='Quahog',
            state='Rhode Island',
            postcode='000093',
            institution_id='98899a91-385b-4264-a048-bf281c48d376',
            institution_type=InstitutionTypes.PHARMACY
        )
        self.mock_medication = Medication(
            medication_id='3049363c-0e2a-4a59-b0f6-3710718d92cb',
            medication_name='Pie'
        )
        self.mock_prescription_id = "d89f540f-7e7a-4819-80f3-a57dcf0ff204"
        self.mock_stored_prescription = Prescription(
            prescription_id=self.mock_prescription_id,
            username='Bill Oddy',
            institution_id=MOCK_USER.institution_id,
            **self.mock_prescription.dict()
        )
        self.mock_pharmacy_assignment = PharmacyPreference(
            institution_id=self.mock_stored_pharmacy.institution_id,
            username='boddy'
        )

    @patch('routers.prescriptions.get_user_by_username')
    def test_throws_400_when_unknown_user_passed(self, mock_get_user_by_username, *_):
        mock_get_user_by_username.return_value = iter([None])

        res = client.post('/prescriptions/randomuser1/create', json=self.mock_prescription.dict())

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'User not found.')

    @patch('routers.prescriptions.get_user_by_username')
    @patch('routers.prescriptions.get_medical_practice')
    def test_throws_400_when_medical_practice_not_found(self, mock_get_medical_practice, mock_get_user_by_username, *_):
        mock_get_user_by_username.return_value = iter([MOCK_USER.dict()])
        mock_get_medical_practice.return_value = None

        res = client.post('/prescriptions/randomuser1/create', json=self.mock_prescription.dict())

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'Institution invalid.')

    @patch('routers.prescriptions.get_users_pharmacy_assignment')
    @patch('routers.prescriptions.get_user_by_username')
    @patch('routers.prescriptions.get_medical_practice')
    def test_throws_400_when_pharmacy_assignment_not_found(
        self,
        mock_get_medical_practice,
        mock_get_user_by_username,
        mock_get_users_pharmacy_assignment,
        *_
    ):
        mock_get_user_by_username.return_value = iter([MOCK_USER.dict()])
        mock_get_medical_practice.return_value = self.mock_medical_practice
        mock_get_users_pharmacy_assignment.return_value = None

        res = client.post('/prescriptions/randomuser1/create', json=self.mock_prescription.dict())

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'Pharmacy assignment not found.')

    @patch('routers.prescriptions.get_users_pharmacy_assignment')
    @patch.object(TimeRecurrenceParser, 'parse')
    @patch('routers.prescriptions.get_medication_by_id')
    @patch('routers.prescriptions.get_user_by_username')
    @patch('routers.prescriptions.get_medical_practice')
    def test_throws_400_when_timestatement_invalid(self, mock_get_medical_practice, mock_get_user_by_username, mock_get_medication, mock_time_parser, *_):
        mock_get_user_by_username.return_value = iter([MOCK_USER.dict()])
        mock_get_medical_practice.return_value = self.mock_medical_practice

        mock_get_medication.return_value = self.mock_medication.dict()
        mock_time_parser.side_effect = ISO8601SyntaxError()

        res = client.post('/prescriptions/randomuser1/create', json=self.mock_prescription.dict())

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'Time statement invalid.')

    @patch('routers.prescriptions.get_users_pharmacy_assignment')
    @patch('routers.prescriptions.get_medication_by_id')
    @patch('routers.prescriptions.get_user_by_username')
    @patch('routers.prescriptions.get_medical_practice')
    def test_throws_400_when_invalid_medication(self, mock_get_medical_practice, mock_get_user_by_username, mock_get_medication, *_):
        mock_get_user_by_username.return_value = iter([MOCK_USER.dict()])
        mock_get_medical_practice.return_value = self.mock_medical_practice

        mock_get_medication.return_value = None

        res = client.post('/prescriptions/randomuser1/create', json=self.mock_prescription.dict())

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'Medication invalid.')

    @patch('routers.prescriptions.get_users_pharmacy_assignment')
    @patch('routers.prescriptions.get_medication_by_id')
    @patch('routers.prescriptions.get_user_by_username')
    @patch('routers.prescriptions.get_medical_practice')
    def test_throws_400_when_patient_not_in_medical_practice(self, mock_get_medical_practice, mock_get_user_by_username, mock_get_medication, *_):
        mock_get_user_by_username.return_value = iter([MOCK_USER.dict()])
        mock_get_medical_practice.side_effect = [self.mock_medical_practice.dict(), None]
        mock_get_medication.return_value = self.mock_medication.dict()

        res = client.post('/prescriptions/randomuser1/create', json=self.mock_prescription.dict())

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'User does not belong to medical practice.')

    @patch('routers.prescriptions.get_users_pharmacy_assignment')
    @patch('routers.prescriptions.create_bloodwork_request')
    @patch('routers.prescriptions.create_prescription')
    @patch('routers.prescriptions.get_medication_by_id')
    @patch('routers.prescriptions.get_user_by_username')
    @patch('routers.prescriptions.get_pharmacy')
    @patch('routers.prescriptions.get_medical_practice')
    def test_creates_bloodwork_request_when_mandated_by_medication(self,
        mock_get_medical_practice,
        mock_get_pharmacy,
        mock_get_user_by_username,
        mock_get_medication,
        mock_create_prescription,
        mock_create_bloodwork,
        *_
    ):
        mock_prescription_id = 'd50fc55d-2554-487b-9cd2-32b65bcecebd'
        mock_bloodwork_request_id = 'f4a1995b-0d63-4d37-8a2c-5760f3b71694'

        # mock 'checker' queries
        mock_get_user_by_username.return_value = iter([MOCK_USER.dict()])
        mock_get_pharmacy.return_value = self.mock_stored_pharmacy.dict()
        mock_get_medical_practice.return_value = self.mock_medical_practice
        mock_get_medication.return_value = Medication(**self.mock_medication.dict(exclude={'bloodwork_requirement'}), 
            bloodwork_requirement=MedicationBloodworkTypes.BLOOD_PRESSURE).dict()

        # mock database return values
        mock_create_prescription.return_value = mock_prescription_id
        mock_create_bloodwork.return_value = mock_bloodwork_request_id

        res = client.post('/prescriptions/randomuser1/create', json=self.mock_prescription.dict())

        mock_create_prescription.assert_called_once()
        mock_create_bloodwork.assert_called_once_with(
            prescription_id=mock_prescription_id,
            practice_id=MOCK_USER.institution_id,
            request_type=MedicationBloodworkTypes.BLOOD_PRESSURE.value
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.json()['prescription_id'], mock_prescription_id)
        self.assertEqual(res.json()['bloodwork_request_id'], mock_bloodwork_request_id)

    @patch('routers.prescriptions.get_prescription')
    def test_prescription_modify_throws_404_when_not_found(self, mock_get_prescription, *_):
        mock_get_prescription.return_value = None
        app.dependency_overrides[_get_prescription] = _get_prescription

        res = client.patch(f'/prescriptions/{self.mock_prescription_id}', json={'medication_id': '3facb015-620a-4168-9ae2-bc37014ea9fc'})

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.json()['detail'], 'Prescription not found.')

    @patch('routers.prescriptions.get_medication_by_id')
    @patch('routers.prescriptions.get_prescription')
    def test_prescription_modify_throws_400_when_non_existent_medication_given(self, mock_get_prescription, mock_get_medication, *_):
        mock_get_prescription.return_value = self.mock_stored_prescription.dict()

        mock_get_medication.return_value = None

        res = client.patch(f'/prescriptions/{self.mock_prescription_id}', json={'medication_id': '3facb015-620a-4168-9ae2-bc37014ea9fc'})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'Medication invalid.')

    @patch('routers.prescriptions.update_prescription')
    @patch('routers.prescriptions.check_iso8601_time_statement')
    @patch('routers.prescriptions.get_medication_by_id')
    @patch('routers.prescriptions.get_prescription')
    def test_calls_check_timestatement_method_when_given(self, mock_get_prescription, mock_get_medication, mock_time_check, *_):
        mock_get_prescription.return_value = self.mock_stored_prescription.dict()
        mock_get_medication.return_value = self.mock_medication.dict()

        res = client.patch(f'/prescriptions/{self.mock_prescription_id}', json={'time_statement': 'R/2021-01-01/P30D'})

        mock_time_check.assert_called_once()
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    @patch('routers.prescriptions.update_prescription')
    @patch('routers.prescriptions.check_medication')
    @patch('routers.prescriptions.get_medication_by_id')
    @patch('routers.prescriptions.get_prescription')
    def test_calls_check_medication_method_when_given(self, mock_get_prescription, mock_get_medication, mock_check_medication, *_):
        mock_get_prescription.return_value = self.mock_stored_prescription.dict()
        mock_get_medication.return_value = self.mock_medication.dict()

        res = client.patch(f'/prescriptions/{self.mock_prescription_id}', json={'medication_id': '3facb015-620a-4168-9ae2-bc37014ea9fc'})

        mock_check_medication.assert_called_once()
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    @patch('routers.prescriptions.update_prescription')
    @patch('routers.prescriptions.get_prescription')
    @patch('routers.prescriptions.get_medication_by_id')
    def test_calls_update_query_when_valid(self, mock_get_medication, mock_get_prescription, mock_update, *_):
        mock_get_medication.return_value = self.mock_medication.dict()
        mock_get_prescription.return_value = self.mock_stored_prescription.dict()
        mock_new_medication_id = '3facb015-620a-4168-9ae2-bc37014ea9fc'

        mock_update.return_value = self.mock_stored_prescription.prescription_id

        res = client.patch(f'/prescriptions/{self.mock_prescription_id}', json={'medication_id': mock_new_medication_id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # assert called with an updated attribute.
        mock_update.assert_called_once_with(Prescription(**self.mock_stored_prescription.dict(exclude={'medication_id'}), medication_id=mock_new_medication_id))

    @patch('routers.prescriptions.delete_prescription')
    @patch('routers.prescriptions.get_prescription')
    def test_delete_user_repeat_prescription_returns_204_when_prescription_is_successfully_deleted(self, mock_get_prescription, mock_delete_prescription, *_):
        mock_get_prescription.return_value = self.mock_stored_prescription.dict()
        mock_delete_prescription.return_value = True

        res = client.delete(f'/prescriptions/{self.mock_prescription_id}')

        mock_get_prescription.assert_called_with(prescription_id=self.mock_prescription_id)
        mock_delete_prescription.assert_called_with(prescription_id=self.mock_prescription_id)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    @patch('routers.prescriptions.delete_prescription')
    @patch('routers.prescriptions.get_prescription')
    def test_delete_user_repeat_prescription_returns_404_when_prescription_could_not_be_found(self, mock_get_prescription, mock_delete_prescription, *_):
        mock_get_prescription.return_value = None
        mock_delete_prescription.return_value = True
        app.dependency_overrides[_get_prescription] = _get_prescription

        res = client.delete(f'/prescriptions/{self.mock_prescription_id}')

        mock_get_prescription.assert_called_with(prescription_id=self.mock_prescription_id)
        mock_delete_prescription.assert_not_called()

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.json()['detail'], 'Prescription not found.')

    @patch('routers.prescriptions.delete_prescription')
    @patch('routers.prescriptions.get_prescription')
    def test_delete_user_repeat_prescription_returns_422_when_prescription_id_is_malformed(self, mock_get_prescription, mock_delete_prescription, *_):
        mock_get_prescription.return_value = self.mock_prescription.dict()
        mock_delete_prescription.return_value = True

        res = client.delete(f'/prescriptions/not{self.mock_prescription_id}')

        mock_get_prescription.assert_not_called()
        mock_delete_prescription.assert_not_called()

        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(res.json()['detail'], 'Malformed UUID detected.')

    @patch('routers.prescriptions.delete_prescription')
    def test_delete_user_repeat_prescription_returns_500_when_database_query_fails(self, mock_delete_prescription, *_):
        app.dependency_overrides[_get_prescription] = lambda: self.mock_stored_prescription
        mock_delete_prescription.return_value = False

        res = client.delete(f'/prescriptions/{self.mock_prescription_id}')

        mock_delete_prescription.assert_called_with(prescription_id=self.mock_prescription_id)

        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(res.json()['detail'], 'Lost connection to the database')


    # GET Prescriptions
    @patch('routers.prescriptions.get_prescriptions_of_institution')
    def test_prescriptions_of_institution_of_user_can_be_fetched(self, mock_get_prescriptions, *_):
        mock_prescription_listing = PrescriptionListing(
            medication_id="0cb652cf-01d5-4de7-8cc2-b333d71facbd",
            time_statement="R/2021-01-01T00:00:00Z/P30D",
            prescription_id="f66330e8-2a87-4268-bafb-ca20eb57b706",
            username="body",
            medication_name="Parecetemol",
            bloodwork_requirement=1,
            name="Bill Oddy",
            request_id="dc17f205-c9bb-4df6-bd29-7d7ec2c3c442",
            institution_id=self.mock_medical_practice.institution_id
        )
        mock_get_prescriptions.return_value = iter([mock_prescription_listing.dict()])

        res = client.get('/prescriptions')
        mock_get_prescriptions.assert_called_once_with(MOCK_USER.institution_id)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    # APPROVE Prescriptions.
    @patch('routers.prescriptions.mark_prescription_approved')
    def test_prescription_cannot_be_approved_when_already_approved(self, mock_mark_prescription, *_):
        mock_prescription = Prescription(
            **self.mock_stored_prescription.dict(exclude={'approved_at'}),
            approved_at='2021-02-11T09:16:51.476934'
        )
        app.dependency_overrides[_get_prescription] = lambda: mock_prescription

        res = client.patch(f'/prescriptions/{self.mock_stored_prescription.prescription_id}/approve')

        mock_mark_prescription.assert_not_called()

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'Prescription already approved.')

    @patch('routers.prescriptions.get_bloodwork_request_for_prescription')
    @patch('routers.prescriptions.mark_prescription_approved')
    def test_prescription_can_be_marked_as_approved(self, mock_mark_prescription, mock_get_bloodwork, *_):
        app.dependency_overrides[_get_prescription] = lambda: self.mock_stored_prescription

        # mark the bloodwork request as complete
        mock_get_bloodwork.return_value = {
            'request_id': 'bf3153b1-94a1-4015-9d7e-4fa96647c488', 
            'completed_at': '2021-02-11T09:16:51.476934'
        }

        res = client.patch(f'/prescriptions/{self.mock_stored_prescription.prescription_id}/approve')

        mock_mark_prescription.assert_called_once_with(prescription_id=self.mock_stored_prescription.prescription_id)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    @patch('routers.prescriptions.get_bloodwork_request_for_prescription')
    @patch('routers.prescriptions.mark_prescription_approved')
    def test_prescripion_cannot_be_marked_as_approved_when_attached_bloodwork_pending(self, mock_mark_prescription, mock_get_bloodwork, *_):
        app.dependency_overrides[_get_prescription] = lambda: self.mock_stored_prescription

        mock_get_bloodwork.return_value = {'request_id': 'bf3153b1-94a1-4015-9d7e-4fa96647c488', 'completed_at': None}

        res = client.patch(f'/prescriptions/{self.mock_stored_prescription.prescription_id}/approve')

        mock_mark_prescription.assert_not_called()

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'Bloodwork incomplete.')

    @patch('routers.prescriptions.get_bloodwork_request_for_prescription')
    @patch('routers.prescriptions.mark_prescription_approved')
    def test_prescription_can_be_marked_as_approved_when_bloodwork_not_attached(self, mock_mark_prescription, mock_get_bloodwork, *_):
        app.dependency_overrides[_get_prescription] = lambda: self.mock_stored_prescription

        mock_get_bloodwork.return_value = {'request_id': None, 'completed_at': None}

        res = client.patch(f'/prescriptions/{self.mock_stored_prescription.prescription_id}/approve')

        mock_get_bloodwork.assert_called_once_with(prescription_id=self.mock_stored_prescription.prescription_id)
        mock_mark_prescription.assert_called_once_with(prescription_id=self.mock_stored_prescription.prescription_id)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    # ISSUE Medication.
    @patch('routers.prescriptions.mark_prescription_issued')
    def test_prescription_cannot_be_issued_when_not_approved(self, mock_prescription_issued, *_):
        app.dependency_overrides[_get_prescription] = lambda: Prescription(
            **self.mock_stored_prescription.dict(exclude={'approved_at'}),
            approved_at=None
        )

        res = client.patch(f'/prescriptions/{self.mock_stored_prescription.prescription_id}/issue')

        mock_prescription_issued.assert_not_called()

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'Prescription not approved for issue.')

    @patch('routers.prescriptions.mark_prescription_issued')
    def test_prescription_cannot_be_issued_when_already_issued(self, mock_prescription_issued, *_):
        app.dependency_overrides[_get_prescription] = lambda: Prescription(
            **self.mock_stored_prescription.dict(exclude={'approved_at', 'issued_at'}),
            approved_at='2021-02-11T09:16:51.476934',
            issued_at='2021-02-11T09:16:51.476934'
        )

        res = client.patch(f'/prescriptions/{self.mock_stored_prescription.prescription_id}/issue')

        mock_prescription_issued.assert_not_called()

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'Prescription already issued.')


    @patch('routers.prescriptions.mark_prescription_issued')
    def test_prescription_cannot_be_issued_by_technican_from_different_insitutition(self, mock_prescription_issued, *_):
        app.dependency_overrides[_get_prescription] = lambda: Prescription(
            **self.mock_stored_prescription.dict(exclude={'approved_at', 'institution_id'}),
            institution_id='fa6f3179-feed-4cea-8bee-c7b6bbbf99b7',
            approved_at=None
        )

        res = client.patch(f'/prescriptions/{self.mock_stored_prescription.prescription_id}/issue')

        mock_prescription_issued.assert_not_called()

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.json()['detail'], 'Wrong institution.')

    @patch('routers.prescriptions.mark_prescription_issued')
    def test_prescription_can_be_issued(self, mock_prescription_issued, *_):
        app.dependency_overrides[_get_prescription] = lambda: Prescription(
            **self.mock_stored_prescription.dict(exclude={'approved_at'}),
            approved_at='2021-02-11T09:16:51.476934'
        )

        res = client.patch(f'/prescriptions/{self.mock_stored_prescription.prescription_id}/issue')

        mock_prescription_issued.assert_called_once_with(
            prescription_id=self.mock_stored_prescription.prescription_id,
            issuing_user=MOCK_USER.username
        )

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    # SHORT Code Prescription Retrieval
    @patch('routers.prescriptions.get_prescription_by_code')
    def test_short_code_throws_404_when_not_found(self, mock_get_by_code, *_):
        mock_get_by_code.return_value = None

        res = client.get('/prescriptions/code/12345678')

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.json()['detail'], 'Prescription not found.')

    @patch('routers.prescriptions._get_prescription')
    @patch('routers.prescriptions.get_prescription_by_code')
    def test_can_retrieve_prescription_by_short_code(self, mock_get_by_code, mock_get_prescription, *_):
        mock_short_code = '12345678'
        mock_get_by_code.return_value = {'prescription_id': self.mock_stored_prescription.prescription_id}
        mock_get_prescription.return_value = self.mock_stored_prescription

        res = client.get(f'/prescriptions/code/{mock_short_code}')

        mock_get_by_code.assert_called_once_with(mock_short_code)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

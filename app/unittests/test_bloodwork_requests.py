import unittest
from unittest.mock import patch
from datetime import datetime

from fastapi import status
from fastapi.testclient import TestClient

from main import app
from auth import OAUTH_2_SCHEME 

from models.bloodwork import BloodworkRequest, BloodworkListing
from models.medication import MedicationBloodworkTypes

from unittests.common_test_utils import MOCK_USER, MOCK_BASE_USER

client = TestClient(app)

@patch('permissions.check_user_by_permissions', return_value=MOCK_USER)
@patch('permissions.get_current_user', return_value=MOCK_USER)
class TestBloodworkRequests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[OAUTH_2_SCHEME] = lambda: 'token'
        self.mock_bloodwork_request = BloodworkListing(
            request_id='dc17f205-c9bb-4df6-bd29-7d7ec2c3c442',
            practice_id=MOCK_USER.institution_id,
            prescription_id='f66330e8-2a87-4268-bafb-ca20eb57b706',
            request_type=MedicationBloodworkTypes.BLOOD_PRESSURE,
            completed_at=None,
            username='ttest',
            name='Testy McTestFace',
            pharmacy_name='Poop mc Plop Pharmacy',
            medication_name='Paracetemol'
        )
        self.mock_practice_id = '4e186db0-fcf7-49b6-9173-c414f71cb60d'
    # GET Bloodwork Request
    @patch('routers.bloodwork_requests.get_request_by_id_in_practice')
    def test_bloodwork_request_can_be_found_in_user_institution(self, mock_get_request_in_practice, *_):
        mock_get_request_in_practice.return_value = self.mock_bloodwork_request.dict()

        res = client.get(f'/bloodwork-requests/{self.mock_bloodwork_request.request_id}')

        mock_get_request_in_practice.assert_called_once_with(
            request_id=self.mock_bloodwork_request.request_id, 
            practice_id=MOCK_USER.institution_id
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    @patch('routers.bloodwork_requests.get_request_by_id_in_practice')
    def test_bloodwork_request_throws_404_when_not_found(self, mock_get_request_in_practice, *_):
        mock_get_request_in_practice.return_value = None

        res = client.get(f'/bloodwork-requests/{self.mock_bloodwork_request.request_id}')

        mock_get_request_in_practice.assert_called_once_with(
            request_id=self.mock_bloodwork_request.request_id, 
            practice_id=MOCK_USER.institution_id
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # GET Bloodwork Requests
    @patch('routers.bloodwork_requests.get_requests_by_practice')
    def test_pending_requests_can_be_retrieved_by_default(self, mock_get_requests_by_practice, *_):
        mock_get_requests_by_practice.return_value = [self.mock_bloodwork_request.dict()]

        res = client.get('/bloodwork-requests')

        mock_get_requests_by_practice.assert_called_once_with(practice_id=MOCK_USER.institution_id, completed=False)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
    
    @patch('routers.bloodwork_requests.get_requests_by_practice')
    def test_all_requests_can_be_retrieved_when_query_param_given(self, mock_get_requests_by_practice, *_):
        mock_get_requests_by_practice.return_value = [self.mock_bloodwork_request.dict()]

        res = client.get('/bloodwork-requests?completed=true')

        mock_get_requests_by_practice.assert_called_once_with(practice_id=MOCK_USER.institution_id, completed=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    # MARK Requests as completed.
    @patch('routers.bloodwork_requests.mark_bloodwork_request_complete')
    @patch('routers.bloodwork_requests.get_request_by_id')
    def test_request_can_be_marked_as_completed(self, mock_get_request, mock_mark_complete, *_):
        mock_get_request.return_value = self.mock_bloodwork_request.dict()

        res = client.patch(f'/bloodwork-requests/{self.mock_bloodwork_request.request_id}/complete', json={})

        mock_mark_complete.assert_called_once_with(request_id=self.mock_bloodwork_request.request_id)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    @patch('routers.bloodwork_requests.mark_bloodwork_request_complete')
    @patch('routers.bloodwork_requests.get_request_by_id')
    def test_throws_404_for_mark_complete_on_non_exitent_request(self, mock_get_request, mock_mark_complete, *_):
        mock_get_request.return_value = None

        res = client.patch(f'/bloodwork-requests/{self.mock_bloodwork_request.request_id}/complete', json={})

        mock_mark_complete.assert_not_called()

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.json()['detail'], 'Bloodwork request not found.')

    @patch('routers.bloodwork_requests.mark_bloodwork_request_complete')
    @patch('routers.bloodwork_requests.get_request_by_id')
    def test_throws_404_when_user_not_part_of_medical_practice_of_request(self, mock_get_request, mock_mark_complete, *_):
        mock_different_practice_id = 'c8124bcb-c146-4b3b-b599-ea48d186b936'
        mock_get_request.return_value = BloodworkRequest(
            **self.mock_bloodwork_request.dict(exclude={'practice_id'}),
            practice_id=mock_different_practice_id
        ).dict()

        res = client.patch(f'/bloodwork-requests/{self.mock_bloodwork_request.request_id}/complete', json={})

        mock_mark_complete.assert_not_called()

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.json()['detail'], 'Bloodwork request not found.')

    @patch('routers.bloodwork_requests.mark_bloodwork_request_complete')
    @patch('routers.bloodwork_requests.get_request_by_id')
    def test_throws_400_when_request_already_marked_as_complete(self, mock_get_request, mock_mark_complete, *_):
        mock_get_request.return_value = BloodworkRequest(
            **self.mock_bloodwork_request.dict(exclude={'completed_at'}),
            completed_at=datetime.utcnow().isoformat()
        ).dict()

        res = client.patch(f'/bloodwork-requests/{self.mock_bloodwork_request.request_id}/complete', json={})

        mock_mark_complete.assert_not_called()

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'Bloodwork request already completed.')

import unittest
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from main import app
from auth import OAUTH_2_SCHEME

from unittests.common_test_utils import MOCK_USER, MOCK_BASE_USER 

client = TestClient(app)

# Disable permission and authentication checking.
@patch('permissions.check_user_by_permissions', return_value=MOCK_USER)
@patch('permissions.get_current_user', return_value=MOCK_USER)
class TestMedicalPractices(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[OAUTH_2_SCHEME] = lambda: 'token'
        self.mock_practice_id = '33de4e85-d3ee-499f-ba2e-85ef1aa09277'

    @patch('routers.medical_practices.get_medical_practice')
    def test_throws_404_when_registering_gp_with_bad_medical_practice(self, mock_get_medical_practice, *_):
        mock_get_medical_practice.return_value = None

        response = client.post('/medical-practices/register/GP', json={
            'username': 'pmcplop',
            'name': 'Poop Mc Plop',
            'email': 'test@test.com'
        })

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Practice not found')

    @patch('routers.medical_practices.check_valid_uuid')
    def test_throws_404_when_uuid_check_fails(self, mock_check_valid_uuid, *_):
        mock_check_valid_uuid.return_value = False

        response = client.post('/medical-practices/register/GP', json={
            'username': 'pmcclop',
            'name': 'Poop Mc Plop Peake',
            'email': 'test@test.com'
        })

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Practice not found')

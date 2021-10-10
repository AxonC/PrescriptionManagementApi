import unittest
from unittest.mock import patch

from fastapi import status, HTTPException
from fastapi.testclient import TestClient

from models.base import InstitutionTypes, RegistrationType
from models.auth import BaseUser, BaseUserWithInstitution
from models.permissions_roles import CoreRoles
from models.registration_tokens import RegistrationToken
from routers.pending_users import _check_registration_token

from main import app

client = TestClient(app)

class TestPendingUsers(unittest.TestCase):
    def setUp(self):
        self.mock_pending_user = BaseUserWithInstitution(
            username='PendingUser',
            email='test@test.com',
            name='Pending User',
            institution_id='b7f895bd-31ac-41d2-9515-46b3c1a559ad'
        )
        self.mock_registration_token = RegistrationToken(
            token_id='eeac173b-3742-46b0-9edd-cfb495660aaf',
            token_type=RegistrationType.GP.value,
            username='PendingUser'
        )
        self.endpoint = "/pending-users/convert"

    @patch('routers.pending_users.add_role_to_user')
    @patch('routers.pending_users.delete_pending_user')
    @patch('routers.pending_users.get_pending_user_by_username')
    @patch('routers.pending_users.create_new_user')
    def test_pending_user_can_be_converted(self, mock_create_new_user, mock_get_pending_user, mock_delete_pending_user, mock_add_role):
        # pass the token check
        app.dependency_overrides[_check_registration_token] = lambda: self.mock_registration_token

        mock_get_pending_user.return_value = iter([{**self.mock_pending_user.dict(), 'institution_type': InstitutionTypes.MEDICAL_PRACTICE}])

        response = client.post(self.endpoint, json={
            'user_type': RegistrationType.GP.value,
            'password': 'test_password',
            'registration_token': str(self.mock_registration_token.token_id)
        })

        mock_create_new_user.assert_called_once()
        mock_add_role.assert_called_once()
        mock_delete_pending_user.assert_called_with(username=self.mock_registration_token.username)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('routers.pending_users.add_role_to_user')
    @patch('routers.pending_users.delete_pending_user')
    @patch('routers.pending_users.get_pending_user_by_username')
    @patch('routers.pending_users.create_new_user')
    def test_pending_user_can_be_converted_as_gp(self, mock_create_new_user, mock_get_pending_user, mock_delete_pending_user, mock_role_assign):
        # pass the token check
        app.dependency_overrides[_check_registration_token] = lambda: self.mock_registration_token

        mock_get_pending_user.return_value = iter([{**self.mock_pending_user.dict(), 'institution_type': InstitutionTypes.MEDICAL_PRACTICE.value}])

        response = client.post(self.endpoint, json={
            'user_type': RegistrationType.GP.value,
            'password': 'test_password',
            'registration_token': str(self.mock_registration_token.token_id)
        })

        mock_create_new_user.assert_called_once()
        mock_role_assign.assert_called_once_with(username=self.mock_pending_user.username, role_id=CoreRoles.GP.value)

        mock_delete_pending_user.assert_called_with(username=self.mock_registration_token.username)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('routers.pending_users.get_pending_user_by_username')
    def test_throws_400_when_user_not_found(self, mock_get_pending_user_by_username):
        app.dependency_overrides[_check_registration_token] = lambda: self.mock_registration_token

        mock_get_pending_user_by_username.return_value = iter(())

        response = client.post(self.endpoint,
            json={
                'user_type': RegistrationType.GP.value,
                'password': 'test_password',
                'registration_token': 'test-token'   
            })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'User does not exist')

    @patch('routers.pending_users.create_new_user')
    @patch('routers.pending_users.get_pending_user_by_username')
    def test_throws_400_when_user_cannot_be_converted(self, mock_get_pending_user, mock_create_new_user):
        # pass the token check
        app.dependency_overrides[_check_registration_token] = lambda: self.mock_registration_token

        mock_get_pending_user.return_value = iter([{**self.mock_pending_user.dict(), 'institution_type': InstitutionTypes.MEDICAL_PRACTICE.value}])

        mock_create_new_user.return_value = False

        response = client.post(self.endpoint, json={
            'user_type': RegistrationType.GP.value,
            'password': 'test_password',
            'registration_token': str(self.mock_registration_token.token_id)
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'Error creating user')

    @patch('routers.pending_users.get_active_token')
    def test_check_registration_token_throws_401_when_invalid(self, mock_get_active_token):
        mock_get_active_token.return_value = iter(())

        with self.assertRaises(HTTPException) as exception: 
            _check_registration_token(self.mock_registration_token.token_id)
        self.assertEqual(exception.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(exception.exception.detail, 'Registration token invalid')

    def test_check_registration_token_throws_401_when_not_valid_string(self):
        with self.assertRaises(HTTPException) as exception:
            _check_registration_token('invalid-token')
        self.assertEqual(exception.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(exception.exception.detail, 'Registration token invalid')

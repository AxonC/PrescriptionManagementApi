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
class TestUsersEndpoint(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[OAUTH_2_SCHEME] = lambda: 'token'

    @patch('main.get_users_by_institution_with_roles')
    def test_gets_institution_users(self, mock_get_users, *_):
        mock_get_users.return_value = iter([{**MOCK_USER.dict(), 'roles': ['developer']}])

        res = client.get('/users')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

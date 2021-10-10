import unittest
from unittest.mock import patch

from main import app

from uuid import UUID

from fastapi import status
from fastapi.testclient import TestClient

from auth import get_current_user
from models.auth import User, BaseUserWithPermissions
from models.permissions_roles import Permission

client = TestClient(app)

class MeEndpointunittests(unittest.TestCase):
    def setUp(self):
        self.mock_current_user = User(username='tmctestface', name='Testy McTestFace', password='test-pwd', email='test@test.com')
        self.mock_me_permissions_model = [
            Permission(permission_id=UUID('9ddfdc47-9663-4aaf-ac0b-ec86e717d420'), name='test.permission')
        ]
        self.mock_me_model = BaseUserWithPermissions(username='tmctestface', name='Testy McTestFace', email='test@test.com', permissions=self.mock_me_permissions_model)
        
        app.dependency_overrides[get_current_user] = lambda: self.mock_current_user

    @patch('main.get_user_by_username_with_permissions')
    def test_me_returns_user_model_with_permissions(self, mock_get_me):
        mock_get_me.return_value = iter([self.mock_me_model])

        response = client.get("/me")
        mock_get_me.assert_called_with(self.mock_current_user.username)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

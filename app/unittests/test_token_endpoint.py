import unittest
from unittest.mock import patch

from main import app

from fastapi import status
from fastapi.testclient import TestClient

from models.auth import BaseUser

client = TestClient(app)

class TokenEndpointUnittests(unittest.TestCase):
    def setUp(self):
        self.mock_payload = {'username': 'test', 'password': 'test-password'}
    
    @patch('main.authenticate_user')
    def test_returns_exception_when_user_not_authenticated(self, mock_authenticate_user):
        mock_authenticate_user.return_value = None

        response = client.post("/token", data=self.mock_payload)

        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual("Unauthorized.", response.json()['detail'])

    @patch('main.create_token')
    @patch('main.authenticate_user')
    def test_returns_token_when_generated(self, mock_authenticate_user, mock_create_token):
        mock_authenticate_user.return_value = BaseUser(username='Username', name='name', email='test@test.com')
        mock_create_token.return_value = 'access_token'

        response = client.post("/token", data=self.mock_payload)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual('access_token', response.json()['access_token'])

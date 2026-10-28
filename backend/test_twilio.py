import unittest
import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from fastapi_app import app
from database import db_session, SessionLocal
from models.company import Company
from models.user import User, UserRole
from models.purchased_number import PurchasedNumber

class TestTwilioIntegration(unittest.TestCase):
    """
    Test suite for programmatical phone number search, validation, and purchasing
    using Twilio Magic Numbers (+15005550006, +15005550000, +15005550001).
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        
        # Setup a mock company & user for JWT mock authorization
        cls.company = Company.query.filter_by(name="Test Twilio Corp").first()
        if not cls.company:
            cls.company = Company(
                name="Test Twilio Corp",
                agent_name="TwilioBot",
                api_keys={
                    "twilio_sid": "ACmocktestaccountdetails12345",
                    "twilio_token": "mock_auth_token_for_validation"
                }
            )
            db_session.add(cls.company)
            db_session.flush()
            
        cls.user = User.query.filter_by(email="twilio_tester@pymai.com").first()
        if not cls.user:
            cls.user = User(
                email="twilio_tester@pymai.com",
                name="Twilio Tester",
                role=UserRole.ADMIN,
                company_id=cls.company.id
            )
            cls.user.set_password("SecurePassword123")
            db_session.add(cls.user)
            
        db_session.commit()
        cls.company_id = cls.company.id
        cls.user_id = cls.user.id

    def _get_headers(self) -> dict:
        """Helper to get JWT authorization headers for endpoints."""
        from utils.auth_fastapi import create_access_token
        access_token = create_access_token(data={"sub": str(self.user_id)})
        return {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json'
        }

    def test_01_validate_credentials_success(self):
        """Test validation of credentials endpoint (mocked success)"""
        # We mock requests.get to simulate Twilio account validation API
        import unittest.mock as mock
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            
            payload = {
                'account_sid': 'ACmockedsuccesssid',
                'auth_token': 'mocked_auth_token'
            }
            response = self.client.post(
                '/api/v1/twilio/validate-credentials',
                json=payload,
                headers=self._get_headers()
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data.get('success'))
            self.assertIn('public_key', data)

    def test_02_validate_credentials_unauthorized(self):
        """Test credentials validation with invalid keys (HTTP 401)"""
        import unittest.mock as mock
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 401
            
            payload = {
                'account_sid': 'ACbadcredentials',
                'auth_token': 'wrong_token'
            }
            response = self.client.post(
                '/api/v1/twilio/validate-credentials',
                json=payload,
                headers=self._get_headers()
            )
            self.assertEqual(response.status_code, 401)

    def test_03_purchase_magic_number_success(self):
        """Test successful purchase using Twilio Magic Number +15005550006"""
        payload = {
            'phoneNumber': '+15005550006'
        }
        response = self.client.post(
            '/api/v1/twilio/purchase-number',
            json=payload,
            headers=self._get_headers()
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data['number']['phone_number'], '+15005550006')

    def test_04_purchase_magic_number_unavailable(self):
        """Test error when purchasing unavailable Magic Number +15005550000"""
        payload = {
            'phoneNumber': '+15005550000'
        }
        response = self.client.post(
            '/api/v1/twilio/purchase-number',
            json=payload,
            headers=self._get_headers()
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data.get('code'), 21440) # Twilio error code for number unavailable

    def test_05_purchase_magic_number_insufficient_funds(self):
        """Test error when purchasing with insufficient funds Magic Number +15005550001"""
        payload = {
            'phoneNumber': '+15005550001'
        }
        response = self.client.post(
            '/api/v1/twilio/purchase-number',
            json=payload,
            headers=self._get_headers()
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data.get('code'), 21005) # Twilio error code for insufficient funds

if __name__ == '__main__':
    unittest.main()

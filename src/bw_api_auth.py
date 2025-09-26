#!/usr/bin/env python3
"""
Bitwarden Public API Authentication Module

Handles OAuth2 client credentials authentication for the Bitwarden Public API.
"""

import os
import requests
import datetime
import logging
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional, Tuple

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class BitwardenAPIAuth:
    """Handle Bitwarden Public API authentication using OAuth2 client credentials."""

    def __init__(self, log_dir: str = "../logs"):
        self.server_url = "https://vault.bitwarden.com/"
        self.api_url = "https://api.bitwarden.com"
        self.identity_url = "https://identity.bitwarden.com/connect/token"
        self.groups_url = f"{self.api_url}/public/groups"
        self.collections_url = f"{self.api_url}/public/collections"

        self.organization_id = os.getenv('BW_ORGID')
        self.client_id = os.getenv('BW_ORGCLIENTID')
        self.client_secret = os.getenv('BW_ORGCLIENTSECRET')

        self.bearer_token: Optional[str] = None
        self.bearer_timeout: Optional[datetime.datetime] = None

        self._setup_logging(log_dir)
        self._validate_credentials()

    def _setup_logging(self, log_dir: str):
        """Set up dedicated logging for API authentication."""
        # Convert relative path to absolute from script location
        if not Path(log_dir).is_absolute():
            log_path = Path(__file__).parent.parent / log_dir.lstrip("../")
        else:
            log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Create timestamped log file for API authentication
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = log_path / f"api_auth_{timestamp}.log"

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # File handler
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Set up logger
        self.logger = logging.getLogger(f"BitwardenAPIAuth_{timestamp}")
        self.logger.setLevel(logging.DEBUG)

        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info(" Bitwarden API Authentication logging initialized")
        self.logger.info(f" Log file: {log_filename}")

    def _validate_credentials(self):
        """Validate that all required credentials are present."""
        required_vars = ['BW_ORGID', 'BW_ORGCLIENTID', 'BW_ORGCLIENTSECRET']

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            self.logger.error(f" Missing required environment variables: {', '.join(missing_vars)}")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        self.logger.info(" All required credentials found")
        self.logger.debug(f" Organization ID: {self.organization_id}")
        self.logger.debug(f" Client ID: {self.client_id[:20]}...")

    def get_auth_bearer_token(self) -> Tuple[str, datetime.datetime]:
        """
        Get OAuth2 bearer token for Bitwarden Public API.

        Returns:
            Tuple of (bearer_token, expiry_time)
        """
        auth_data = {
            "grant_type": "client_credentials",
            "scope": "api.organization",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            self.logger.info(" Requesting bearer token from Bitwarden API...")
            self.logger.debug(f" Token URL: {self.identity_url}")
            response = requests.post(self.identity_url, headers=headers, data=auth_data)
            response.raise_for_status()

            token_data = response.json()
            token_expiry = token_data["expires_in"]
            bearer_token = str(token_data["access_token"].strip())
            bearer_timeout = datetime.datetime.now() + datetime.timedelta(seconds=token_expiry)

            self.bearer_token = bearer_token
            self.bearer_timeout = bearer_timeout

            self.logger.info(f" Bearer token obtained successfully")
            self.logger.info(f" Token expires at: {bearer_timeout}")
            self.logger.debug(f" Token: {bearer_token[:30]}...")
            return bearer_token, bearer_timeout

        except requests.exceptions.RequestException as e:
            self.logger.error(f" Failed to obtain bearer token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f" Response: {e.response.text}")
            raise
        except KeyError as e:
            self.logger.error(f" Unexpected token response format: {e}")
            raise

    def is_token_valid(self) -> bool:
        """Check if current token is still valid."""
        if not self.bearer_token or not self.bearer_timeout:
            return False

        # Add 60 second buffer before expiry
        return datetime.datetime.now() < (self.bearer_timeout - datetime.timedelta(seconds=60))

    def get_valid_token(self) -> str:
        """Get a valid bearer token, refreshing if necessary."""
        if not self.is_token_valid():
            self.logger.info(" Token expired or missing, obtaining new token...")
            self.get_auth_bearer_token()
        else:
            self.logger.debug(" Using existing valid token")

        return self.bearer_token

    def get_auth_headers(self) -> dict:
        """Get authorization headers for API requests."""
        token = self.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def make_api_request(self, method: str, endpoint: str, data: dict = None) -> requests.Response:
        """
        Make an authenticated request to the Bitwarden API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/public/groups')
            data: Request data (for POST/PUT requests)

        Returns:
            Response object
        """
        url = f"{self.api_url}{endpoint}"
        headers = self.get_auth_headers()

        try:
            self.logger.info(f" API Request: {method.upper()} {url}")
            if data:
                self.logger.debug(f"📤 Request data: {data}")

            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            self.logger.info(f" API Request successful: {response.status_code}")
            return response

        except requests.exceptions.RequestException as e:
            self.logger.error(f" API request failed: {method} {url} - {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f" Response: {e.response.text}")
            raise


def main():
    """Test authentication functionality."""
    try:
        auth = BitwardenAPIAuth()

        # Test token acquisition
        token, expiry = auth.get_auth_bearer_token()
        print(f" Authentication successful")
        print(f"Token: {token[:20]}...")
        print(f"Expires: {expiry}")

        # Test API request (list groups)
        response = auth.make_api_request('GET', '/public/groups')
        print(f" API request successful: {response.status_code}")

        groups_data = response.json()
        print(f" Found {len(groups_data.get('data', []))} existing groups")

    except Exception as e:
        print(f" Authentication test failed: {e}")


if __name__ == "__main__":
    main()
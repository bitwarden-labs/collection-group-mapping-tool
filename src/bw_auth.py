#!/usr/bin/env python3
"""
Bitwarden CLI Authentication Module

Handles authentication and session management for the Bitwarden CLI tool.
"""

import os
import subprocess
import logging
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BitwardenAuth:
    """Handle Bitwarden CLI authentication and session management."""

    def __init__(self):
        self.bw_cmd = "bw"
        self.session_key = None
        self.organization_id = os.getenv('BW_ORGID')
        self.username = os.getenv('BW_USERNAME')
        self.master_password = os.getenv('BW_MASTERPASSWORD')
        self.client_id = os.getenv('BW_USERCLIENTID')
        self.client_secret = os.getenv('BW_USERCLIENTSECRET')

        self._validate_credentials()

    def _validate_credentials(self):
        """Validate that all required credentials are present."""
        required_vars = [
            'BW_ORGID', 'BW_USERNAME', 'BW_MASTERPASSWORD',
            'BW_USERCLIENTID', 'BW_USERCLIENTSECRET'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def logout(self):
        """Logout from Bitwarden CLI."""
        try:
            result = subprocess.run([self.bw_cmd, "logout"],
                                  capture_output=True, text=True, check=False)
            logger.info("Logged out from Bitwarden CLI")
            return True
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False

    def login(self):
        """Authenticate with Bitwarden CLI using API key."""
        try:
            # Set environment variables for the CLI
            env = os.environ.copy()
            env["BW_CLIENTID"] = self.client_id
            env["BW_CLIENTSECRET"] = self.client_secret

            # Login with API key
            result = subprocess.run(
                [self.bw_cmd, "login", "--apikey"],
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("Successfully authenticated with Bitwarden CLI")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Login failed: {e.stderr}")
            return False

    def unlock(self):
        """Unlock the vault and get session key."""
        try:
            # Unlock vault and get session key
            result = subprocess.run(
                [self.bw_cmd, "unlock", self.master_password, "--raw"],
                capture_output=True,
                text=True,
                check=True
            )

            self.session_key = result.stdout.strip()
            logger.info("Vault unlocked successfully")
            return self.session_key

        except subprocess.CalledProcessError as e:
            logger.error(f"Unlock failed: {e.stderr}")
            return None

    def authenticate(self):
        """Complete authentication flow: logout, login, and unlock."""
        logger.info("Starting Bitwarden CLI authentication...")

        # Step 1: Logout (reset any existing session)
        self.logout()

        # Step 2: Login with API key
        if not self.login():
            raise Exception("Authentication failed")

        # Step 3: Unlock vault
        session_key = self.unlock()
        if not session_key:
            raise Exception("Vault unlock failed")

        logger.info("Bitwarden CLI authentication complete")
        return session_key

    def run_command(self, command_args, use_session=True, input_data=None):
        """Run a Bitwarden CLI command with proper session handling."""
        if use_session and self.session_key:
            command_args.extend(["--session", self.session_key])

        try:
            result = subprocess.run(
                [self.bw_cmd] + command_args,
                input=input_data,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(command_args)}")
            logger.error(f"Error: {e.stderr}")
            raise


def main():
    """Test authentication functionality."""
    try:
        auth = BitwardenAuth()
        session_key = auth.authenticate()
        print(f"✓ Authentication successful")
        print(f"Session key: {session_key[:20]}...")

        # Test a simple command
        result = auth.run_command(["status"])
        print(f"✓ Status command successful")

    except Exception as e:
        print(f"✗ Authentication failed: {e}")


if __name__ == "__main__":
    main()
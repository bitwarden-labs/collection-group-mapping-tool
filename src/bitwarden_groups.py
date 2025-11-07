#!/usr/bin/env python3
"""
Bitwarden Groups Management Module (INT-249)

Creates groups using the Bitwarden Public API.
"""

import json
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path

from csv_parser import CollectionPermissionParser
from bw_api_auth import BitwardenAPIAuth
from bulk_logger import BulkLogger


class BitwardenGroupsManager:
    """Manage Bitwarden Groups via Public API based on CSV input."""

    def __init__(self, csv_path: str, log_dir: str = "../logs"):
        self.csv_path = Path(csv_path)
        self.parser = CollectionPermissionParser(csv_path)
        self.api_auth = BitwardenAPIAuth(log_dir)
        self.logger = BulkLogger(log_dir, "group_management")

        self.groups_data: List[str] = []
        self.created_groups: Dict[str, str] = {}  # group_name -> group_id

    def extract_groups_from_csv(self) -> List[str]:
        """
        Extract group names from CSV headers (columns).

        Returns:
            List of group names from CSV columns
        """
        try:
            self.logger.logger.info(" Parsing CSV headers for group extraction...")

            parsed_data = self.parser.parse()
            self.groups_data = parsed_data['groups']

            self.logger.logger.info(f" Found {len(self.groups_data)} groups in CSV:")
            for group in self.groups_data:
                self.logger.logger.info(f"    {group}")

            return self.groups_data

        except Exception as e:
            self.logger.logger.error(f" Failed to parse CSV: {e}")
            raise

    def validate_group_names(self) -> bool:
        """
        Validate group names against Bitwarden requirements.

        Returns:
            True if all group names are valid
        """
        valid = True

        for group_name in self.groups_data:
            if not group_name or len(group_name.strip()) == 0:
                self.logger.logger.error(f" Empty group name found")
                valid = False
            else:
                self.logger.logger.debug(f" Valid group name: '{group_name}'")

        return valid

    def check_existing_groups(self) -> Dict[str, str]:
        """
        Check for existing groups.  Groups with existing names will not be reacreated to avoid duplicates.

        Returns:
            Dict mapping group_name -> group_id for existing groups
        """
        try:
            self.logger.logger.info(" Checking for existing groups...")

            response = self.api_auth.make_api_request('GET', '/public/groups')
            groups_response = response.json()

            existing_groups = {}
            if 'data' in groups_response:
                for group in groups_response['data']:
                    group_name = group.get('name', '')
                    group_id = group.get('id', '')
                    existing_groups[group_name] = group_id

            self.logger.logger.info(f" Found {len(existing_groups)} existing groups:")
            for name, group_id in existing_groups.items():
                self.logger.logger.info(f"    Group Name: '{name}' → objectID: {group_id}")

            return existing_groups

        except Exception as e:
            self.logger.logger.error(f" Failed to check existing groups: {e}")
            raise

    def create_group(self, group_name: str) -> Optional[str]:
        """
        Create a single group via Bitwarden Public API.

        Args:
            group_name: Name of the group to create

        Returns:
            Group ID if successful, None if failed
        """
        try:
            self.logger.logger.info(f" Creating group: '{group_name}'")

            # Prepare group data according to GroupCreateUpdateRequestModel
            group_data = {
                "name": group_name,
                "externalId": None,
                "collections": []
            }

            response = self.api_auth.make_api_request('POST', '/public/groups', group_data)
            group_response = response.json()

            group_id = group_response.get('id')
            if group_id:
                self.logger.log_group_created(group_name, group_id, self.api_auth.organization_id)
                return group_id
            else:
                error_msg = f"No group ID returned in response: {group_response}"
                self.logger.log_group_failed(group_name, self.api_auth.organization_id, error_msg)
                return None

        except Exception as e:
            error_msg = f"API request failed: {str(e)}"
            self.logger.log_group_failed(group_name, self.api_auth.organization_id, error_msg)
            return None

    def create_all_groups(self, skip_existing: bool = True) -> Dict[str, str]:
        """
        Create all groups from CSV, optionally skipping existing ones.

        Args:
            skip_existing: Whether to skip groups that already exist

        Returns:
            Dict mapping group_name -> group_id for all groups (created + existing)
        """
        self.logger.logger.info("=" * 60)
        self.logger.logger.info(" STARTING GROUP CREATION PROCESS")
        self.logger.logger.info("=" * 60)

        try:
            # Step 1: Extract groups from CSV
            self.extract_groups_from_csv()

            # Step 2: Validate group names
            if not self.validate_group_names():
                raise ValueError("Group validation failed")

            # Step 3: Check existing groups
            existing_groups = self.check_existing_groups() if skip_existing else {}

            # Step 4: Create new groups
            all_groups = existing_groups.copy()
            groups_to_create = []

            for group_name in self.groups_data:
                if group_name in existing_groups:
                    self.logger.logger.info(f"  Skipping existing group: '{group_name}'")
                else:
                    groups_to_create.append(group_name)

            self.logger.logger.info(f" Groups to create: {len(groups_to_create)}")
            self.logger.logger.info(f" Groups to skip: {len(existing_groups)}")

            # Create each new group
            skipped_count = len(existing_groups)
            created_count = 0
            failed_count = 0

            for group_name in groups_to_create:
                group_id = self.create_group(group_name)
                if group_id:
                    all_groups[group_name] = group_id
                    created_count += 1
                else:
                    failed_count += 1

            self.created_groups = all_groups

            # Final summary
            total_attempted = len(groups_to_create)
            self.logger.finalise_operation(
                "Group Creation",
                total_attempted,
                created_count,
                str(self.csv_path),
                skipped_count
            )

            self.logger.logger.info("=" * 60)
            self.logger.logger.info(" GROUP CREATION PROCESS COMPLETE")
            self.logger.logger.info("=" * 60)

            return all_groups

        except Exception as e:
            self.logger.logger.error(f" Group creation process failed: {e}")
            raise

    def get_created_groups(self) -> Dict[str, str]:
        """Get mapping of created group names to IDs."""
        return self.created_groups.copy()

    def export_groups_mapping(self, output_file: str = None) -> str:
        """
        Export group name -> ID mapping to JSON file.

        Args:
            output_file: Optional custom output file path

        Returns:
            Path to exported file
        """
        if not output_file:
            timestamp = self.logger.log_data["operation_metadata"]["start_time"].replace(":", "").split(".")[0]
            output_file = f"../output/groups_mapping_{timestamp}.json"

        # Convert relative path to absolute from script location
        if not Path(output_file).is_absolute():
            output_path = Path(__file__).parent.parent / output_file.lstrip("../")
        else:
            output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.created_groups, f, indent=2)

        self.logger.logger.info(f" Groups mapping exported to: {output_path}")
        return str(output_path)


def main():
    """Main entry point for group creation from CSV."""
    try:
        # Initialise groups manager
        csv_path = "../input/collections_permissions.csv"
        groups_manager = BitwardenGroupsManager(csv_path)

        # Create all groups
        created_groups = groups_manager.create_all_groups()

        print(f" Group creation completed!")
        print(f" Total groups available: {len(created_groups)}")

        for name, group_id in created_groups.items():
            print(f"    '{name}' → {group_id}")

        # Export mapping
        mapping_file = groups_manager.export_groups_mapping()
        print(f" Mapping exported to: {mapping_file}")

    except Exception as e:
        print(f" Group creation failed: {e}")


if __name__ == "__main__":
    main()
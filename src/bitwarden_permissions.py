#!/usr/bin/env python3
"""
Bitwarden Permissions Management Module (INT-250)

Handles group-collection permission assignments from CSV input using the Bitwarden Public API.
"""

import json
from typing import List, Dict, Optional, Any
from pathlib import Path

from csv_parser import CollectionPermissionParser
from bw_api_auth import BitwardenAPIAuth
from bulk_logger import BulkLogger


class BitwardenPermissionsManager:
    """Manage Bitwarden Group-Collection permissions via Public API based on CSV input."""

    def __init__(self, csv_path: str, log_dir: str = "../logs"):
        self.csv_path = Path(csv_path)
        self.parser = CollectionPermissionParser(csv_path)
        self.api_auth = BitwardenAPIAuth(log_dir)
        self.logger = BulkLogger(log_dir, "permission_assignment")

        # CSV data
        self.csv_data: Dict = {}
        self.permission_matrix: Dict[str, Dict[str, str]] = {}

        # ID mappings
        self.collection_ids: Dict[str, str] = {}  # collection_path -> collection_id
        self.group_ids: Dict[str, str] = {}      # group_name -> group_id

        # Permission mapping from CSV values to API format
        self.permission_mapping = {
            "Read": {"readOnly": True, "hidePasswords": False, "manage": False},
            "Edit": {"readOnly": False, "hidePasswords": False, "manage": False},
            "Manage": {"readOnly": False, "hidePasswords": False, "manage": True},
            "None": None  # Skip - don't include in collections array
        }

    def parse_csv_permissions(self) -> Dict[str, Dict[str, str]]:
        """
        Parse CSV file to extract permission matrix.

        Returns:
            Dict mapping collection_path -> {group_name: permission_level}
        """
        try:
            self.logger.logger.info(" Parsing CSV file for permission matrix...")

            self.csv_data = self.parser.parse()
            self.permission_matrix = self.csv_data['permissions']

            self.logger.logger.info(f" Found permissions for {len(self.permission_matrix)} collections:")
            for collection_path, group_perms in self.permission_matrix.items():
                self.logger.logger.info(f"    {collection_path}: {group_perms}")

            return self.permission_matrix

        except Exception as e:
            self.logger.logger.error(f" Failed to parse CSV permissions: {e}")
            raise

    def load_collection_ids(self) -> Dict[str, str]:
        """
        Load collection IDs from the most recent collection creation log.

        Returns:
            Dict mapping collection_path -> collection_id
        """
        try:
            self.logger.logger.info(" Loading collection IDs from logs...")

            # Find most recent collection creation log
            log_files = list(Path(self.logger.log_dir).glob("collection_creation_*.json"))
            if not log_files:
                raise FileNotFoundError("No collection creation log files found")

            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            self.logger.logger.info(f" Reading from: {latest_log}")

            with open(latest_log, 'r') as f:
                log_data = json.load(f)

            # Extract collection mappings
            for entry in log_data.get("collections", []):
                if entry.get("status") == "created":
                    collection_path = entry["collection_path"]
                    collection_id = entry["collection_id"]
                    self.collection_ids[collection_path] = collection_id

            self.logger.logger.info(f" Loaded {len(self.collection_ids)} collection IDs:")
            for path, coll_id in self.collection_ids.items():
                self.logger.logger.info(f"    '{path}' → {coll_id}")

            return self.collection_ids

        except Exception as e:
            self.logger.logger.error(f" Failed to load collection IDs: {e}")
            raise

    def load_group_ids(self) -> Dict[str, str]:
        """
        Load group IDs from the most recent group creation output.

        Returns:
            Dict mapping group_name -> group_id
        """
        try:
            self.logger.logger.info(" Loading group IDs from output files...")

            # Find most recent group mapping file
            output_files = list(Path(self.logger.log_dir).parent.glob("output/groups_mapping_*.json"))
            if not output_files:
                raise FileNotFoundError("No group mapping files found")

            latest_mapping = max(output_files, key=lambda x: x.stat().st_mtime)
            self.logger.logger.info(f" Reading from: {latest_mapping}")

            with open(latest_mapping, 'r') as f:
                self.group_ids = json.load(f)

            self.logger.logger.info(f" Loaded {len(self.group_ids)} group IDs:")
            for name, group_id in self.group_ids.items():
                self.logger.logger.info(f"    '{name}' → {group_id}")

            return self.group_ids

        except Exception as e:
            self.logger.logger.error(f" Failed to load group IDs: {e}")
            raise

    def convert_csv_to_api_permissions(self, group_name: str) -> List[Dict[str, Any]]:
        """
        Convert CSV permissions for a group to API format.

        Args:
            group_name: Name of the group to process

        Returns:
            List of AssociationWithPermissionsRequestModel objects
        """
        collections_list = []

        for collection_path, group_perms in self.permission_matrix.items():
            permission_level = group_perms.get(group_name, "None")

            # Skip if no permission or permission is "None"
            if permission_level == "None" or permission_level is None:
                continue

            # Get collection ID
            collection_id = self.collection_ids.get(collection_path)
            if not collection_id:
                self.logger.logger.warning(f"  Collection ID not found for: '{collection_path}'")
                continue

            # Convert permission to API format
            api_permissions = self.permission_mapping.get(permission_level)
            if not api_permissions:
                self.logger.logger.warning(f"  Unknown permission level: '{permission_level}' for {collection_path}")
                continue

            # Create association object
            association = {
                "id": collection_id,
                **api_permissions
            }
            collections_list.append(association)

        self.logger.logger.debug(f" Group '{group_name}' has {len(collections_list)} collection associations")
        return collections_list

    def assign_permissions_to_group(self, group_name: str, group_id: str) -> bool:
        """
        Assign collection permissions to a single group.

        Args:
            group_name: Name of the group
            group_id: UUID of the group

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.logger.info(f" Assigning permissions to group: '{group_name}'")

            # Convert CSV permissions to API format
            collections_list = self.convert_csv_to_api_permissions(group_name)

            # Prepare group update data
            group_data = {
                "name": group_name,
                "externalId": None,
                "collections": collections_list
            }

            # Make API request
            response = self.api_auth.make_api_request('PUT', f'/public/groups/{group_id}', group_data)

            # Log each permission assignment
            for association in collections_list:
                collection_id = association["id"]
                # Find collection path from ID
                collection_path = None
                for path, coll_id in self.collection_ids.items():
                    if coll_id == collection_id:
                        collection_path = path
                        break

                # Determine permission level
                permission_level = "Unknown"
                if association.get("manage"):
                    permission_level = "Manage"
                elif association.get("readOnly"):
                    permission_level = "Read"
                else:
                    permission_level = "Edit"

                self.logger.log_permission_mapped(
                    collection_path or collection_id,
                    collection_id,
                    group_name,
                    group_id,
                    permission_level,
                    self.api_auth.organization_id or ""
                )

            return True

        except Exception as e:
            error_msg = f"API request failed: {str(e)}"
            self.logger.logger.error(f" Failed to assign permissions to '{group_name}': {error_msg}")

            # Log failure for each attempted permission
            for collection_path, group_perms in self.permission_matrix.items():
                permission_level = group_perms.get(group_name, "None")
                if permission_level != "None":
                    self.logger.log_permission_failed(
                        collection_path,
                        group_name,
                        permission_level,
                        self.api_auth.organization_id or "",
                        error_msg
                    )
            return False

    def validate_permissions(self) -> bool:
        """
        Validate that all required IDs and permissions are available.

        Returns:
            True if validation passes
        """
        valid = True

        # Check that we have collections and groups
        if not self.collection_ids:
            self.logger.logger.error(" No collection IDs loaded")
            valid = False

        if not self.group_ids:
            self.logger.logger.error(" No group IDs loaded")
            valid = False

        if not self.permission_matrix:
            self.logger.logger.error(" No permission matrix parsed")
            valid = False

        # Check for missing collection IDs
        missing_collections = []
        for collection_path in self.permission_matrix.keys():
            if collection_path not in self.collection_ids:
                missing_collections.append(collection_path)

        if missing_collections:
            self.logger.logger.error(f" Missing collection IDs for: {missing_collections}")
            valid = False

        # Check for missing group IDs
        all_groups = set()
        for group_perms in self.permission_matrix.values():
            all_groups.update(group_perms.keys())

        missing_groups = []
        for group_name in all_groups:
            if group_name not in self.group_ids:
                missing_groups.append(group_name)

        if missing_groups:
            self.logger.logger.error(f" Missing group IDs for: {missing_groups}")
            valid = False

        if valid:
            self.logger.logger.info(" Permission validation passed")

        return valid

    def assign_all_permissions(self) -> Dict[str, bool]:
        """
        Assign all permissions from CSV to all groups.

        Returns:
            Dict mapping group_name -> success_status
        """
        self.logger.logger.info("=" * 70)
        self.logger.logger.info(" STARTING PERMISSION ASSIGNMENT PROCESS")
        self.logger.logger.info("=" * 70)

        try:
            # Step 1: Parse CSV permissions
            self.parse_csv_permissions()

            # Step 2: Load Collection and Group IDs
            self.load_collection_ids()
            self.load_group_ids()

            # Step 3: Validate everything is ready
            if not self.validate_permissions():
                raise ValueError("Permission validation failed")

            # Step 4: Assign permissions to each group
            results = {}
            succeeded = 0
            failed = 0

            for group_name, group_id in self.group_ids.items():
                # Skip groups that aren't in our CSV (like existing groups)
                has_permissions = any(group_name in group_perms for group_perms in self.permission_matrix.values())

                if not has_permissions:
                    self.logger.logger.info(f"  Skipping group '{group_name}' (not in CSV)")
                    continue

                success = self.assign_permissions_to_group(group_name, group_id)
                results[group_name] = success

                if success:
                    succeeded += 1
                else:
                    failed += 1

            # Final summary
            total_attempted = len(results)
            self.logger.finalize_operation(
                "Permission Assignment",
                total_attempted,
                succeeded,
                str(self.csv_path)
            )

            self.logger.logger.info("=" * 70)
            self.logger.logger.info(" PERMISSION ASSIGNMENT PROCESS COMPLETE")
            self.logger.logger.info("=" * 70)

            return results

        except Exception as e:
            self.logger.logger.error(f" Permission assignment process failed: {e}")
            raise

    def export_permission_summary(self, output_file: str = None) -> str:
        """
        Export permission assignment summary to JSON file.

        Args:
            output_file: Optional custom output file path

        Returns:
            Path to exported file
        """
        if not output_file:
            timestamp = self.logger.log_data["operation_metadata"]["start_time"].replace(":", "").split(".")[0]
            output_file = f"../output/permissions_summary_{timestamp}.json"

        # Convert relative path to absolute from script location
        if not Path(output_file).is_absolute():
            output_path = Path(__file__).parent.parent / output_file.lstrip("../")
        else:
            output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True)

        # Create summary
        summary = {
            "csv_source": str(self.csv_path),
            "groups": self.group_ids,
            "collections": self.collection_ids,
            "permission_matrix": self.permission_matrix,
            "permission_mappings": []
        }

        # Add detailed mappings
        for group_name, group_id in self.group_ids.items():
            group_mapping = {
                "group_name": group_name,
                "group_id": group_id,
                "collections": []
            }

            for collection_path, group_perms in self.permission_matrix.items():
                permission_level = group_perms.get(group_name, "None")
                if permission_level != "None":
                    collection_mapping = {
                        "collection_path": collection_path,
                        "collection_id": self.collection_ids.get(collection_path),
                        "permission_level": permission_level,
                        "api_permissions": self.permission_mapping.get(permission_level)
                    }
                    group_mapping["collections"].append(collection_mapping)

            summary["permission_mappings"].append(group_mapping)

        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)

        self.logger.logger.info(f" Permission summary exported to: {output_path}")
        return str(output_path)


def main():
    """Main entry point for permission assignment from CSV."""
    try:
        # Initialize permissions manager
        csv_path = "../input/collections_permissions.csv"
        permissions_manager = BitwardenPermissionsManager(csv_path)

        # Assign all permissions
        results = permissions_manager.assign_all_permissions()

        print(f" Permission assignment completed!")
        print(f" Results:")

        for group_name, success in results.items():
            status = " Success" if success else " Failed"
            print(f"    '{group_name}': {status}")

        # Export summary
        summary_file = permissions_manager.export_permission_summary()
        print(f" Summary exported to: {summary_file}")

    except Exception as e:
        print(f" Permission assignment failed: {e}")


if __name__ == "__main__":
    main()
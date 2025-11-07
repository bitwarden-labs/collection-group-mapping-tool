#!/usr/bin/env python3
"""
Bulk Management Logger

Logging includes:
- Collection creation tracking
- Group creation tracking
- Permission mapping tracking
- Operation results and IDs
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class CollectionLog:
    """Log entry for collection creation."""
    timestamp: str
    collection_path: str
    collection_id: str
    organization_id: str
    status: str = "created"
    error_message: Optional[str] = None

@dataclass
class GroupLog:
    """Log entry for group creation."""
    timestamp: str
    group_name: str
    group_id: str
    organization_id: str
    status: str = "created"
    error_message: Optional[str] = None

@dataclass
class PermissionLog:
    """Log entry for permission mapping."""
    timestamp: str
    collection_path: str
    collection_id: str
    group_name: str
    group_id: str
    permission_level: str
    organization_id: str
    status: str = "mapped"
    error_message: Optional[str] = None

@dataclass
class OperationSummary:
    """Summary of bulk operation results."""
    operation_type: str
    start_time: str
    end_time: str
    total_attempted: int
    total_succeeded: int
    total_failed: int
    total_skipped: int
    organization_id: str
    csv_source_file: str


class BulkLogger:
    """Comprehensive logger for Bitwarden bulk management operations."""

    def __init__(self, log_dir: str = "../logs", operation_name: str = "bulk_operation"):
        # Convert relative path to absolute from script location
        if not Path(log_dir).is_absolute():
            self.log_dir = Path(__file__).parent.parent / log_dir.lstrip("../")
        else:
            self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{operation_name}_{timestamp}.json"

        # Initialise log data structure
        self.log_data = {
            "operation_metadata": {
                "operation_name": operation_name,
                "start_time": datetime.now().isoformat(),
                "log_file": str(self.log_file)
            },
            "collections": [],
            "groups": [],
            "permissions": [],
            "summary": {}
        }

        # Set up Python logging
        self._setup_python_logging(operation_name, timestamp)

    def _setup_python_logging(self, operation_name: str, timestamp: str):
        """Set up Python logging to file and console."""
        log_filename = self.log_dir / f"{operation_name}_{timestamp}.log"

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
        self.logger = logging.getLogger(f"BulkLogger_{operation_name}")
        self.logger.setLevel(logging.DEBUG)

        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info(f"Bulk operation logging initialised: {operation_name}")
        self.logger.info(f"JSON log file: {self.log_file}")
        self.logger.info(f"Text log file: {log_filename}")

    def log_collection_created(self, collection_path: str, collection_id: str,
                             organization_id: str) -> None:
        """Log successful collection creation."""
        log_entry = CollectionLog(
            timestamp=datetime.now().isoformat(),
            collection_path=collection_path,
            collection_id=collection_id,
            organization_id=organization_id
        )

        self.log_data["collections"].append(asdict(log_entry))
        self.logger.info(f" Collection created: '{collection_path}' → ID: {collection_id}")
        self._save_log()

    def log_collection_failed(self, collection_path: str, organization_id: str,
                            error_message: str) -> None:
        """Log failed collection creation."""
        log_entry = CollectionLog(
            timestamp=datetime.now().isoformat(),
            collection_path=collection_path,
            collection_id="",
            organization_id=organization_id,
            status="failed",
            error_message=error_message
        )

        self.log_data["collections"].append(asdict(log_entry))
        self.logger.error(f" Collection failed: '{collection_path}' - {error_message}")
        self._save_log()

    def log_group_created(self, group_name: str, group_id: str,
                         organization_id: str) -> None:
        """Log successful group creation."""
        log_entry = GroupLog(
            timestamp=datetime.now().isoformat(),
            group_name=group_name,
            group_id=group_id,
            organization_id=organization_id
        )

        self.log_data["groups"].append(asdict(log_entry))
        self.logger.info(f" Group created: '{group_name}' → ID: {group_id}")
        self._save_log()

    def log_group_failed(self, group_name: str, organization_id: str,
                        error_message: str) -> None:
        """Log failed group creation."""
        log_entry = GroupLog(
            timestamp=datetime.now().isoformat(),
            group_name=group_name,
            group_id="",
            organization_id=organization_id,
            status="failed",
            error_message=error_message
        )

        self.log_data["groups"].append(asdict(log_entry))
        self.logger.error(f" Group failed: '{group_name}' - {error_message}")
        self._save_log()

    def log_permission_mapped(self, collection_path: str, collection_id: str,
                             group_name: str, group_id: str, permission_level: str,
                             organization_id: str) -> None:
        """Log successful permission mapping."""
        log_entry = PermissionLog(
            timestamp=datetime.now().isoformat(),
            collection_path=collection_path,
            collection_id=collection_id,
            group_name=group_name,
            group_id=group_id,
            permission_level=permission_level,
            organization_id=organization_id
        )

        self.log_data["permissions"].append(asdict(log_entry))
        self.logger.info(f" Permission mapped: '{group_name}' → '{collection_path}' ({permission_level})")
        self._save_log()

    def log_permission_failed(self, collection_path: str, group_name: str,
                             permission_level: str, organization_id: str,
                             error_message: str) -> None:
        """Log failed permission mapping."""
        log_entry = PermissionLog(
            timestamp=datetime.now().isoformat(),
            collection_path=collection_path,
            collection_id="",
            group_name=group_name,
            group_id="",
            permission_level=permission_level,
            organization_id=organization_id,
            status="failed",
            error_message=error_message
        )

        self.log_data["permissions"].append(asdict(log_entry))
        self.logger.error(f" Permission failed: '{group_name}' → '{collection_path}' ({permission_level}) - {error_message}")
        self._save_log()

    def finalise_operation(self, operation_type: str, total_attempted: int,
                          total_succeeded: int, csv_source_file: str,
                          total_skipped: int = 0) -> None:
        """Finalise the operation and create summary."""
        summary = OperationSummary(
            operation_type=operation_type,
            start_time=self.log_data["operation_metadata"]["start_time"],
            end_time=datetime.now().isoformat(),
            total_attempted=total_attempted,
            total_succeeded=total_succeeded,
            total_failed=total_attempted - total_succeeded,
            total_skipped=total_skipped,
            organization_id=self._get_org_id_from_logs(),
            csv_source_file=csv_source_file
        )

        self.log_data["summary"] = asdict(summary)
        self._save_log()

        # Log summary
        self.logger.info("=" * 50)
        self.logger.info(f" OPERATION SUMMARY: {operation_type}")
        self.logger.info("=" * 50)
        self.logger.info(f" Succeeded: {total_succeeded}")
        self.logger.info(f" Failed: {total_attempted - total_succeeded}")
        self.logger.info(f" Skipped: {total_skipped}")
        self.logger.info(f" Total: {total_attempted}")
        self.logger.info(f" Source: {csv_source_file}")
        self.logger.info(f"️  Log file: {self.log_file}")

    def get_created_collections(self) -> Dict[str, str]:
        """Get mapping of collection paths to IDs for successful creations."""
        collections = {}
        for entry in self.log_data["collections"]:
            if entry["status"] == "created":
                collections[entry["collection_path"]] = entry["collection_id"]
        return collections

    def get_created_groups(self) -> Dict[str, str]:
        """Get mapping of group names to IDs for successful creations."""
        groups = {}
        for entry in self.log_data["groups"]:
            if entry["status"] == "created":
                groups[entry["group_name"]] = entry["group_id"]
        return groups

    def _get_org_id_from_logs(self) -> str:
        """Extract organization ID from log entries."""
        for entry in self.log_data["collections"]:
            if entry["organization_id"]:
                return entry["organization_id"]
        for entry in self.log_data["groups"]:
            if entry["organization_id"]:
                return entry["organization_id"]
        return ""

    def _save_log(self) -> None:
        """Save current log data to JSON file."""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.log_data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save log file: {e}")


def test_logging():
    """
    Test the logging functionality.
    This method is run when the bulk_logger.py file is run directly.
    """
    logger = BulkLogger(operation_name="test_logging")

    # Test collection logging
    logger.log_collection_created("Business Unit", "test-id-123", "org-123")
    logger.log_collection_created("Business Unit/A1", "test-id-456", "org-123")
    logger.log_collection_failed("Business Unit/Failed", "org-123", "Test error")

    # Test group logging
    logger.log_group_created("Users", "group-123", "org-123")
    logger.log_group_failed("Failed Group", "org-123", "Test error")

    # Test permission logging
    logger.log_permission_mapped("Business Unit", "test-id-123", "Users", "group-123", "Read", "org-123")
    logger.log_permission_failed("Business Unit", "Failed Group", "Edit", "org-123", "Test error")

    # Finalise
    logger.finalise_operation("Test Operation", 6, 4, "test.csv")

    print(" Test logging completed")


if __name__ == "__main__":
    test_logging()
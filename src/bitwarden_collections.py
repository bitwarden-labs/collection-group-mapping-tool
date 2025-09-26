import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from bw_auth import BitwardenAuth
from bulk_logger import BulkLogger


@dataclass
class CollectionInfo:
    """Information about a Bitwarden collection."""
    name: str
    path: str
    id: Optional[str] = None
    organization_id: Optional[str] = None


class BitwardenCollectionManager:
    """Manage Bitwarden collections via CLI commands."""

    def __init__(self, auth: BitwardenAuth | None = None, logger: BulkLogger | None = None):
        self.auth = auth if auth is not None else BitwardenAuth()
        self.organization_id = self.auth.organization_id
        self.created_collections: Dict[str, CollectionInfo] = {}
        self.logger = logger

    def generate_create_command(self, collection_path: str) -> str:
        """Generate the CLI command to create a collection."""
        return (
            f'bw get template org-collection | '
            f'jq \'.organizationId="{self.organization_id}" | .name="{collection_path}"\' | '
            f'bw encode | '
            f'bw create org-collection --organizationid {self.organization_id}'
        )

    def generate_list_command(self) -> str:
        """Generate the CLI command to list all collections."""
        return f'bw list org-collections --organizationid {self.organization_id}'

    def create_collection(self, collection_name: str, collection_path: str) -> CollectionInfo:
        """Create a collection and return its information."""
        try:
            # Get template, modify, encode, and create
            template_result = self.auth.run_command(["get", "template", "org-collection"])
            template_data = json.loads(template_result)

            # Modify template - use the full path as the collection name for nesting
            template_data["organizationId"] = self.organization_id
            template_data["name"] = collection_path  # Use full path instead of just leaf name

            # Convert back to JSON and encode
            template_json = json.dumps(template_data)
            encoded_result = self.auth.run_command(["encode"], input_data=template_json)

            # Create the collection
            create_result = self.auth.run_command([
                "create", "org-collection",
                "--organizationid", self.organization_id
            ], input_data=encoded_result)

            # Parse the JSON response
            collection_data = json.loads(create_result)
            collection_info = CollectionInfo(
                name=collection_name,
                path=collection_path,
                id=collection_data.get('id'),
                organization_id=collection_data.get('organizationId')
            )

            # Store the created collection
            self.created_collections[collection_path] = collection_info

            # Log successful creation
            if self.logger and collection_info.id:
                self.logger.log_collection_created(
                    collection_path=collection_path,
                    collection_id=collection_info.id,
                    organization_id=self.organization_id
                )

            return collection_info

        except Exception as e:
            # Log failed creation
            if self.logger:
                self.logger.log_collection_failed(
                    collection_path=collection_path,
                    organization_id=self.organization_id,
                    error_message=str(e)
                )
            raise Exception(f"Failed to create collection '{collection_name}': {e}")

    def create_collections_from_paths(self, collection_paths: List[str]) -> Dict[str, CollectionInfo]:
        """Create collections for all given paths, handling hierarchy."""
        # Sort paths to ensure parent collections are created first
        sorted_paths = sorted(collection_paths, key=lambda x: (x.count('/'), x))

        for path in sorted_paths:
            collection_name = path.split('/')[-1]  # Get the last segment as the name
            print(f"Creating collection: {collection_name} (path: {path})")

            try:
                collection_info = self.create_collection(collection_name, path)
                print(f"✓ Created collection '{collection_name}' with ID: {collection_info.id}")
            except Exception as e:
                print(f"✗ Error creating collection '{collection_name}': {e}")

        return self.created_collections


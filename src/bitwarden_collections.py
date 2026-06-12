import base64
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
        self._template_cache: Optional[Dict] = None

    def _get_template(self) -> Dict:
        """Fetch the org-collection template once per manager instance and cache it.
        The template is static for the run, so a single `bw get template` call is enough."""
        if self._template_cache is None:
            template_result = self.auth.run_command(["get", "template", "org-collection"])
            self._template_cache = json.loads(template_result)
        # Return a shallow copy so per-collection mutations don't pollute the cache.
        return dict(self._template_cache)

    def generate_create_command(self, collection_path: str) -> str:
        """Generate the equivalent shell pipeline for creating a collection.

        Mirrors `create_collection`: the live path caches `bw get template org-collection`
        once per run and uses native base64 instead of `bw encode`. This helper is for
        debug/display only — it shows the per-row equivalent without the caching."""
        return (
            f'bw get template org-collection | '
            f'jq \'.organizationId="{self.organization_id}" | .name="{collection_path}"\' | '
            f'base64 | '
            f'bw create org-collection --organizationid {self.organization_id}'
        )

    def generate_list_command(self) -> str:
        """Generate the CLI command to list all collections."""
        return f'bw list org-collections --organizationid {self.organization_id}'

    def list_existing_collections(self) -> Dict[str, str]:
        """List collections already in the org, returning a name → id map.

        Used for de-duplication: paths in the CSV that match an existing collection name
        are skipped during creation. When the same name appears more than once in the org
        (Bitwarden permits this), the first ID encountered wins and a warning is logged."""
        result = self.auth.run_command([
            "list", "org-collections",
            "--organizationid", self.organization_id
        ])
        collections = json.loads(result)

        name_to_id: Dict[str, str] = {}
        duplicate_counts: Dict[str, int] = {}

        for col in collections:
            name = col.get("name")
            cid = col.get("id")
            if not name or not cid:
                continue
            if name in name_to_id:
                duplicate_counts[name] = duplicate_counts.get(name, 1) + 1
            else:
                name_to_id[name] = cid

        if duplicate_counts and self.logger:
            for name, count in duplicate_counts.items():
                self.logger.logger.warning(
                    f"Collection name '{name}' appears {count}× in org — "
                    f"keeping first ID {name_to_id[name]}, ignoring the rest"
                )

        return name_to_id

    def create_collection(self, collection_name: str, collection_path: str) -> CollectionInfo:
        """Create a collection and return its information."""
        try:
            template_data = self._get_template()
            template_data["organizationId"] = self.organization_id
            template_data["name"] = collection_path  # Full path drives nesting

            # `bw encode` is just base64 of stdin; do it in-process to avoid a subprocess per row.
            template_json = json.dumps(template_data)
            encoded_result = base64.b64encode(template_json.encode("utf-8")).decode("ascii")

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


#!/usr/bin/env python3
"""
Execute Collection Creation

This script will create the collections in Bitwarden based on the CSV input file.
"""

from csv_parser import CollectionPermissionParser
from bitwarden_collections import BitwardenCollectionManager
from bw_auth import BitwardenAuth
from bulk_logger import BulkLogger
import json


def main():
    """Create collections in organisation."""
    csv_file = "../input/collections_permissions.csv"

    print(" Org Collection Creation")
    print("=" * 50)

    try:
        # Step 1: Initialise logging
        print("\n1. Initialising logging...")
        logger = BulkLogger(operation_name="collection_creation")
        print(f"   ✓ Logger initialised")

        # Step 2: Authenticate with Bitwarden
        print("\n2. Authenticating with Bitwarden...")
        auth = BitwardenAuth()
        session_key = auth.authenticate()
        print(f"   ✓ Authentication successful")
        print(f"   ✓ Organisation ID: {auth.organization_id}")

        # Step 3: Parse CSV for collections
        print("\n3. Parsing CSV file...")
        parser = CollectionPermissionParser(csv_file)
        data = parser.parse()
        unique_collections = parser.get_unique_collections()

        print(f"   ✓ Found {len(unique_collections)} unique collections to create")
        for collection in sorted(unique_collections):
            print(f"     - {collection}")

        # Step 4: Initialise collection manager with logger
        print("\n4. Initialising collection manager...")
        collection_manager = BitwardenCollectionManager(auth, logger)

        # Step 5: Look up existing collections so we can skip duplicates.
        print("\n5. Looking up existing collections for de-duplication...")
        existing_collections = collection_manager.list_existing_collections()
        print(f"   ✓ Found {len(existing_collections)} existing collections in org")

        # Step 6: Create collections (skipping any whose name already exists)
        print("\n6. Creating collections in Bitwarden...")
        print("-" * 40)

        # Sort to ensure parent collections are created first
        sorted_collections = sorted(unique_collections, key=lambda x: (x.count('/'), x))

        created_count = 0
        existing_count = 0
        failed_count = 0

        for collection_path in sorted_collections:
            collection_name = collection_path.split('/')[-1]

            if collection_path in existing_collections:
                existing_id = existing_collections[collection_path]
                print(f"Skipping (already exists): '{collection_path}' → ID: {existing_id}")
                logger.log_collection_existing(
                    collection_path=collection_path,
                    collection_id=existing_id,
                    organization_id=auth.organization_id
                )
                existing_count += 1
                continue

            try:
                print(f"Creating: '{collection_path}' (leaf name: {collection_name})")
                collection_info = collection_manager.create_collection(collection_name, collection_path)
                print(f"    Success! Full path stored as name. ID: {collection_info.id}")
                created_count += 1

            except Exception as e:
                print(f"    Failed: {e}")
                failed_count += 1

        # Step 7: Finalise logging
        print(f"\n7. Finalising operation logs...")
        attempted = created_count + failed_count
        logger.finalise_operation(
            operation_type="Collection Creation",
            total_attempted=attempted,
            total_succeeded=created_count,
            csv_source_file=csv_file,
            total_skipped=existing_count
        )

        if created_count > 0:
            print(f"\n Collections created at:")
            print(f"   {auth.server_url}#/organizations/{auth.organization_id}/collections")

        # Step 8: List collections in org for verification
        print(f"\n8. Listing current collections for verification...")
        try:
            collections_result = auth.run_command([
                "list", "org-collections",
                "--organizationid", auth.organization_id
            ])
            collections_data = json.loads(collections_result)

            print(f"   Current collections in organisation:")
            for collection in collections_data:
                print(f"     - {collection['name']} (ID: {collection['id']})")

        except Exception as e:
            print(f"     Could not list collections: {e}")

    except Exception as e:
        print(f"\n ERROR: {e}")
        return False

    return True


if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n Collection creation completed successfully!")
        # Note: auth object not available here, using default message
        print(f"   Check your Bitwarden vault to view collections.")
    else:
        print(f"\n Collection creation failed!")
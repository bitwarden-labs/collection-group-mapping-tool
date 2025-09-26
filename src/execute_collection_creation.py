#!/usr/bin/env python3
"""
Execute Collection Creation for INT-248

This script will actually create the collections in Bitwarden based on the CSV file.
"""

from csv_parser import CollectionPermissionParser
from bitwarden_collections import BitwardenCollectionManager
from bw_auth import BitwardenAuth
from bulk_logger import BulkLogger
import json


def main():
    """Create collections in organisation."""
    csv_file = "../input/collections_permissions.csv"

    print(" INT-248: Org Collection Creation")
    print("=" * 50)

    try:
        # Step 1: Initialize logging
        print("\n1. Initializing logging...")
        logger = BulkLogger(operation_name="collection_creation")
        print(f"   ✓ Logger initialized")

        # Step 2: Authenticate with Bitwarden
        print("\n2. Authenticating with Bitwarden...")
        auth = BitwardenAuth()
        session_key = auth.authenticate()
        print(f"   ✓ Authentication successful")
        print(f"   ✓ Organization ID: {auth.organization_id}")

        # Step 3: Parse CSV for collections
        print("\n3. Parsing CSV file...")
        parser = CollectionPermissionParser(csv_file)
        data = parser.parse()
        unique_collections = parser.get_unique_collections()

        print(f"   ✓ Found {len(unique_collections)} unique collections to create")
        for collection in sorted(unique_collections):
            print(f"     - {collection}")

        # Step 4: Initialize collection manager with logger
        print("\n4. Initialising collection manager...")
        collection_manager = BitwardenCollectionManager(auth, logger)

        # Step 5: Create collections
        print("\n5. Creating collections in Bitwarden...")
        print("-" * 40)

        # Sort to ensure parent collections are created first
        sorted_collections = sorted(unique_collections, key=lambda x: (x.count('/'), x))

        created_count = 0
        failed_count = 0

        for collection_path in sorted_collections:
            collection_name = collection_path.split('/')[-1]

            try:
                print(f"Creating: '{collection_path}' (leaf name: {collection_name})")
                collection_info = collection_manager.create_collection(collection_name, collection_path)
                print(f"    Success! Full path stored as name. ID: {collection_info.id}")
                created_count += 1

            except Exception as e:
                print(f"    Failed: {e}")
                failed_count += 1

        # Step 6: Finalize logging
        print(f"\n6. Finalising operation logs...")
        logger.finalize_operation(
            operation_type="Collection Creation",
            total_attempted=len(sorted_collections),
            total_succeeded=created_count,
            csv_source_file=csv_file
        )

        if created_count > 0:
            print(f"\n Collections created at:")
            print(f"   https://vault.bitwarden.com/#/organizations/{auth.organization_id}/collections")

        # Step 7: List created collections for verification
        print(f"\n7. Listing current collections for verification...")
        try:
            collections_result = auth.run_command([
                "list", "org-collections",
                "--organizationid", auth.organization_id
            ])
            collections_data = json.loads(collections_result)

            print(f"   Current collections in organization:")
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
        print(f"   Check vault.bitwarden.com to view collections.")
    else:
        print(f"\n Collection creation failed!")
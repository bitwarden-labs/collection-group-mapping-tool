#!/usr/bin/env python3
"""
INT-248: Collection Creation Tool

This module implements the functionality to:
1. Scan CSV files for collection definitions
2. Generate Bitwarden CLI commands to create collections
3. Execute collection creation with proper hierarchy handling
"""

from csv_parser import CollectionPermissionParser
from bitwarden_collections import BitwardenCollectionManager
from bw_auth import BitwardenAuth


def main():
    """Main function to demonstrate INT-248 functionality."""
    # Configuration
    csv_file = "../input/collections_permissions.csv"

    print("INT-248: Collection Creation Tool")
    print("=" * 40)

    # Step 1: Parse the CSV file
    print("\n1. Parsing CSV file...")
    parser = CollectionPermissionParser(csv_file)
    data = parser.parse()

    print(f"   Found {len(data['collections'])} collection paths")
    print(f"   Found {len(data['groups'])} groups: {', '.join(data['groups'])}")

    # Step 2: Extract unique collections
    print("\n2. Extracting unique collections...")
    unique_collections = parser.get_unique_collections()
    print(f"   Total unique collections to create: {len(unique_collections)}")

    for collection in sorted(unique_collections):
        print(f"   - {collection}")

    # Step 3: Initialise authentication and collection manager
    print("\n3. Initialising Bitwarden authentication...")
    try:
        auth = BitwardenAuth()
        collection_manager = BitwardenCollectionManager(auth)
        print(f"   ✓ Organization ID: {auth.organization_id}")
    except Exception as e:
        print(f"   ✗ Authentication setup failed: {e}")
        return

    # Step 4: Generate sample code
    print("\n4. Generating sample Python code...")
    sample_code = collection_manager.generate_sample_code(list(unique_collections))

    # Write sample code to file
    with open("../output/sample_collection_creation.py", "w") as f:
        f.write(sample_code)
    print("   ✓ Sample code written to output/sample_collection_creation.py")

    # Step 5: Display CLI commands
    print("\n5. CLI Commands for manual execution:")
    print("-" * 40)
    for collection_path in sorted(unique_collections):
        collection_name = collection_path.split('/')[-1]
        command = collection_manager.generate_create_command(collection_path)
        print(f"\n# Create collection: {collection_path}")
        print(f"echo 'Creating {collection_path}...'")
        print(command)

    # Step 6: Show collection hierarchy
    print("\n6. Collection Hierarchy:")
    print("-" * 25)
    hierarchy = parser.get_collection_hierarchy()
    for parent, children in hierarchy.items():
        if parent == 'root':
            print("Root Collections:")
            for child in children:
                print(f"  └── {child}")
        else:
            print(f"{parent}:")
            for child in children:
                child_name = child.split('/')[-1]
                print(f"  └── {child_name}")

    print(f"\n✓ INT-248 analysis complete. Ready to create {len(unique_collections)} collections.")


if __name__ == "__main__":
    main()
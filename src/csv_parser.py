import csv
from typing import List, Dict, Set
from pathlib import Path


class CollectionPermissionParser:
    """Parse CSV files containing collection permission matrices."""

    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self.collections = []
        self.groups = []
        self.permissions = {}

    def parse(self) -> Dict:
        """Parse the CSV file and extract collections, groups, and permissions."""
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            # Extract group names from headers (skip 'Path' column)
            self.groups = [col for col in reader.fieldnames if col != 'Path']

            # Parse each row
            for row in reader:
                collection_path = row['Path']
                self.collections.append(collection_path)

                # Store permissions for this collection
                self.permissions[collection_path] = {
                    group: row[group] for group in self.groups
                }

        return {
            'collections': self.collections,
            'groups': self.groups,
            'permissions': self.permissions
        }

    def get_unique_collections(self) -> Set[str]:
        """Extract unique collection names from paths."""
        collections = set()
        for path in self.collections:
            # Add each segment of the path as a collection
            parts = path.split('/')
            for i in range(len(parts)):
                collection_path = '/'.join(parts[:i+1])
                collections.add(collection_path)
        return collections

    def get_collection_hierarchy(self) -> Dict[str, List[str]]:
        """Build collection hierarchy mapping parent -> children."""
        hierarchy = {}
        unique_collections = self.get_unique_collections()

        for collection in unique_collections:
            parts = collection.split('/')
            if len(parts) > 1:
                parent = '/'.join(parts[:-1])
                if parent not in hierarchy:
                    hierarchy[parent] = []
                hierarchy[parent].append(collection)
            else:
                # Root level collection
                if 'root' not in hierarchy:
                    hierarchy['root'] = []
                hierarchy['root'].append(collection)

        return hierarchy
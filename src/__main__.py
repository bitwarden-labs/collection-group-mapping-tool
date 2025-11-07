#!/usr/bin/env python3
"""
Bitwarden Collection Permission Assignment Tool

Single command execution for the complete workflow:
- Create Collections from CSV input
- Create Groups from CSV input
- Assign Group-Collection Permissions based on CSV matrix

Usage:
    python -m src
"""

import sys
import time
import subprocess
from pathlib import Path


def run_step(step_name: str, command: list, description: str):
    """
    Run a single workflow step and measure time.

    Args:
        step_name: Name of the step for logging
        command: Command to execute
        description: Description of what the step does

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{step_name}")
    print("-" * 50)
    print(f"{description}")

    step_start = time.time()

    try:
        result = subprocess.run(command, check=True, capture_output=False, text=True)
        step_time = time.time() - step_start
        print(f"{step_name.split(':')[0]} completed successfully in {step_time:.1f}s")
        return True
    except subprocess.CalledProcessError as e:
        step_time = time.time() - step_start
        print(f"{step_name.split(':')[0]} failed after {step_time:.1f}s")
        print(f"Error: {e}")
        return False


def run_complete_workflow():
    """Execute the complete Bitwarden bulk management workflow."""

    print("BITWARDEN BULK MANAGEMENT SUITE")
    print("=" * 60)
    print("Collection & Group Management Tool")
    print("=" * 60)

    workflow_start = time.time()

    try:
        # Step 1: Create Collections
        success1 = run_step(
            "STEP 1: Creating Collections from CSV",
            ["python", "execute_collection_creation.py"],
            "Creating nested collections from CSV input using Bitwarden CLI"
        )

        if not success1:
            return False

        time.sleep(2)  # Brief pause between steps

        # Step 2: Create Groups
        success2 = run_step(
            "STEP 2: Creating Groups from CSV input",
            ["python", "bitwarden_groups.py"],
            "Creating groups from CSV headers using Bitwarden Public API"
        )

        if not success2:
            return False

        time.sleep(2)

        # Step 3: Assign Permissions
        success3 = run_step(
            "STEP 3: Assigning Group-Collection Permissions",
            ["python", "bitwarden_permissions.py"],
            "Assigning collection permissions to groups based on CSV matrix"
        )

        if not success3:
            return False

        # Final Summary
        workflow_time = time.time() - workflow_start
        print("\n" + "=" * 60)
        print("Workflow complete!")
        print("=" * 60)
        print(f"Total execution time: {workflow_time:.1f}s")

        print("\nAll steps completed successfully:")
        print("   [✓] Collections created from CSV rows")
        print("   [✓] Groups created from CSV columns")
        print("   [✓] Permissions assigned from CSV matrix")

        print("\nOutput files generated:")
        print("   - groups_mapping_*.json (group name -> ID mapping)")
        print("   - permissions_summary_*.json (detailed permission assignments)")

        print("\nView results:")
        print("   Check your Bitwarden vault collections page at the Admin Console")

        print("\nDetailed logs available in: logs/")

        return True

    except Exception as e:
        workflow_time = time.time() - workflow_start
        print(f"\nWORKFLOW FAILED after {workflow_time:.1f}s")
        print(f"Error: {e}")
        print("\nCheck logs for detailed error information")
        return False


def main():
    """Main entry point for the bulk management workflow."""
    try:
        # Determine if we're running from project root or src/ directory
        current_dir = Path.cwd()
        src_dir = None
        csv_file = None

        if (current_dir / "src" / "execute_collection_creation.py").exists():
            # Running from project root (python -m src)
            src_dir = current_dir / "src"
            csv_file = current_dir / "input" / "collections_permissions.csv"
        elif (current_dir / "execute_collection_creation.py").exists():
            # Running from src/ directory
            src_dir = current_dir
            csv_file = current_dir / ".." / "input" / "collections_permissions.csv"
        else:
            print("Error: Must be run from the src/ directory or use 'python -m src' from project root")
            print("Current directory:", current_dir)
            sys.exit(1)

        # Change to src directory for script execution
        original_dir = Path.cwd()
        import os
        os.chdir(src_dir)

        # Check if CSV file exists
        if not csv_file.exists():
            print(f"Error: CSV file not found: {csv_file}")
            print("Please ensure the CSV file exists in the input/ directory.")
            sys.exit(1)

        # Run the complete workflow
        success = run_complete_workflow()

        if success:
            print("\nAll operations completed successfully!")
            sys.exit(0)
        else:
            print("\nWorkflow failed. Check logs for details.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
    finally:
        # Restore original directory if it was changed
        try:
            if 'original_dir' in locals():
                import os
                os.chdir(original_dir)
        except:
            pass


if __name__ == "__main__":
    main()
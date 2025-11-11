# Bitwarden Bulk Management Tool

A Python-based automation tool for bulk management of Bitwarden collections, groups, and permissions. This tool implements allows for creation of creations & groups, as well as establishing the relationship between them in Bitwarden organisations, using input from a .csv template.

## Tool Overview

This tool automates three core operations:

- Creation of nested collections from CSV rows
- Creation of groups from CSV column headers
- Assignment of collection permissions to groups based on CSV matrix values

N.b. Existing Objects

Collections are always created.  There is no de-duplication tool available for Collections.
Groups will be created where an idenitically-named group does not already exist.  If a group already exists matching the name on the input file, then this existing group will be used.


The tool processes a CSV file whereby:

- The first column (`Path`) defines nested collection structures (e.g., `Business Unit/A1/alpha`)
- The column headers define group names (e.g., `Users`, `Seniors`, `Admins`)
- The cell values define permissions (`None`, `Read`, `Edit`, `Manage`)

## Installation

### 1. Python preparation

A python environment is required to run the tool.  Additional support for preparing this on your machine (for macOS/Linux/Windows) can be found in the accompanying README-Python-installation.md document.

When running python, a virtual environment is generally recommended, and one method of producing this is described in the aforementioned doc.

## Configuration

### 1. Create Environment File

Copy and configure your environment variables:

```bash
cp .env.example .env
# Renames the example .env file, ready to populate with your actual secrets
```

### 2. Configure .env File

Edit `.env` with your Bitwarden credentials:

```env
# Bitwarden CLI Authentication
BW_USERNAME=your_account_username_here
BW_MASTERPASSWORD=your_master_password_here
# https://bitwarden.com/help/cli/#using-an-api-key
BW_USERCLIENTID=your_client_api_id_here
BW_USERCLIENTSECRET=your_account_api_secret_here

# Bitwarden API Authentication (for groups/permissions)
# See https://bitwarden.com/help/public-api/
BW_ORGCLIENTID=your_api_client_id_here
BW_ORGCLIENTSECRET=your_organisation_api_secret_here

# Organization ID
BW_ORGID=organisation_id
```

### 3. Prepare Input CSV

Place your CSV file at `input/collections_permissions.csv`.  An example structure is shown below:

```csv
Path,Users,Seniors,Admins
Business Unit,Read,Read,Manage
Business Unit/A1,Edit,Edit,Manage
Business Unit/A1/alpha,Edit,Edit,Manage
```

**CSV Format:**

- **First column (`Path`)**: Collection names.  Nested collections are demarcated with the `/` character (<https://bitwarden.com/help/about-collections/#nested-collections>)
- **Other columns**: Group names (headers become group names) <https://bitwarden.com/help/about-groups/>
- **Cell values**: Permission levels
  - `None` - No access
  - `ReadPWsHidden` - View-only access, but secret fields are only available via auto-fill
  - `Read` - View-only access
  - `EditPWsHidden` - Edit access, but secret fields are only available via auto-fill
  - `Edit` - View and edit access
  - `Manage` - Full management access
<https://bitwarden.com/help/collection-permissions/#permissions-table>

### 4. Launch the tool

When you are ready to run the tool, you can do so by installing a valid Python environment, along with necessary dependencies, and running:

```bash
python -m src
```

from the working directory.


### Workflow Steps

When you run the tool, it executes three steps sequentially:

#### **STEP 1: Creating Collections**

- Parses CSV `Path` column
- Creates nested collection hierarchy using Bitwarden CLI
- Example: `Business Unit/A1/alpha` creates 3 nested collections

#### **STEP 2: Creating Groups**

- Parses CSV column headers (excluding `Path`)
- Creates groups via Bitwarden Public API
- Generates `output/groups_mapping_*.json` with name→ID mappings

#### **STEP 3: Assigning Permissions**

- Reads CSV permission matrix
- Assigns collection access to groups with specified permissions
- Generates `output/permissions_summary_*.json` with assignment details

## Output Files

Generated in the `output/` directory:

- **`groups_mapping_YYYYMMDD_HHMMSS.json`**
  Maps group names to UUIDs created in Bitwarden

- **`permissions_summary_YYYYMMDD_HHMMSS.json`**
  Detailed log of all permission assignments

## Logs

Detailed execution logs are written to `logs/` directory:

- Timestamped log files for each run
- Error details and debugging information
- API request/response logs

## Troubleshooting

### CSV parsing errors

Verify:

- CSV is UTF-8 encoded
- First column is named `Path`
- No extra commas or malformed rows
- Permission values are: `None`, `Read`, `Edit`, or `Manage`

### Running Individual Steps

```bash
# Run only collections creation
pipenv run python src/execute_collection_creation.py

# Run only groups creation
pipenv run python src/bitwarden_groups.py

# Run only permissions assignment
pipenv run python src/bitwarden_permissions.py
```

## Security Notes

- **Never commit `.env`** to version control (already in `.gitignore`)
- API credentials have full organization access - protect this carefully

## Version Information

- Python: 3.12.11
- Dependencies: See `Pipfile.lock` for exact versions
- Bitwarden CLI: Latest stable version recommended

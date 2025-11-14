# Python Installation

Operating Python environments can be complicated, and there are almost as many options as there are users.  The README below quickly details a couple of methods that you may wish to use to run the tool.

## Prerequisites

No matter what method you chose to run the Python modules, the following pre-requisites should be available

- **Python 3.12**
- **Packages listed in requirements.txt**
- **Bitwarden CLI** (`bw`) installed and configured
- **Bitwarden account** with organisation admin access
- **API credentials** (Client ID and Client Secret)
- **.env file correctly configured**

This project was built with ([Pipenv](https://pipenv.pypa.io/en/latest/)), which can also be used to simply run the tool.  Alternatively, plain Python can also be used.

## Quick start overview

For those with existing Python experience, the project can be installed by:

- Creating a venv
- Installing the required packages from requirements.txt
- Running `python -m src` from the project directory

## Using pipenv

Pipenv is a tool designed to assist with the creation and maintanence of Python venvs.  Some notes are included below to help users get started.  For full guidance, please [refer to the official documentation](https://pipenv.pypa.io/en/latest/).

## Understanding Pipfile & Pipfile.lock

These two files replicate the functionality of requirements.txt

**Pipfile:**
- Human-readable dependency specification to specifiy dependencies
- Also specifies Python version requirement (3.12.11)

**Pipfile.lock:**
- Machine-generated lock file with exact versions
- Contains cryptographic hashes for security verification
- Includes all transitive dependencies (dependencies of dependencies)

If you prefer, you can manage dependencies from the lock file using standard pip:

```bash
pip install -r <(pipenv lock -r)
```

## Running with Pipenv

### 1. Check python installation

Ensure you have Python 3.12 installed on your system:

```bash
python --version  # Should show 3.12.x
```

### 2. Check bw CLI binary availability

```bash
bw --version
```

### 3. Clone and Setup Project

Navigate to the project directory:

```bash
cd /path/to/working directory
# Replace /path/to/ with your actual project location

git clone https://github.com/bitwarden-labs/collection-group-mapping-tool.git
```

Install project dependencies:

```bash
pipenv install
```

This command:

- Creates a virtual environment specifically for this project
- Installs all dependencies from `Pipfile.lock` (python-dotenv, requests, and their dependencies)
- Verifies package integrity using cryptographic hashes

**Verify installation:**

```bash
# Check virtual environment was created
pipenv --venv

# Verify dependencies are installed
pipenv run pip list
# Should show: certifi, charset-normalizer, idna, pip, python-dotenv, requests, urllib3
```

## Usage

### Understanding pipenv Commands

pipenv creates an isolated virtual environment for your project. This ensures:

- Dependencies don't conflict with other Python projects
- Exact versions are locked for reproducibility
- Different Python versions can be used per project

**Common pipenv commands:**

```bash
# Activate the virtual environment (optional - not required for run)
pipenv shell

# Run a command in the virtual environment
pipenv run python src/bulk_logger.py # Run testing function of bulk_logger module

# Run a module
pipenv run python -m src # Run the full tool

# Install new packages
pipenv install package_name

# Install dev dependencies
pipenv install --dev package_name

# Update all dependencies
pipenv update

# Check for security vulnerabilities
pipenv check

# Remove the virtual environment
pipenv --rm

# See where the virtual environment is located
pipenv --venv
```


### Running the Tool

**Primary command (from project root):**

```bash
pipenv run python -m src
```

**What this does:**

1. Activates the project's virtual environment
2. Executes `python -m src` which runs `src/__main__.py`
3. Runs the complete 3-step workflow automatically

**Alternative methods:**

```bash
# If you prefer to activate the shell first
pipenv shell
python -m src
exit  # When done, to exit the python venv

```

## Troubleshooting

### Python version mismatch

If you see "Requires python_version 3.12":

- Check your version: `python --version`
- Install Python 3.12 or consider using [pyenv](https://github.com/pyenv/pyenv) to manage multiple versions

### pipenv not found after installation

Add Python scripts directory to PATH:

**macOS/Linux:**

```bash
export PATH="$HOME/.local/bin:$PATH"
# Add to ~/.bashrc or ~/.zshrc to make permanent
```

**Windows:**

Add `%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts` to PATH environment variable

### Permission denied errors

- **macOS/Linux**: Use `pip install --user pipenv` (not sudo)
- **Windows**: Run terminal as Administrator

### Virtual environment issues

If dependencies aren't being found:

```bash
# Remove and recreate virtual environment
pipenv --rm
pipenv install
```

### "No module named X" errors

Ensure you're using pipenv to run commands:

- **Use**: `pipenv run python -m src`
- **NOT**: `python -m src` (won't use the virtual environment)

### Pipenv hangs during installation

If `pipenv install` appears stuck:

```bash
# Try with verbose output
pipenv install --verbose

# Or clear pipenv cache
pipenv --clear
pipenv install
```

## Next Steps

Once Python and dependencies are installed, return to the main [README.md](README.md) for:

- Configuration (.env file setup)
- CSV preparation
- Running the tool
- Understanding the workflow steps

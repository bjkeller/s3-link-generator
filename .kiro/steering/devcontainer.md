# Dev Container Workflow

This project uses dev containers for consistent development environments.

## Kiro Pants Power (Recommended)

**PREFERRED METHOD**: Use the `kiro-pants-power` for automated devcontainer and Pants command execution. The power automatically manages container lifecycle and wraps all Pants commands.

Available power tools:
- `pants_fix` — Format code and auto-fix linting issues
- `pants_lint` — Run linters on code
- `pants_check` — Run type checking with mypy
- `pants_test` — Run tests (supports test_filter for specific test names)
- `pants_package` — Build packages
- `full_quality_check` — Run complete workflow (fix → lint → check → test)
- `container_start`, `container_stop`, `container_rebuild` — Container lifecycle management

The power handles all container management automatically, ensuring the container is running before executing commands.

### Intent-Based Parameters

All Pants tools support intent-based parameters:

- `scope`: `'all'` (default), `'directory'`, or `'file'`
- `path`: Directory or file path (required for `'directory'` and `'file'` scopes)
- `recursive`: Include subdirectories (default: true, directory scope only)
- `test_filter`: Filter tests by name pattern (pants_test only)

### Usage Examples

```
# Run on all code
pants_fix with scope="all"
pants_test with scope="all"

# Run on specific directory
pants_lint with scope="directory", path="lambda/s3_signed_url/src/python"
pants_test with scope="directory", path="lambda/s3_signed_url/test/python"

# Run on single file
pants_check with scope="file", path="lambda/s3_signed_url/src/python/s3_signed_url_lambda/lambda_function.py"

# Run specific tests by name
pants_test with scope="directory", path="lambda/s3_signed_url/test/python", test_filter="test_presign"
```

## Manual Scripts (Fallback)

If the power is unavailable, use the devcontainer scripts in the `bin/` directory.

**CRITICAL**: Before executing any commands in the container, ALWAYS run `./bin/start-devcontainer.sh` first. This command is idempotent.

### Commands to Run in Container

```bash
# Setup
./bin/exec-in-devcontainer.sh bash get-pants.sh

# Code quality
./bin/exec-in-devcontainer.sh pants fix ::
./bin/exec-in-devcontainer.sh pants lint ::
./bin/exec-in-devcontainer.sh pants check ::

# Testing
./bin/exec-in-devcontainer.sh pants test ::
./bin/exec-in-devcontainer.sh pants test lambda/s3_signed_url/test/python::

# Building
./bin/exec-in-devcontainer.sh pants package ::
```

### Interactive Shell

```bash
./bin/terminal.sh
# Then run commands directly: pants fix :: && pants lint :: && pants check :: && pants test ::
```

## Container Management

```bash
./bin/start-devcontainer.sh    # Start (idempotent)
./bin/stop-devcontainer.sh     # Stop
./bin/build-container.sh       # Rebuild after .devcontainer/ changes
```

## Python Environment

The dev container provides Python 3.12 pre-installed via the Dockerfile. No manual Python installation needed.

## Kiro AI Assistant Workflow

### Using Kiro Pants Power (Recommended)

1. Use power tools directly (e.g., `pants_fix`, `pants_lint`, `pants_test`)
2. The power automatically manages container lifecycle
3. Use `full_quality_check` for complete validation workflow

### Using Manual Scripts (Fallback)

1. **ALWAYS** run `./bin/start-devcontainer.sh` first
2. Execute commands with `./bin/exec-in-devcontainer.sh`

---
inclusion: auto
description: Guidance for using the kiro-pants-power to automate Pants build system and devcontainer operations
---

# Kiro Pants Power Usage

## Overview

The `kiro-pants-power` automates Pants build system and devcontainer operations for this repository. Use power tools instead of manual scripts whenever possible.

## Quick Reference

### Most Common Operations

**Complete Quality Check** (recommended before commits):
```
Use: full_quality_check tool
```

**Individual Steps**:
```
Use: pants_fix tool with scope="all"      # Format all code (always run first)
Use: pants_lint tool with scope="all"     # Check linting
Use: pants_check tool with scope="all"    # Type checking
Use: pants_test tool with scope="all"     # Run all tests
```

**Build Lambda Packages**:
```
Use: pants_package tool with scope="all"
Use: pants_package tool with scope="directory", path="lambda/s3_signed_url/src/python/s3_signed_url_lambda"
```

## Intent-Based Parameters

All Pants tools support these parameters:

- `scope` (optional): `'all'` (default), `'directory'`, or `'file'`
- `path` (required for 'directory' and 'file'): Directory or file path
- `recursive` (optional, default: true): Include subdirectories (directory scope only)
- `test_filter` (optional, pants_test only): Filter tests by name pattern

## Workflow Best Practices

### Before Committing Code

Always run the complete quality check:
```
Use: full_quality_check tool
```

This runs: fix → lint → check → test in sequence and stops on first failure.

### During Development

Focus on specific areas you're changing:
```
Use: pants_test tool with scope="directory", path="lambda/s3_signed_url/test/python"
Use: pants_fix tool with scope="directory", path="lambda/s3_signed_url/src/python"
```

### Run Specific Tests

```
Use: pants_test tool with scope="all", test_filter="test_presign"
Use: pants_test tool with scope="directory", path="lambda/s3_signed_url/test/python", test_filter="test_presign"
```

### When Seeing Weird Errors

```
Use: pants_clear_cache tool
```

### After Dependency Changes

```
Use: container_rebuild tool
```

## Container Management

The power automatically starts the container when needed. Manual control:

```
Use: container_start tool     # Idempotent
Use: container_stop tool      # Stop container
Use: container_rebuild tool   # Rebuild from scratch
```

## Manual Scripts Fallback

If the power is unavailable, use scripts in `bin/`:
- `./bin/start-devcontainer.sh` — Start container
- `./bin/exec-in-devcontainer.sh <command>` — Execute command
- `./bin/terminal.sh` — Open interactive shell

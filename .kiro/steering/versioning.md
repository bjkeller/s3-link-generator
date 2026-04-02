# Versioning and Changelog Guidelines

## Version Number Management

**CRITICAL RULE: Never automatically bump version numbers or create changelog entries.**

### When Making Code Changes

1. **DO NOT** add new version entries to any changelog or release files
2. **DO NOT** increment version numbers in any files
3. **DO** document what changes were made in your summary
4. **DO** wait for explicit user instruction before creating version entries

### Only Update Versions When Explicitly Asked

Version numbers should only be updated when the user explicitly requests it with phrases like:
- "Create a new version"
- "Bump the version to X.Y.Z"
- "Prepare a release"

### Why This Rule Exists

Version management involves coordinated steps (changelogs, tags, builds, releases) that require human oversight. Automatically bumping versions can cause conflicts and confusion.

## What To Do Instead

When you make changes that would normally warrant a version bump:

1. Document the changes clearly in your summary
2. List the modified files
3. Suggest that a version bump may be needed, but don't do it automatically

## Exception: Documentation-Only Changes

For documentation-only changes (README updates, comment improvements, etc.) that don't affect functionality:
- No version bump is needed
- No changelog entry is needed
- Just document what was updated in your summary

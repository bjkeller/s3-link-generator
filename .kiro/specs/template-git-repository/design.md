# Template Git Repository Design Document

## Overview

This design transforms the existing AWS Lambda monorepo template directory into a proper template git repository with automated setup capabilities. The solution provides developers with a streamlined way to bootstrap new AWS Lambda monorepos using modern development practices including Pants build system, dev containers, and Terraform infrastructure management.

The template repository will feature an interactive setup script that customizes template files with project-specific information, automated git initialization, and comprehensive documentation to guide developers through the entire process from setup to deployment.

## Architecture

### Templating Tool Decision: Cookiecutter vs Custom Solution

**Decision: Use Cookiecutter as the templating engine**

After evaluating options, Cookiecutter provides significant advantages:

**Cookiecutter Benefits:**
- **Mature ecosystem**: Battle-tested with extensive community support
- **Jinja2 templating**: Powerful conditional logic and variable substitution
- **JSON/YAML configuration**: Structured configuration with validation
- **Hooks support**: Pre/post generation hooks for custom logic
- **Cross-platform**: Works consistently across operating systems
- **Extensive documentation**: Well-documented with many examples

**Architecture with Cookiecutter:**

```
aws-lambda-monorepo-template/
├── cookiecutter.json           # Template configuration and prompts
├── hooks/                      # Pre/post generation hooks
│   ├── pre_gen_project.py     # Input validation and setup
│   └── post_gen_project.py    # Git init, cleanup, final setup
├── {{cookiecutter.project_name}}/  # Template directory
│   ├── README.md              # Project README template
│   ├── .devcontainer/         # Dev container configuration
│   ├── bin/                   # Development scripts
│   ├── docs/                  # Documentation templates
│   ├── examples/              # Example implementations
│   └── lambda/                # Lambda function templates
├── README.md                  # Template usage documentation
└── docs/                      # Template documentation
```

### Key Architectural Decisions

1. **Cookiecutter Integration**: Leverage Cookiecutter's proven templating system instead of building custom solution
2. **Jinja2 Templates**: Use `{{cookiecutter.variable_name}}` syntax and conditional blocks `{% if cookiecutter.enable_database %}`
3. **Hooks for Logic**: Implement complex setup logic in pre/post generation hooks
4. **JSON Configuration**: Define all template variables and prompts in cookiecutter.json
5. **Modular Features**: Use Jinja2 conditionals for optional feature inclusion

## Components and Interfaces

### Cookiecutter Configuration (`cookiecutter.json`)

Defines all template variables, prompts, and validation rules:

```json
{
    "project_name": "my-lambda-project",
    "project_title": "{{ cookiecutter.project_name.replace('-', ' ').title() }}",
    "project_description": "AWS Lambda monorepo using Pants and Terraform",
    "author_name": "Your Name",
    "author_email": "your.email@example.com",
    "aws_region": ["us-east-1", "us-west-2", "eu-west-1"],
    "python_version": ["3.11", "3.10", "3.12"],
    "enable_database": ["no", "yes"],
    "database_type": ["mysql", "postgresql", "oracle"],
    "enable_vpc": ["no", "yes"],
    "aws_services": {
        "s3": "no",
        "dynamodb": "no", 
        "sqs": "no",
        "sns": "no"
    }
}
```

### Pre-Generation Hook (`hooks/pre_gen_project.py`)

Validates inputs and performs setup preparation:

```python
import re
import sys

def validate_project_name(name: str) -> bool:
    """Validate project name follows conventions."""
    pattern = r'^[a-z][a-z0-9-]*[a-z0-9]$'
    return bool(re.match(pattern, name))

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# Validation logic
project_name = '{{ cookiecutter.project_name }}'
author_email = '{{ cookiecutter.author_email }}'

if not validate_project_name(project_name):
    print("ERROR: Invalid project name. Use lowercase letters, numbers, and hyphens.")
    sys.exit(1)

if not validate_email(author_email):
    print("ERROR: Invalid email format.")
    sys.exit(1)
```

### Post-Generation Hook (`hooks/post_gen_project.py`)

Handles git initialization and final setup:

```python
import os
import subprocess
from pathlib import Path

def initialize_git_repository():
    """Initialize git repository with initial commit."""
    subprocess.run(['git', 'init'], check=True)
    subprocess.run(['git', 'add', '.'], check=True)
    subprocess.run(['git', 'commit', '-m', 'Initial commit from template'], check=True)

def cleanup_conditional_files():
    """Remove files not needed based on configuration."""
    if '{{ cookiecutter.enable_database }}' == 'no':
        # Remove database-related files
        db_files = Path('.').glob('**/database*')
        for file in db_files:
            file.unlink(missing_ok=True)

def make_scripts_executable():
    """Make shell scripts executable."""
    script_files = Path('bin').glob('*.sh')
    for script in script_files:
        script.chmod(0o755)

# Execute post-generation tasks
cleanup_conditional_files()
make_scripts_executable()
initialize_git_repository()
```

### Template Structure

Jinja2 templates with conditional content:

```jinja2
# In requirements.txt template
aws-lambda-powertools[aws-sdk]>=2.37.0
boto3>=1.34.0
{% if cookiecutter.enable_database == 'yes' %}
{% if cookiecutter.database_type == 'mysql' %}
pymysql>=1.1.1
sqlalchemy>=2.0.23
{% elif cookiecutter.database_type == 'postgresql' %}
psycopg2-binary>=2.9.0
{% endif %}
{% endif %}
{% if cookiecutter.aws_services.s3 == 'yes' %}
boto3-stubs[s3]
{% endif %}
```

## Data Models

### Cookiecutter Variables

Variables defined in `cookiecutter.json` and available in all templates:

**Core Project Variables:**
- `cookiecutter.project_name` - Project name (kebab-case)
- `cookiecutter.project_title` - Project title (derived from name)
- `cookiecutter.project_description` - Project description
- `cookiecutter.author_name` - Author full name
- `cookiecutter.author_email` - Author email address
- `cookiecutter.aws_region` - Default AWS region
- `cookiecutter.python_version` - Python version (e.g., "3.11")

**Feature Configuration:**
- `cookiecutter.enable_database` - Boolean for database support
- `cookiecutter.database_type` - Database type when enabled
- `cookiecutter.enable_vpc` - Boolean for VPC configuration
- `cookiecutter.aws_services` - Object with AWS service flags

### Jinja2 Template Syntax

**Variable Substitution:**
```jinja2
# Simple variable
{{ cookiecutter.project_name }}

# Derived variable with filters
{{ cookiecutter.project_name.replace('-', ' ').title() }}
```

**Conditional Content:**
```jinja2
{% if cookiecutter.enable_database == 'yes' %}
# Database configuration
DATABASE_URL = "{{ cookiecutter.database_type }}://..."
{% endif %}
```

**Loops and Lists:**
```jinja2
{% for service, enabled in cookiecutter.aws_services.items() %}
{% if enabled == 'yes' %}
# {{ service }} configuration
{% endif %}
{% endfor %}
```

### File Naming with Variables

Cookiecutter supports variable file and directory names:

```
{{cookiecutter.project_name}}/
├── lambda/
│   └── {{cookiecutter.project_name}}_example/
└── docs/
    └── {{cookiecutter.project_name}}-guide.md
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After reviewing all properties identified in the prework, I've identified several areas where properties can be consolidated:

**Redundancy Analysis:**
- Properties 1.1, 1.4, and 1.5 all test file/directory creation and can be combined into a comprehensive "template completeness" property
- Properties 2.2 and 2.4 both test variable replacement and can be combined into a single "variable replacement" property  
- Properties 4.1, 4.2, and 4.4 all test conditional feature inclusion and can be combined into a "conditional features" property
- Properties 1.2, 3.4 can be combined into a "documentation generation" property

**Consolidated Properties:**
1. **Template completeness** - combines file structure, examples, and Terraform template verification
2. **Variable replacement** - comprehensive testing of variable substitution across all file types
3. **Git initialization** - repository setup and initial commit
4. **Input validation** - error handling for invalid inputs
5. **Conditional features** - optional feature inclusion/exclusion
6. **Documentation generation** - comprehensive documentation creation
7. **Development environment** - functional development setup
8. **Variable naming consistency** - consistent variable naming patterns

Property 1: Template completeness
*For any* valid cookiecutter configuration, running `cookiecutter` on the template should create all required files and directories including configuration files, example implementations, Terraform templates, and documentation
**Validates: Requirements 1.1, 1.4, 1.5**

Property 2: Variable replacement consistency  
*For any* valid cookiecutter configuration and template file containing variables, all Jinja2 template variables should be replaced with the corresponding values from the configuration
**Validates: Requirements 2.2, 2.4**

Property 3: Git repository initialization
*For any* successful cookiecutter generation, the post-generation hook should initialize a git repository with proper .gitignore and an initial commit containing all generated files
**Validates: Requirements 2.3**

Property 4: Input validation and error handling
*For any* invalid input provided during cookiecutter prompts, the pre-generation hook should display appropriate error messages and prevent template generation
**Validates: Requirements 2.5**

Property 5: Conditional feature inclusion
*For any* cookiecutter configuration with optional features enabled or disabled, only the files and dependencies corresponding to enabled features should be included in the generated project
**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

Property 6: Documentation generation completeness
*For any* cookiecutter configuration, the generated project should include comprehensive documentation covering usage instructions, template variables, and selected features
**Validates: Requirements 1.2, 3.4**

Property 7: Functional development environment
*For any* generated project, the development environment should be functional with working dev container, build system, and example implementations
**Validates: Requirements 1.3**

Property 8: Variable naming consistency
*For any* template file in the repository, all template variables should follow consistent Jinja2 naming conventions using the {{cookiecutter.variable_name}} pattern
**Validates: Requirements 5.4**

## Error Handling

The template system implements comprehensive error handling at multiple levels:

### Input Validation Errors
- **Invalid project names**: Names containing invalid characters or reserved words
- **Missing required fields**: Empty or null values for required configuration
- **Invalid AWS regions**: Non-existent or unsupported AWS regions
- **Conflicting options**: Incompatible feature combinations

### File Processing Errors
- **Template file not found**: Missing template files during processing
- **Permission errors**: Insufficient permissions to create files or directories
- **Disk space errors**: Insufficient disk space for project creation
- **Invalid template syntax**: Malformed template variable syntax

### Git Repository Errors
- **Existing repository**: Target directory already contains a git repository
- **Git not available**: Git command not found in system PATH
- **Initial commit failure**: Errors during git repository initialization

### Recovery Strategies
- **Partial cleanup**: Remove partially created files on setup failure
- **Detailed logging**: Comprehensive error logging for troubleshooting
- **User guidance**: Clear error messages with suggested solutions
- **Graceful degradation**: Continue setup where possible despite non-critical errors

## Testing Strategy

The template repository uses a dual testing approach combining unit tests for specific functionality and property-based tests for universal correctness properties.

### Unit Testing Approach

Unit tests verify specific examples and integration points:

- **Setup script functionality**: Test individual setup script methods with known inputs
- **Template processing**: Verify specific template files are processed correctly
- **Git operations**: Test repository initialization with specific scenarios
- **Error conditions**: Test specific error cases and error message content
- **File generation**: Verify specific generated files match expected content

Unit tests provide concrete examples of correct behavior and catch specific bugs in implementation details.

### Property-Based Testing Approach

Property-based tests verify universal properties across all valid inputs using **Hypothesis** for Python. Each property-based test runs a minimum of 100 iterations to ensure comprehensive coverage.

**Property-based testing requirements:**
- Use Hypothesis library for generating test inputs
- Configure minimum 100 iterations per property test
- Tag each test with format: **Feature: template-git-repository, Property {number}: {property_text}**
- Generate realistic cookiecutter configurations for testing
- Test edge cases through property generators

**Test generators will create:**
- Valid project names (various lengths, character sets)
- Different feature combinations (database types, AWS services)
- Various user input scenarios (names, emails, descriptions)
- Edge cases (minimum/maximum values, special characters)

Property-based tests verify that the cookiecutter template works correctly across the entire input space, catching edge cases that unit tests might miss.

### Integration Testing

- **End-to-end setup**: Complete setup process from start to finish
- **Generated project validation**: Verify generated projects can be built and deployed
- **Development workflow**: Test that generated projects support the full development lifecycle
- **Cross-platform compatibility**: Ensure template works on different operating systems

Both unit and property-based tests are essential for comprehensive coverage: unit tests catch concrete implementation bugs while property-based tests verify general correctness across all possible inputs.
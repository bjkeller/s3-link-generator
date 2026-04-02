# AWS Lambda Monorepo Template

This directory contains template files and documentation for creating new AWS Lambda monorepos using Pants build system and Terraform for infrastructure.

## Quick Start

1. **Copy template files** to your new repository
2. **Customize configuration** files for your project
3. **Follow setup guide** in `docs/setup-guide.md`
4. **Use development workflow** in `docs/development-workflow.md`

## Template Structure

```
lambda-monorepo-template/
├── README.md                    # This file
├── docs/                        # Documentation
│   ├── setup-guide.md          # Step-by-step setup instructions
│   ├── development-workflow.md  # Daily development workflow
│   ├── project-structure.md    # Repository organization patterns
│   ├── lambda-patterns.md      # Lambda implementation patterns
│   └── deployment-guide.md     # Terraform deployment guide
├── templates/                   # Template files to copy
│   ├── config/                 # Configuration files
│   ├── devcontainer/           # Dev container setup
│   ├── lambda-example/         # Sample lambda structure
│   └── scripts/                # Helper scripts
└── examples/                    # Example implementations
    ├── simple-lambda/          # Basic lambda without database
    ├── database-lambda/        # Lambda with database connection
    └── batch-processing/       # Batch processing lambda
```

## Key Features

- **Pants Build System** - Modern Python monorepo management
- **Dev Containers** - Consistent development environment
- **Terraform Integration** - Infrastructure as Code
- **AWS Lambda Powertools** - Production-ready logging and tracing
- **Type Safety** - MyPy and Pydantic for robust code
- **Code Quality** - Automated formatting and linting

## Documentation Overview

### Essential Reading
1. **Setup Guide** - Complete project initialization
2. **Development Workflow** - Daily development patterns
3. **Project Structure** - Repository organization

### Reference Documentation
4. **Lambda Patterns** - Implementation templates
5. **Deployment Guide** - Terraform and AWS deployment

## Getting Started

1. Read the setup guide: `docs/setup-guide.md`
2. Copy template files to your new repository
3. Follow the customization checklist
4. Start building your first lambda

## Support

This template is based on production patterns from the NACC Identifiers project and includes best practices for:
- Security and compliance
- Performance optimization
- Maintainable code structure
- Scalable infrastructure
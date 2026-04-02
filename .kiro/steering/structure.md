# Project Structure

## Monorepo Organization

This is a Pants-managed monorepo for AWS Lambda functions. It was created from the `naccdata/lambda-monorepo-template`.

## Repository Layout

```
s3-presigned-url-service/
├── .devcontainer/              # Dev container configuration
│   ├── devcontainer.json
│   └── Dockerfile
├── .kiro/                      # Kiro settings and steering
│   ├── settings/mcp.json      # Kiro Pants Power config
│   └── steering/              # Steering documents
├── bin/                        # Dev scripts (build, start, stop, terminal, exec)
├── lambda/                     # Individual Lambda functions
│   └── s3_signed_url/
│       ├── src/python/s3_signed_url_lambda/
│       │   ├── BUILD
│       │   └── lambda_function.py
│       ├── test/python/
│       │   ├── BUILD
│       │   └── test_lambda_function.py
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── docs/                       # Documentation
├── examples/                   # Example lambda implementations (for reference)
│   ├── simple-lambda/
│   ├── database-lambda/
│   └── common/
├── prompts/                    # Spec prompts for agent-driven development
│   ├── 01-lambda.md           # Lambda implementation spec prompt
│   ├── 02-api.md              # API Gateway / SAM spec prompt
│   └── 03-web-app.md          # Quick Access Link web app spec prompt
├── BUILD                       # Root Pants BUILD file
├── pants.toml                  # Pants configuration
├── requirements.txt            # Python dependencies
├── ruff.toml                   # Ruff linter config
└── get-pants.sh               # Pants installer
```

## Lambda Structure

Each lambda follows this pattern:

```
lambda/<lambda_name>/
├── src/python/<lambda_name>_lambda/
│   ├── BUILD                  # Pants targets: python_sources, python_aws_lambda_function, python_aws_lambda_layer
│   └── lambda_function.py     # Handler implementation
├── test/python/
│   ├── BUILD                  # python_sources + python_tests targets
│   └── test_lambda_function.py
├── main.tf                    # Terraform configuration
├── variables.tf               # Terraform variables
└── outputs.tf                 # Terraform outputs
```

### Lambda BUILD File Pattern

```python
python_sources(name="function")

python_aws_lambda_function(
    name="lambda",
    runtime="python3.12",
    handler="lambda_function.py:lambda_handler",
    include_requirements=False,
)

python_aws_lambda_layer(
    name="layer",
    runtime="python3.12",
    dependencies=[
        ":function",
        "//:root#boto3",
        "//:root#pydantic",
        "//:root#aws-lambda-powertools",
    ],
    include_sources=False,
)
```

## Root BUILD File

```python
python_requirements(name="root")
```

External dependencies from `requirements.txt` are referenced as `//:root#<package>`.

## Source Roots

Pants recognizes these as source roots (from `pants.toml`):
- `src/*` — Source code
- `test/*` — Test code

## Ignored Directories

Pants ignores:
- `.devcontainer/`
- `.vscode/`

## Spec Prompts

The `prompts/` directory contains structured prompts for spec-based agent development:
- `01-lambda.md` — S3 presign Lambda behavior, client registry, and testing requirements
- `02-api.md` — API Gateway, SAM template, authentication, and infrastructure
- `03-web-app.md` — Quick Access Link web app (consumer of the presign API)

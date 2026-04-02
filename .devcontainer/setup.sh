#!/bin/bash
set -e

echo "Setting up development environment..."

# Install Pants launcher using get-pants.sh
./get-pants.sh

# Verify installations
python --version
node --version
terraform --version
pants --version

echo "Development environment ready!"

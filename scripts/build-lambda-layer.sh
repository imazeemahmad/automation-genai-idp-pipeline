#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Build the Lambda Layer zip containing Python dependencies.
# Structure required by AWS: python/lib/python3.12/site-packages/...
#
# Usage: ./scripts/build-lambda-layer.sh
# Output: build/layer.zip
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_ROOT}/build/layer"
OUTPUT="${PROJECT_ROOT}/build/layer.zip"
REQUIREMENTS="${PROJECT_ROOT}/app_src/app/lambdas/requirements.txt"
PYTHON_VERSION="3.12"

echo "Building Lambda Layer from ${REQUIREMENTS}"

# Clean previous build
rm -rf "$BUILD_DIR" "$OUTPUT"
mkdir -p "$BUILD_DIR/python/lib/python${PYTHON_VERSION}/site-packages"

# Install dependencies for arm64 Lambda runtime
pip install \
  -r "$REQUIREMENTS" \
  -t "$BUILD_DIR/python/lib/python${PYTHON_VERSION}/site-packages/" \
  --platform manylinux2014_aarch64 \
  --implementation cp \
  --python-version "$PYTHON_VERSION" \
  --abi cp312 \
  --only-binary=:all: \
  --upgrade \
  --quiet

# Create zip
cd "$BUILD_DIR"
zip -r "$OUTPUT" python/ -x "*/__pycache__/*" "*.pyc"

LAYER_SIZE=$(du -h "$OUTPUT" | cut -f1)
echo "Layer zip created: $OUTPUT ($LAYER_SIZE)"

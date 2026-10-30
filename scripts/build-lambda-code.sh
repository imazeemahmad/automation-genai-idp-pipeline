#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Build the Lambda code zip (application code only, no dependencies).
#
# Usage: ./scripts/build-lambda-code.sh
# Output: build/code.zip
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_ROOT}/build/code"
OUTPUT="${PROJECT_ROOT}/build/code.zip"
SOURCE_DIR="${PROJECT_ROOT}/app_src/app/lambdas"

echo "Building Lambda code zip from ${SOURCE_DIR}"

# Clean previous build
rm -rf "$BUILD_DIR" "$OUTPUT"
mkdir -p "$BUILD_DIR"

# Copy application code (handlers, models, services, repositories, parsers)
for dir in handlers models services repositories parsers; do
  if [ -d "$SOURCE_DIR/$dir" ]; then
    cp -r "$SOURCE_DIR/$dir" "$BUILD_DIR/"
  fi
done

# Generate version file with build metadata
COMMIT_SHA="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo "unknown")}"
COMMIT_SHORT="${COMMIT_SHA:0:8}"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
BRANCH="${GITHUB_REF_NAME:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")}"
TAG="$(git describe --tags --exact-match 2>/dev/null || echo "")"

# Detect uncommitted changes (always false in CI since GITHUB_SHA is set)
if [[ -n "${GITHUB_SHA:-}" ]]; then
  DIRTY="false"
else
  DIRTY=$(git diff --quiet 2>/dev/null && echo "false" || echo "true")
fi

cat > "$BUILD_DIR/version.json" <<EOF
{
  "commit": "${COMMIT_SHA}",
  "commit_short": "${COMMIT_SHORT}",
  "branch": "${BRANCH}",
  "tag": "${TAG}",
  "build_date": "${BUILD_DATE}",
  "dirty": ${DIRTY}
}
EOF

echo "Version: ${COMMIT_SHORT} (${BRANCH}) built at ${BUILD_DATE} dirty=${DIRTY} tag=${TAG:-none}"

# Create zip
cd "$BUILD_DIR"
zip -r "$OUTPUT" . -x "*/__pycache__/*" "*.pyc"

CODE_SIZE=$(du -h "$OUTPUT" | cut -f1)
echo "Code zip created: $OUTPUT ($CODE_SIZE)"

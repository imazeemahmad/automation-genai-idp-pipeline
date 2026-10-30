#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Push Lambda build artifacts (layer.zip and code.zip) to S3.
#
# Must be run AFTER build-lambda-layer.sh and/or build-lambda-code.sh,
# and BEFORE terraform plan/apply (the module's data source needs the
# objects to exist in S3 at plan time).
#
# Usage:
#   ./scripts/push-lambda-artifacts.sh <developer|sbx|dev|uat|prod>
#
# Examples:
#   ./scripts/push-lambda-artifacts.sh developer-4
#   ./scripts/push-lambda-artifacts.sh sbx
#   ./scripts/push-lambda-artifacts.sh dev
#   ./scripts/push-lambda-artifacts.sh uat
#   ./scripts/push-lambda-artifacts.sh prod
#
# Environment variables (optional overrides):
#   APP_NAME_SHORT  - default: idp
#   REGION_SHORT    - default: emea
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_ROOT}/build"

# ─── Configuration ───────────────────────────────────────────────────────────

APP_NAME_SHORT="${APP_NAME_SHORT:-idp}"
REGION_SHORT="${REGION_SHORT:-emea}"

# ─── Argument validation ─────────────────────────────────────────────────────

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <developer|sbx|dev|uat|prod>"
  echo ""
  echo "Examples:"
  echo "  $0 developer-4    # push to sandbox bucket for developer 'developer-4'"
  echo "  $0 sbx       # push to base shared sandbox bucket"
  echo "  $0 dev       # push to dev environment bucket"
  echo "  $0 uat       # push to uat environment bucket"
  echo "  $0 prod      # push to prod environment bucket"
  exit 1
fi

TARGET="$1"

# ─── Determine bucket name and S3 key prefix ────────────────────────────────

# resource_prefix: app-<app_name_short>-<region_short>
RESOURCE_PREFIX="app-${APP_NAME_SHORT}-${REGION_SHORT}"

if [[ "${TARGET}" == "dev" || "${TARGET}" == "uat" || "${TARGET}" == "prod" ]]; then
  # Shared environment (no developer suffix)
  ENV="${TARGET}"
  SUFFIX=""
elif [[ "${TARGET}" == "sbx" ]]; then
  ENV="sbx"
  SUFFIX=""
else
  # Per-developer sandbox
  ENV="sbx"
  DEVELOPER="${TARGET}"
  SUFFIX="-${DEVELOPER}"
fi

# Bucket: app-<app_name_short>-<region_short>-common-build-<env>[-<developer>]
BUCKET_NAME="${RESOURCE_PREFIX}-common-build-${ENV}${SUFFIX}"

# Key prefix: app-<app_name_short>-<region_short>[-<developer>]
KEY_PREFIX="${RESOURCE_PREFIX}${SUFFIX}"

# ─── Validate build artifacts exist ─────────────────────────────────────────

LAYER_ZIP="${BUILD_DIR}/layer.zip"
CODE_ZIP="${BUILD_DIR}/code.zip"

ARTIFACTS_TO_PUSH=()

if [[ -f "${LAYER_ZIP}" ]]; then
  ARTIFACTS_TO_PUSH+=("layer")
else
  echo "WARNING: layer.zip not found — skipping (run build-lambda-layer.sh first)"
fi

if [[ -f "${CODE_ZIP}" ]]; then
  ARTIFACTS_TO_PUSH+=("code")
else
  echo "WARNING: code.zip not found — skipping (run build-lambda-code.sh first)"
fi

if [[ ${#ARTIFACTS_TO_PUSH[@]} -eq 0 ]]; then
  echo "ERROR: No artifacts to push. Run build scripts first."
  exit 1
fi

# ─── Push to S3 ─────────────────────────────────────────────────────────────

echo "──────────────────────────────────────────────"
echo " Bucket : ${BUCKET_NAME}"
echo " Prefix : ${KEY_PREFIX}/"
echo " Artifacts: ${ARTIFACTS_TO_PUSH[*]}"
echo "──────────────────────────────────────────────"

for artifact in "${ARTIFACTS_TO_PUSH[@]}"; do
  LOCAL_FILE="${BUILD_DIR}/${artifact}.zip"
  S3_KEY="${KEY_PREFIX}/${artifact}.zip"
  echo "Uploading ${artifact}.zip -> s3://${BUCKET_NAME}/${S3_KEY}"
  aws s3 cp "${LOCAL_FILE}" "s3://${BUCKET_NAME}/${S3_KEY}"
done

# ─── Push version.json ───────────────────────────────────────────────────────

VERSION_FILE="${BUILD_DIR}/code/version.json"
if [[ -f "${VERSION_FILE}" ]]; then
  S3_KEY="${KEY_PREFIX}/version.json"
  echo "Uploading version.json -> s3://${BUCKET_NAME}/${S3_KEY}"
  aws s3 cp "${VERSION_FILE}" "s3://${BUCKET_NAME}/${S3_KEY}"
else
  echo "WARNING: version.json not found — skipping"
fi

echo "Push complete."

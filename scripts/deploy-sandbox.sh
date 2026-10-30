#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Terraform wrapper script for sandbox and dev environments
#
# Usage:
#   ./scripts/deploy-sandbox.sh <developer|sbx|dev> <action> [extra terraform args...]
#
# Actions: init, plan, apply, destroy, force-unlock
#
# Examples:
#   ./scripts/deploy-sandbox.sh developer-4 init
#   ./scripts/deploy-sandbox.sh developer-4 plan
#   ./scripts/deploy-sandbox.sh developer-4 apply -auto-approve
#   ./scripts/deploy-sandbox.sh developer-4 force-unlock <lock-id>
#   ./scripts/deploy-sandbox.sh sbx plan          # base shared sbx environment
#   ./scripts/deploy-sandbox.sh dev plan          # dev environment
#   ./scripts/deploy-sandbox.sh dev apply
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TF_DIR="${ROOT_DIR}/app_terraform"

# ─── Argument validation ─────────────────────────────────────────────────────

FORCE_LAMBDA=false
CLEAN_INIT=false
BUILD_CODE=false
BUILD_LAYER=false
PUSH=false

# Parse optional flags
POSITIONAL_ARGS=()
for arg in "$@"; do
  case "${arg}" in
    --force-lambda)
      FORCE_LAMBDA=true
      ;;
    --clean)
      CLEAN_INIT=true
      ;;
    --build-code)
      BUILD_CODE=true
      ;;
    --build-layer)
      BUILD_LAYER=true
      ;;
    --build-all)
      BUILD_CODE=true
      BUILD_LAYER=true
      ;;
    --push)
      PUSH=true
      ;;
    *)
      POSITIONAL_ARGS+=("${arg}")
      ;;
  esac
done
set -- "${POSITIONAL_ARGS[@]}"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <developer|sbx|dev> <action> [--build-code] [--build-layer] [--build-all] [--push] [--force-lambda] [--clean] [extra args...]"
  echo ""
  echo "  developer : developer-4, developer-5, developer-2, developer-1, developer-3"
  echo "  sbx       : deploy the base shared sandbox (no developer override)"
  echo "  dev       : deploy the dev environment"
  echo "  action    : init, plan, apply, destroy, force-unlock, state"
  echo ""
  echo "Options:"
  echo "  --build-code   : Build Lambda code zip before running Terraform"
  echo "  --build-layer  : Build Lambda layer zip before running Terraform"
  echo "  --build-all    : Build layer and code before running Terraform"
  echo "  --push         : Push build artifacts to S3 before running Terraform"
  echo "  --force-lambda : Force Lambda code update (replaces S3 objects)"
  echo "  --clean        : Remove .terraform/ and .terraform.lock.hcl before init"
  echo ""
  echo "Examples:"
  echo "  $0 developer-4 init"
  echo "  $0 developer-4 init --clean"
  echo "  $0 developer-4 plan --build-code --push"
  echo "  $0 developer-4 apply --build-all --push -auto-approve"
  echo "  $0 developer-4 apply --force-lambda -auto-approve"
  echo "  $0 developer-4 force-unlock <lock-id>"
  echo "  $0 developer-4 state list"
  echo "  $0 developer-4 state show module.kms.aws_kms_key.kms"
  echo "  $0 sbx plan"
  echo "  $0 dev plan"
  echo "  $0 dev apply --build-code --push"
  exit 1
fi

TARGET="$1"
ACTION="$2"
shift 2

# ─── Determine var-files and backend config ──────────────────────────────────

if [[ "${TARGET}" == "dev" ]]; then
  # Dev environment — no developer suffix
  ENV_DIR="${ROOT_DIR}/env/dev"
  BACKEND_FILES=(
    -backend-config="${ENV_DIR}/backend_config.tfvars"
  )
  VAR_FILES=(
    -var-file="${ENV_DIR}/variables.tfvars"
  )
  LABEL="dev"
elif [[ "${TARGET}" == "sbx" ]]; then
  # Base shared sandbox — no developer override
  ENV_DIR="${ROOT_DIR}/env/sbx"
  BACKEND_FILES=(
    -backend-config="${ENV_DIR}/backend_config.tfvars"
  )
  VAR_FILES=(
    -var-file="${ENV_DIR}/variables.tfvars"
  )
  LABEL="sbx (base)"
else
  # Per-developer sandbox
  ENV_DIR="${ROOT_DIR}/env/sbx"
  DEVELOPER="${TARGET}"

  if [[ ! -f "${ENV_DIR}/developers/${DEVELOPER}.tfvars" ]]; then
    echo "Error: Developer '${DEVELOPER}' not found."
    echo "Expected file: env/sbx/developers/${DEVELOPER}.tfvars"
    echo ""
    echo "Available developers:"
    find "${ENV_DIR}/developers/" -maxdepth 1 -name '*.tfvars' -not -name '*.backend*' -print0 | xargs -0 -I{} basename {} .tfvars | sort -u
    exit 1
  fi

  if [[ ! -f "${ENV_DIR}/developers/${DEVELOPER}.backend.tfvars" ]]; then
    echo "Error: Backend config for '${DEVELOPER}' not found."
    echo "Expected file: env/sbx/developers/${DEVELOPER}.backend.tfvars"
    exit 1
  fi

  BACKEND_FILES=(
    -backend-config="${ENV_DIR}/backend_config.tfvars"
    -backend-config="${ENV_DIR}/developers/${DEVELOPER}.backend.tfvars"
  )
  VAR_FILES=(
    -var-file="${ENV_DIR}/variables.tfvars"
    -var-file="${ENV_DIR}/developers/${DEVELOPER}.tfvars"
  )
  LABEL="${DEVELOPER}"
fi

# ─── Execute action ──────────────────────────────────────────────────────────

echo "──────────────────────────────────────────────"
echo " Target    : ${LABEL}"
echo " Action    : ${ACTION}"
echo " Directory : app_terraform/"
echo "──────────────────────────────────────────────"

# ─── JFrog Terraform credentials (before init) ──────────────────────────────

if [[ "${ACTION}" == "init" ]]; then
  if [[ -n "${TF_TOKEN_grand_org_jfrog_io:-}" ]]; then
    echo "──── JFrog: using TF_TOKEN_grand_org_jfrog_io env variable ────"
  else
    CREDENTIALS_FILE="${HOME}/.terraform.d/credentials.tfrc.json"
    if [[ ! -f "${CREDENTIALS_FILE}" ]] || ! grep -q "grand_org.jfrog.io" "${CREDENTIALS_FILE}" 2>/dev/null; then
      echo "──── JFrog: credentials not found ────"
      echo "Set TF_TOKEN_grand_org_jfrog_io env variable or run 'terraform login grand_org.jfrog.io'."
      exit 1
    fi
  fi
fi

# ─── Run Terraform ───────────────────────────────────────────────────────────

# ─── Build Lambda artifacts (if flags are set) ──────────────────────────────

if [[ "${BUILD_LAYER}" == "true" ]]; then
  echo "──── Building Lambda layer ────"
  "${SCRIPT_DIR}/build-lambda-layer.sh"
fi

if [[ "${BUILD_CODE}" == "true" ]]; then
  echo "──── Building Lambda code ────"
  "${SCRIPT_DIR}/build-lambda-code.sh"
fi

# ─── Push artifacts to S3 (if --push flag is set) ────────────────────────────

if [[ "${PUSH}" == "true" ]]; then
  echo "──── Pushing artifacts to S3 ────"
  "${SCRIPT_DIR}/push-lambda-artifacts.sh" "${TARGET}"
fi

# ─── Execute Terraform command ───────────────────────────────────────────────

case "${ACTION}" in
  init)
    if [[ "${CLEAN_INIT}" == "true" ]]; then
      echo "──── Cleaning .terraform directory and lock file ────"
      rm -rf "${TF_DIR}/.terraform"
      rm -f "${TF_DIR}/.terraform.lock.hcl"
    fi

    terraform -chdir="${TF_DIR}" init \
      "${BACKEND_FILES[@]}" \
      "$@"
    ;;
  plan)
    terraform -chdir="${TF_DIR}" plan \
      "${VAR_FILES[@]}" \
      "$@"
    ;;
  apply)
    if [[ "${FORCE_LAMBDA}" == "true" ]]; then
      echo "──── Force Lambda: replacing layer version to trigger update ────"
      terraform -chdir="${TF_DIR}" apply \
        "${VAR_FILES[@]}" \
        -replace='aws_lambda_layer_version.dependencies' \
        "$@"
    else
      terraform -chdir="${TF_DIR}" apply \
        "${VAR_FILES[@]}" \
        "$@"
    fi
    ;;
  destroy)
    terraform -chdir="${TF_DIR}" destroy \
      "${VAR_FILES[@]}" \
      "$@"
    ;;
  force-unlock)
    if [[ $# -lt 1 ]]; then
      echo "Error: force-unlock requires a lock ID"
      echo "Usage: $0 ${TARGET} force-unlock <lock-id>"
      exit 1
    fi
    terraform -chdir="${TF_DIR}" force-unlock "$@"
    ;;
  state)
    terraform -chdir="${TF_DIR}" state "$@"
    ;;
  *)
    echo "Error: Unknown action '${ACTION}'"
    echo "Valid actions: init, plan, apply, destroy, force-unlock, state"
    exit 1
    ;;
esac

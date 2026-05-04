#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE="phalouvas/ph-agent-framework"
TAG="latest"
PUSH=false

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  -t, --tag TAG     Image tag (default: latest)
  -p, --push        Push to Docker Hub after building
  -h, --help        Show this help
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--tag) TAG="$2"; shift 2 ;;
    -p|--push) PUSH=true; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

echo "Building ${IMAGE}:${TAG} from ${PROJECT_DIR} ..."
docker build -t "${IMAGE}:${TAG}" -f "${SCRIPT_DIR}/Dockerfile" "${PROJECT_DIR}"

if $PUSH; then
  echo "Pushing ${IMAGE}:${TAG} ..."
  docker push "${IMAGE}:${TAG}"
  echo "Done — ${IMAGE}:${TAG} pushed."
else
  echo "Done — ${IMAGE}:${TAG} built. Use --push to push to Docker Hub."
fi

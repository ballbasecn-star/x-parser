#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d)-$(git -C "$ROOT_DIR" rev-parse --short HEAD)}"
IMAGE_NAME="${X_PARSER_IMAGE:-ballbase/x-parser}"
BUNDLE_DIR="${ROOT_DIR}/.tmp/release/${IMAGE_TAG}"

mkdir -p "${BUNDLE_DIR}/images" "${BUNDLE_DIR}/deploy"

echo "==> 导出 x-parser 镜像"
docker save -o "${BUNDLE_DIR}/images/x-parser.tar" "${IMAGE_NAME}:${IMAGE_TAG}"

cp "${ROOT_DIR}/deploy/compose.prod.yaml" "${BUNDLE_DIR}/deploy/compose.prod.yaml"
cp "${ROOT_DIR}/deploy/.env.prod.example" "${BUNDLE_DIR}/deploy/.env.prod.example"

cat > "${BUNDLE_DIR}/deploy/release.env" <<EOF
X_PARSER_IMAGE=${IMAGE_NAME}
X_PARSER_VERSION=${IMAGE_TAG}
EOF

echo "==> 导出完成: ${BUNDLE_DIR}"

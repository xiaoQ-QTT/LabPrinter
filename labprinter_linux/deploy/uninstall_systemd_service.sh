#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-labprinter}"

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "未找到 systemctl：当前系统可能未使用 systemd。"
  exit 1
fi

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
ENV_DIR="/etc/${SERVICE_NAME}"

echo "==> 停止并移除 systemd 服务: ${SERVICE_NAME}"

${SUDO} systemctl disable --now "${SERVICE_NAME}.service" || true
${SUDO} rm -f "${SERVICE_FILE}"
${SUDO} systemctl daemon-reload

echo "==> 已移除服务文件: ${SERVICE_FILE}"
echo "==> 环境文件目录未删除（如需删除请手动处理）: ${ENV_DIR}"

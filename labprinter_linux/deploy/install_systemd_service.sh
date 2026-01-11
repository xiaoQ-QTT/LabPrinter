#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT_DIR="$(pwd -P)"

SERVICE_NAME="${SERVICE_NAME:-labprinter}"

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

if [[ "${ROOT_DIR}" =~ [[:space:]] ]]; then
  echo "工作目录包含空格，systemd 的 ExecStart/WorkingDirectory 可能解析失败：${ROOT_DIR}"
  echo "建议把项目放到不含空格的路径后再安装服务。"
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "未找到 systemctl：当前系统可能未使用 systemd，无法配置开机自启动。"
  exit 1
fi

PYTHON="${ROOT_DIR}/venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  echo "未找到虚拟环境: ${PYTHON}"
  echo "请先安装依赖: ./deploy/install_ubuntu22.sh"
  exit 1
fi

_project_owner_user() {
  stat -c '%U' "${ROOT_DIR}" 2>/dev/null || true
}

RUN_USER="${SERVICE_USER:-}"
if [[ -z "${RUN_USER}" ]]; then
  if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    RUN_USER="${SUDO_USER}"
  elif [[ "${EUID}" -eq 0 ]]; then
    RUN_USER="$(_project_owner_user)"
    RUN_USER="${RUN_USER:-root}"
  else
    RUN_USER="$(id -un)"
  fi
fi

if ! id -u "${RUN_USER}" >/dev/null 2>&1; then
  echo "运行用户不存在: ${RUN_USER}"
  echo "可通过 SERVICE_USER=用户名 ./deploy/install_systemd_service.sh 指定"
  exit 1
fi

if [[ "${RUN_USER}" == "root" ]]; then
  echo "警告：将以 root 运行服务（不推荐）。建议创建普通用户并用 SERVICE_USER 指定。"
fi

RUN_GROUP="${SERVICE_GROUP:-}"
if [[ -z "${RUN_GROUP}" ]]; then
  RUN_GROUP="$(id -gn "${RUN_USER}")"
fi

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
ENV_DIR="/etc/${SERVICE_NAME}"
ENV_FILE="${ENV_DIR}/${SERVICE_NAME}.env"

echo "==> 安装 systemd 服务: ${SERVICE_NAME}"
echo "    工作目录: ${ROOT_DIR}"
echo "    运行用户: ${RUN_USER}:${RUN_GROUP}"
echo "    服务文件: ${SERVICE_FILE}"
echo "    环境文件: ${ENV_FILE}"

${SUDO} mkdir -p "${ENV_DIR}"
${SUDO} chown root:root "${ENV_DIR}"
${SUDO} chmod 0750 "${ENV_DIR}"
if [[ ! -f "${ENV_FILE}" ]]; then
  ${SUDO} tee "${ENV_FILE}" >/dev/null <<EOF
# Environment for ${SERVICE_NAME}
HOST=0.0.0.0
PORT=5000
DEBUG=false

# 可选：默认打印机/白名单
# DEFAULT_PRINTER=
# ALLOWED_PRINTERS=

# 可选：PDF 预处理（提升兼容性，但可能更慢）
# PDF_PREPROCESS=none
# PDF_RASTER_DPI=200

# 并发任务数
# MAX_CONCURRENT_JOBS=3

# Flask SECRET_KEY（生产环境建议修改）
# SECRET_KEY=change-me
EOF
fi
${SUDO} chown root:root "${ENV_FILE}"
${SUDO} chmod 0640 "${ENV_FILE}"

${SUDO} tee "${SERVICE_FILE}" >/dev/null <<EOF
[Unit]
Description=LabPrinter (Linux)
After=network-online.target cups.service
Wants=network-online.target cups.service

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${ROOT_DIR}
Environment=PYTHONUNBUFFERED=1
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin
EnvironmentFile=-${ENV_FILE}
ExecStart=${PYTHON} ${ROOT_DIR}/run.py
Restart=on-failure
RestartSec=2

# 轻量加固（不影响 LibreOffice/CUPS）
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo "==> systemd reload + enable + start"
${SUDO} systemctl daemon-reload
${SUDO} systemctl enable --now "${SERVICE_NAME}.service"

echo "==> 状态"
${SUDO} systemctl status "${SERVICE_NAME}.service" --no-pager

echo ""
echo "OK."
echo "查看日志: ${SUDO} journalctl -u ${SERVICE_NAME}.service -f"
echo "停止服务: ${SUDO} systemctl disable --now ${SERVICE_NAME}.service"

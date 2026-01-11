#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  python3 python3-venv \
  cups cups-client cups-filters \
  libreoffice-writer \
  ghostscript poppler-utils \
  fontconfig

# 字体安装与 fontconfig 别名映射
./deploy/install_fonts.sh

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "OK. Run: ./deploy/start.sh"

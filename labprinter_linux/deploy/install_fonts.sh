#!/usr/bin/env bash
# 安装/修复字体：用于 LibreOffice headless 转 PDF + CUPS 打印

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> 安装常用字体包（Office/CJK）..."
sudo apt-get update

_apt_pkg_available() {
  apt-cache show "$1" 2>/dev/null | grep -q '^Package:'
}

base_pkgs=(
  fontconfig
  fonts-noto-cjk
  fonts-noto-cjk-extra
  fonts-wqy-zenhei
  fonts-wqy-microhei
  fonts-arphic-ukai
  fonts-arphic-uming
  fonts-droid-fallback
  fonts-liberation
  fonts-crosextra-carlito
  fonts-crosextra-caladea
)

# 扩大覆盖面（不同发行版/源可能缺少部分包，存在就装，不存在就跳过）
optional_pkgs=(
  fonts-noto-core
  fonts-noto-extra
  fonts-noto-ui-core
  fonts-noto-mono
  fonts-noto-color-emoji
  fonts-dejavu
  fonts-dejavu-core
  fonts-dejavu-extra
  fonts-freefont-ttf
  fonts-liberation2
  fonts-ubuntu
  fonts-ubuntu-console
  fonts-roboto
  fonts-roboto-unhinted
  fonts-cantarell
  fonts-opensymbol
  fonts-unifont
  fonts-hanazono
  fonts-nanum
  fonts-baekmuk
  fonts-unfonts-core
  fonts-unfonts-extra
  fonts-ipafont-gothic
  fonts-ipafont-mincho
  fonts-ipaexfont
  fonts-ipaexfont-gothic
  fonts-ipaexfont-mincho
  fonts-takao
  fonts-lmodern
  fonts-stix
  fonts-stix2
  fonts-texgyre
)

to_install=()
to_install+=("${base_pkgs[@]}")
for pkg in "${optional_pkgs[@]}"; do
  if _apt_pkg_available "${pkg}"; then
    to_install+=("${pkg}")
  fi
done

if [[ "${INSTALL_MS_FONTS:-0}" == "1" ]]; then
  if _apt_pkg_available "ttf-mscorefonts-installer"; then
    echo "==> 将安装 Microsoft Core Fonts（需要联网下载，且包含许可/EULA）..."
    if _apt_pkg_available "debconf-utils"; then
      sudo apt-get install -y --no-install-recommends debconf-utils
    fi
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | sudo debconf-set-selections || true
    to_install+=("ttf-mscorefonts-installer")
  else
    echo "==> 未找到 ttf-mscorefonts-installer（可能未启用 multiverse），跳过 Microsoft Core Fonts"
  fi
fi

sudo apt-get install -y --no-install-recommends "${to_install[@]}"

CUSTOM_DIR="${SCRIPT_DIR}/fonts"
if [[ -d "${CUSTOM_DIR}" ]]; then
  echo "==> 检测到自定义字体目录: ${CUSTOM_DIR}"
  echo "    将其中的 .ttf/.otf/.ttc 安装到 /usr/local/share/fonts/labprinter/"
  sudo mkdir -p /usr/local/share/fonts/labprinter

  found=0
  while IFS= read -r -d '' f; do
    found=1
    sudo cp -f "$f" /usr/local/share/fonts/labprinter/
  done < <(find "${CUSTOM_DIR}" -maxdepth 1 -type f \( -iname '*.ttf' -o -iname '*.otf' -o -iname '*.ttc' \) -print0)

  if [[ "${found}" -eq 0 ]]; then
    echo "    (未发现字体文件，跳过复制)"
  fi
else
  echo "==> 未发现自定义字体目录: ${CUSTOM_DIR} （可选）"
  echo "    如需安装 Windows 专有字体（宋体/黑体/微软雅黑等），可把字体文件复制到该目录后再运行本脚本。"
fi

ALIAS_FILE="/etc/fonts/conf.d/99-labprinter-windows-fonts.conf"
echo "==> 写入 fontconfig 别名映射: ${ALIAS_FILE}"
sudo tee "${ALIAS_FILE}" >/dev/null <<'EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <!--
    注意：脚本会在写入后把 <prefer> 统一转换为 <accept>。
    目的：当你安装了真实 Windows 字体（放入 deploy/fonts/）时，优先使用原字体；仅在字体缺失/缺字时才回退到这些候选字体。
  -->
  <!-- CJK: common Windows font families -->
  <alias>
    <family>SimSun</family>
    <prefer>
      <family>Noto Serif CJK SC</family>
      <family>AR PL UMing CN</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>宋体</family>
    <prefer>
      <family>Noto Serif CJK SC</family>
      <family>AR PL UMing CN</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>SimSun-ExtB</family>
    <prefer>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
      <family>Unifont</family>
    </prefer>
  </alias>
  <alias>
    <family>NSimSun</family>
    <prefer>
      <family>Noto Serif CJK SC</family>
      <family>AR PL UMing CN</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>新宋体</family>
    <prefer>
      <family>Noto Serif CJK SC</family>
      <family>AR PL UMing CN</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>

  <alias>
    <family>SimHei</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>WenQuanYi Zen Hei</family>
      <family>WenQuanYi Micro Hei</family>
      <family>Noto Sans CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>黑体</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>WenQuanYi Zen Hei</family>
      <family>WenQuanYi Micro Hei</family>
      <family>Noto Sans CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>华文黑体</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>Noto Sans CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>STHeiti</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>Noto Sans CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>Heiti SC</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>Noto Sans CJK TC</family>
    </prefer>
  </alias>

  <alias>
    <family>Microsoft YaHei</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>WenQuanYi Micro Hei</family>
    </prefer>
  </alias>
  <alias>
    <family>Microsoft YaHei UI</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>WenQuanYi Micro Hei</family>
    </prefer>
  </alias>
  <alias>
    <family>微软雅黑</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>WenQuanYi Micro Hei</family>
    </prefer>
  </alias>
  <alias>
    <family>Microsoft YaHei Light</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>WenQuanYi Micro Hei</family>
    </prefer>
  </alias>
  <alias>
    <family>DengXian</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>WenQuanYi Micro Hei</family>
    </prefer>
  </alias>
  <alias>
    <family>等线</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>WenQuanYi Micro Hei</family>
    </prefer>
  </alias>
  <alias>
    <family>PingFang SC</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>WenQuanYi Micro Hei</family>
    </prefer>
  </alias>
  <alias>
    <family>苹方</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>WenQuanYi Micro Hei</family>
    </prefer>
  </alias>

  <!-- Traditional Chinese -->
  <alias>
    <family>Microsoft JhengHei</family>
    <prefer>
      <family>Noto Sans CJK TC</family>
      <family>Noto Sans CJK SC</family>
    </prefer>
  </alias>
  <alias>
    <family>Microsoft JhengHei UI</family>
    <prefer>
      <family>Noto Sans CJK TC</family>
      <family>Noto Sans CJK SC</family>
    </prefer>
  </alias>
  <alias>
    <family>微軟正黑體</family>
    <prefer>
      <family>Noto Sans CJK TC</family>
      <family>Noto Sans CJK SC</family>
    </prefer>
  </alias>
  <alias>
    <family>PMingLiU</family>
    <prefer>
      <family>Noto Serif CJK TC</family>
      <family>Noto Serif CJK SC</family>
      <family>AR PL UMing CN</family>
    </prefer>
  </alias>
  <alias>
    <family>MingLiU</family>
    <prefer>
      <family>Noto Serif CJK TC</family>
      <family>Noto Serif CJK SC</family>
      <family>AR PL UMing CN</family>
    </prefer>
  </alias>
  <alias>
    <family>新細明體</family>
    <prefer>
      <family>Noto Serif CJK TC</family>
      <family>Noto Serif CJK SC</family>
      <family>AR PL UMing CN</family>
    </prefer>
  </alias>

  <alias>
    <family>KaiTi</family>
    <prefer>
      <family>AR PL UKai CN</family>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>楷体</family>
    <prefer>
      <family>AR PL UKai CN</family>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>KaiTi_GB2312</family>
    <prefer>
      <family>AR PL UKai CN</family>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>华文楷体</family>
    <prefer>
      <family>AR PL UKai CN</family>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>STKaiti</family>
    <prefer>
      <family>AR PL UKai CN</family>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>

  <alias>
    <family>FangSong</family>
    <prefer>
      <family>AR PL UMing CN</family>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>仿宋</family>
    <prefer>
      <family>AR PL UMing CN</family>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>FangSong_GB2312</family>
    <prefer>
      <family>AR PL UMing CN</family>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>华文仿宋</family>
    <prefer>
      <family>AR PL UMing CN</family>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>STFangsong</family>
    <prefer>
      <family>AR PL UMing CN</family>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>

  <alias>
    <family>华文宋体</family>
    <prefer>
      <family>Noto Serif CJK SC</family>
      <family>AR PL UMing CN</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>华文中宋</family>
    <prefer>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
      <family>AR PL UMing CN</family>
    </prefer>
  </alias>
  <alias>
    <family>STZhongsong</family>
    <prefer>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
      <family>AR PL UMing CN</family>
    </prefer>
  </alias>
  <alias>
    <family>华文细黑</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>Noto Sans CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>STXihei</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>Noto Sans CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>STSong</family>
    <prefer>
      <family>Noto Serif CJK SC</family>
      <family>AR PL UMing CN</family>
      <family>Noto Serif CJK TC</family>
    </prefer>
  </alias>
  <alias>
    <family>Songti SC</family>
    <prefer>
      <family>Noto Serif CJK SC</family>
      <family>Noto Serif CJK TC</family>
      <family>AR PL UMing CN</family>
    </prefer>
  </alias>

  <!-- Office defaults (improves layout fidelity) -->
  <alias>
    <family>Calibri</family>
    <prefer>
      <family>Carlito</family>
      <family>Noto Sans</family>
      <family>Liberation Sans</family>
      <family>DejaVu Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Calibri Light</family>
    <prefer>
      <family>Carlito</family>
      <family>Noto Sans</family>
      <family>Liberation Sans</family>
      <family>DejaVu Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Cambria</family>
    <prefer>
      <family>Caladea</family>
      <family>Noto Serif</family>
      <family>Liberation Serif</family>
      <family>DejaVu Serif</family>
    </prefer>
  </alias>
  <alias>
    <family>Cambria Math</family>
    <prefer>
      <family>STIX Two Math</family>
      <family>STIXGeneral</family>
      <family>Latin Modern Math</family>
      <family>DejaVu Serif</family>
    </prefer>
  </alias>
  <alias>
    <family>Consolas</family>
    <prefer>
      <family>DejaVu Sans Mono</family>
      <family>Noto Sans Mono</family>
      <family>Liberation Mono</family>
    </prefer>
  </alias>
  <alias>
    <family>Microsoft Sans Serif</family>
    <prefer>
      <family>DejaVu Sans</family>
      <family>Noto Sans</family>
      <family>Liberation Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>MS Sans Serif</family>
    <prefer>
      <family>DejaVu Sans</family>
      <family>Noto Sans</family>
      <family>Liberation Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Arial Unicode MS</family>
    <prefer>
      <family>Noto Sans</family>
      <family>DejaVu Sans</family>
      <family>Unifont</family>
    </prefer>
  </alias>
  <alias>
    <family>Helvetica</family>
    <prefer>
      <family>DejaVu Sans</family>
      <family>Noto Sans</family>
      <family>Liberation Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Helvetica Neue</family>
    <prefer>
      <family>DejaVu Sans</family>
      <family>Noto Sans</family>
      <family>Liberation Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Georgia</family>
    <prefer>
      <family>DejaVu Serif</family>
      <family>Noto Serif</family>
      <family>Liberation Serif</family>
    </prefer>
  </alias>
  <alias>
    <family>Tahoma</family>
    <prefer>
      <family>DejaVu Sans</family>
      <family>Noto Sans</family>
      <family>Liberation Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Verdana</family>
    <prefer>
      <family>DejaVu Sans</family>
      <family>Noto Sans</family>
      <family>Liberation Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Segoe UI</family>
    <prefer>
      <family>Noto Sans</family>
      <family>DejaVu Sans</family>
      <family>Liberation Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Segoe UI Symbol</family>
    <prefer>
      <family>Noto Sans Symbols2</family>
      <family>Noto Sans Symbols</family>
      <family>DejaVu Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Segoe UI Emoji</family>
    <prefer>
      <family>Noto Color Emoji</family>
      <family>Noto Emoji</family>
      <family>DejaVu Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Apple Color Emoji</family>
    <prefer>
      <family>Noto Color Emoji</family>
      <family>Noto Emoji</family>
      <family>DejaVu Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Wingdings</family>
    <prefer>
      <family>OpenSymbol</family>
      <family>DejaVu Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Webdings</family>
    <prefer>
      <family>OpenSymbol</family>
      <family>DejaVu Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Times New Roman</family>
    <prefer>
      <family>Liberation Serif</family>
      <family>Noto Serif</family>
      <family>DejaVu Serif</family>
    </prefer>
  </alias>
  <alias>
    <family>Arial</family>
    <prefer>
      <family>Liberation Sans</family>
      <family>Noto Sans</family>
      <family>DejaVu Sans</family>
    </prefer>
  </alias>
  <alias>
    <family>Courier New</family>
    <prefer>
      <family>Liberation Mono</family>
      <family>DejaVu Sans Mono</family>
      <family>Noto Sans Mono</family>
    </prefer>
  </alias>

  <!-- Japanese -->
  <alias>
    <family>MS Gothic</family>
    <prefer>
      <family>Noto Sans CJK JP</family>
      <family>IPAexGothic</family>
      <family>IPAGothic</family>
    </prefer>
  </alias>
  <alias>
    <family>MS PGothic</family>
    <prefer>
      <family>Noto Sans CJK JP</family>
      <family>IPAexGothic</family>
      <family>IPAGothic</family>
    </prefer>
  </alias>
  <alias>
    <family>MS Mincho</family>
    <prefer>
      <family>Noto Serif CJK JP</family>
      <family>IPAexMincho</family>
      <family>IPAMincho</family>
    </prefer>
  </alias>
  <alias>
    <family>MS PMincho</family>
    <prefer>
      <family>Noto Serif CJK JP</family>
      <family>IPAexMincho</family>
      <family>IPAMincho</family>
    </prefer>
  </alias>
  <alias>
    <family>Meiryo</family>
    <prefer>
      <family>Noto Sans CJK JP</family>
      <family>IPAexGothic</family>
      <family>IPAGothic</family>
    </prefer>
  </alias>

  <!-- Korean -->
  <alias>
    <family>Malgun Gothic</family>
    <prefer>
      <family>Noto Sans CJK KR</family>
      <family>NanumGothic</family>
      <family>UnDotum</family>
    </prefer>
  </alias>
  <alias>
    <family>Gulim</family>
    <prefer>
      <family>Noto Sans CJK KR</family>
      <family>NanumGothic</family>
      <family>UnGulim</family>
    </prefer>
  </alias>
  <alias>
    <family>굴림</family>
    <prefer>
      <family>Noto Sans CJK KR</family>
      <family>NanumGothic</family>
      <family>UnGulim</family>
    </prefer>
  </alias>
  <alias>
    <family>Dotum</family>
    <prefer>
      <family>Noto Sans CJK KR</family>
      <family>NanumGothic</family>
      <family>UnDotum</family>
    </prefer>
  </alias>
  <alias>
    <family>돋움</family>
    <prefer>
      <family>Noto Sans CJK KR</family>
      <family>NanumGothic</family>
      <family>UnDotum</family>
    </prefer>
  </alias>
</fontconfig>
EOF

# prefer 会让“回退字体”强制优先，可能导致安装了真实字体也不生效；统一改为 accept（追加候选）。
sudo sed -i 's#<prefer>#<accept>#g; s#</prefer>#</accept>#g' "${ALIAS_FILE}"

echo "==> 刷新字体缓存..."
sudo fc-cache -fv

echo "==> 验证（查看匹配到的实际字体）..."
fc-match "SimSun" || true
fc-match "宋体" || true
fc-match "SimHei" || true
fc-match "Microsoft YaHei" || true
fc-match "Calibri" || true
fc-match "Cambria Math" || true
fc-match "Segoe UI Emoji" || true

echo ""
echo "字体安装与映射完成。"
echo "若仍有缺字："
echo "1) 先检查 LibreOffice 转换出的 PDF 本身是否缺字（缺字=字体问题）"
echo "2) PDF 正常但打印缺字/失败：可在运行服务时设置 PDF_PREPROCESS=gs-pdfwrite 或 gs-rasterize 作为兜底"

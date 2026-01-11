将“真实字体文件”放到此目录（可选）。

用途：当 Word 文档指定了 Windows 专有字体（如 宋体/微软雅黑/黑体/Calibri 等）导致 Linux 转 PDF 或打印缺字时，可把对应字体复制到这里，然后运行：

```bash
cd labprinter_linux
./deploy/install_fonts.sh
```

支持的格式：`.ttf` / `.ttc` / `.otf`

提示：
- 如果你希望脚本额外安装 Microsoft Core Fonts（需要联网下载且包含许可/EULA），可用：`INSTALL_MS_FONTS=1 ./deploy/install_fonts.sh`
- 请勿将该目录中的字体文件提交到 Git/GitHub（多数 Windows 字体不允许再分发）；本目录已提供 `.gitignore` 进行保护。

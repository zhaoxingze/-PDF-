# PDF论文翻译工具

将英文PDF论文翻译为中文，保持原始排版格式。

## 功能特点

- 支持英文PDF论文翻译为中文
- 保持原始PDF排版格式（字体大小、位置、图片等）
- 支持多种翻译方式：Google翻译、百度翻译API、本地翻译
- 支持扫描版PDF的OCR识别
- 简单易用的GUI界面

## 安装步骤

### 1. 创建Anaconda环境

```bash
conda create -n pdf-translator python=3.10
conda activate pdf-translator
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 启动GUI

```bash
conda activate pdf-translator
python main.py
```

或直接双击 `run.cmd`

### 操作流程

1. 选择翻译方式（Google翻译/百度翻译API/本地翻译）
2. 点击"浏览"选择输入PDF文件
3. 选择输出路径（自动生成）
4. 点击"开始翻译"
5. 等待翻译完成

## 支持的翻译方式

### 1. Google翻译（推荐）
- 免费，无需注册
- 无需下载模型
- 速度较快

### 2. 百度翻译API
- 需要API密钥
- 标准版免费（每月5万字符）
- 获取方式: https://fanyi-api.baidu.com/

### 3. 本地翻译
- 需要下载模型（约300MB）
- 需要VPN/代理下载模型

## 项目结构

```
pdf-word/
├── main.py              # 程序入口
├── config.py            # 配置文件
├── requirements.txt     # 依赖包列表
├── run.cmd              # 启动脚本
├── src/
│   ├── core/
│   │   ├── pdf_reader.py    # PDF读取模块
│   │   ├── pdf_writer.py    # PDF写入模块
│   │   ├── translator.py    # 翻译模块
│   │   └── ocr.py           # OCR模块
│   ├── gui/
│   │   └── app.py           # GUI界面
│   └── utils/
│       └── font_manager.py  # 字体管理
└── fonts/
    └── NotoSansSC-Regular.ttf  # 中文字体
```

## 注意事项

- 翻译质量取决于原始PDF的文本提取质量
- 大型PDF文件翻译时间较长，请耐心等待
- 建议使用Google翻译（免费且稳定）

## 常见问题

### Q: 翻译后中文显示为方块？

A: 确保 `fonts/NotoSansSC-Regular.ttf` 文件存在。

### Q: 翻译速度很慢？

A: Google翻译速度较快，本地翻译较慢。

### Q: 翻译质量不好？

A: 可以尝试切换不同的翻译方式。

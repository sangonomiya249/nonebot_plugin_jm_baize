# nonebot_plugin_jm_baize

NoneBot2 JM 漫画插件，支持搜索、详情查看与 PDF/ZIP 下载，结果以图片卡片展示。

## 🚀 快速开始

### 安装

```bash
pip install git+https://github.com/sangonomiya249/nonebot_plugin_jm_baize.git
```


### 配置

在 `.env` 中添加（可选，以下为默认值）：

```env
JM_DOWNLOAD_DIR=./data/downloads
JM_USE_API_CLIENT=true
JM_OUTPUT_FORMAT=pdf
JM_PDF_ENCRYPT=true
JM_DELETE_AFTER_UPLOAD=false
```

### 依赖

```bash
pip install jmcomic img2pdf pypdf
```

## 🎯 功能

### /jm搜索 — 搜索本子

按关键词搜索本子，支持多种排序方式，结果以图片卡片展示。

```
/jm搜索 关键词
/jm搜索 排序 关键词
```

**支持的排序**：默认 / 相关 / 最新 / 总排行 / 观看 / 点赞

<img src="https://raw.githubusercontent.com/sangonomiya249/nonebot_plugin_jm_baize/main/screenshots/search.png" width="600" alt="搜索">

---

### /jm详情 — 查看详情

查看本子的详细信息（标签、人物、章节列表、简介等）。

```
/jm详情 1446079
```

<img src="https://raw.githubusercontent.com/sangonomiya249/nonebot_plugin_jm_baize/main/screenshots/info.png" width="600" alt="详情">

---

### /jm下载 — 下载本子

下载本子并转为 PDF（支持加密）或 ZIP，上传到群文件或私聊。

```
/jm下载 1446079
```

<img src="https://raw.githubusercontent.com/sangonomiya249/nonebot_plugin_jm_baize/main/screenshots/download.png" width="600" alt="下载">

---

### /下一页 / /上一页

基于最近一次搜索翻页，无需重复输入关键词。

### /jm帮助

查看所有指令及使用示例。

## ⚙️ 配置项

| 变量 | 默认值 | 说明 |
| ---- | ---- | ---- |
| `JM_DOWNLOAD_DIR` | `/app/jm_downloads` | 下载目录 |
| `JM_USE_API_CLIENT` | `true` | 使用 API 客户端 |
| `JM_PROXY` | `""` | HTTP 代理地址 |
| `JM_IMAGE_SUFFIX` | `.jpg` | 图片后缀 |
| `JM_OUTPUT_FORMAT` | `pdf` | 输出格式（pdf / zip） |
| `JM_PDF_ENCRYPT` | `true` | PDF 加密 |
| `JM_DELETE_AFTER_UPLOAD` | `false` | 上传后删除本地文件 |

## 📁 目录结构

```
nonebot_plugin_jm_baize/
├── __init__.py          # 插件入口、matcher 注册
├── config.py            # 配置类、常量
├── render.py            # 图片渲染
├── client.py            # JM API 客户端
├── download.py          # 下载与文件处理
├── pyproject.toml       # 构建配置
├── README.md            # 本文档
└── data/                # 运行时数据（自动创建）
```

## 📦 依赖

- Python >= 3.9
- nonebot2 >= 2.2.0
- jmcomic >= 2.0
- Pillow >= 9.0
- img2pdf >= 0.4
- pypdf >= 3.0

## 🙏 鸣谢

- [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) — 本插件底层使用该项目提供的 JM Comic API 客户端

## 📄 许可证

MIT

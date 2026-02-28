# PaperSpider 文档

## 上手

### 安装

1) 安装 Python 3.10+ 和 `uv`。
2) 克隆仓库。
3) 运行应用：

```bash
uv run paperspider
```

### 选择会议与数据集

1) 在工作台打开 **Settings**。
2) 选择基础目录（数据存放在 `会议/年份` 目录下）。
3) 从列表选择已有数据集，或点击 **Add** 新建并选择会议/年份。
4) 点击 **Use selected** 进入工作台。

### 获取与同步论文列表

- 点击 **Fetch paper list** 获取或刷新所选会议/年份的论文列表。
- 论文列表保存在 SQLite 中，可随时重新打开。
- 当前支持会议：NeurIPS、ICML、ICLR。

### 添加筛选条件

1) 点击 **Add filter**。
2) 选择范围（All/Title/Authors/Abstract/Keywords）。
3) 选择匹配方式（contains / not contains）。
4) 选择角色：
   - **Must**：必须满足
   - **Should**：可选满足
   - **Must not**：必须排除
5) 设置 **Min should match** 以要求至少命中 N 个 Should 条件。
6) 点击 **Apply filter**。

### 选择与下载

- 使用勾选列选择论文，或用 **Select all / none / invert**。
- **Abstract**：
  - 若显示 **No**，点击单元格下载。
  - 若显示 **Yes**，悬浮可预览摘要。
- **PDF**：
  - 若显示 **No**，点击单元格下载。
  - 若显示 **Yes**，双击打开。
  - Ctrl+单击定位到文件夹。
- **Bibtex**：
  - 若显示 **No**，点击单元格下载。
  - 若显示 **Yes**，双击复制到剪贴板。
  - Ctrl+单击定位到文件夹。
- **Export selected**：
  - 对已选论文打开导出弹窗。
  - 格式支持 CSV、JSON、纯文本列表。
  - CSV/JSON 可选择导出字段（title/authors/abstract）。
  - 纯文本列表按一行一个标题导出。
  - 生成内容显示在文本框中，可全选复制，并提供 **Copy** 按钮。
- 下载过程中可点击 **Cancel Download** 取消。

### 数据结构

所有数据存放在：

```
<base folder>/<conference>/<year>/
  papers.sqlite
  pdf/
  bib/
```

## 开发

### 环境要求

- Python 3.10+
- `uv`

### 开发设置

1) Fork 或克隆仓库。
2) 安装依赖：

```bash
uv sync
```

3) 运行应用：

```bash
uv run paperspider
```

4) 运行测试：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

### 打包为可双击启动的应用

macOS：

```bash
uv run --with pyinstaller pyinstaller --noconfirm --clean --windowed --name PaperSpider paper_spider/__main__.py
```

Windows：

```bash
uv run --with pyinstaller pyinstaller --noconfirm --clean --windowed --name PaperSpider paper_spider/__main__.py
```

### 说明

- UI 使用 PyQt6 构建。
- 会议适配器位于 `paper_spider/conferences/`。
- 存储与数据库结构在 `paper_spider/storage.py`。

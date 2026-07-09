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

1) 从空状态或顶部数据集名称选择数据集开始。
2) 在顶部区域查看当前会议/年份。
3) 在独立的数据集窗口中设置基础目录、选择已有数据集，或选择会议/年份创建新数据集，然后加载到工作台。
4) 如需调整访问间隔，再从顶部区域打开 **Settings**。

### 获取与同步论文列表

- 点击 **Fetch list** 获取或刷新所选会议/年份的论文列表。
- 论文列表保存在 SQLite 中，可随时重新打开。
- 当前支持会议：NeurIPS、ICML、ICLR、AAAI、IJCAI、CVPR、ICCV、EMNLP、ACL、NAACL、SIGCOMM、NSDI、OSDI、ATC、FAST、USENIX Security、NDSS、VLDB。

### 添加筛选条件

1) 打开筛选区域。
2) 在 **Must**、**Should** 或 **Must not** 分组下添加规则。
3) 选择范围（All/Title/Authors/Abstract/Keywords）。
4) 选择匹配方式（contains / not contains）。
5) 输入规则文本。
6) 设置 **Min should match** 以要求至少命中 N 个 Should 条件。
7) 应用筛选条件。
8) 使用表格上方的快速搜索，在当前筛选结果内继续按关键词缩小列表，不改变已保存的筛选规则。

筛选角色含义：

- **Must**：所有启用的 Must 规则都必须命中。
- **Should**：默认是可选条件；当 **Min should match** 大于 0 时，要求至少命中指定数量。
- **Must not**：命中的论文会被排除。

### 选择、查看与下载

- 使用勾选列选择论文，或用表格下方动作栏里的 **Select all / none / invert**。
- 使用论文表格完成选择和元数据浏览。Abstract/PDF/Bib 操作不再嵌入表格列。
- 使用详情面板查看当前论文：
  - 阅读完整摘要。
  - 复制已有摘要，或下载缺失摘要。
  - 下载缺失 PDF，或打开/定位已有 PDF 文件。
  - 获取/导出、复制或定位 BibTeX 文件。
- 使用状态/日志区域查看获取与下载进度。
- 摘要或 PDF 下载运行时，可在状态/日志区域使用取消控件。

### 导出选中论文

- 选择一篇或多篇论文后，点击 **Export selected**。
- 格式支持 CSV、JSON、纯文本列表。
- CSV/JSON 可选择导出字段（title/authors/abstract）。
- 纯文本列表按一行一个标题导出。
- 生成内容显示在文本框中，可全选复制，并提供 **Copy** 按钮。

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
- CCF A 会议实现调研位于 `docs/ccf_a_conference_research.md`。

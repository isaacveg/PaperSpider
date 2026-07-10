# PaperSpider 使用说明

[项目首页](../README.zh.md) · [English guide](en.md)

PaperSpider 用来把完整的会议论文列表逐步缩小为需要关注的论文集合，并完成查看、下载和导出。

## 启动应用

安装 Python 3.10+ 和 [uv](https://docs.astral.sh/uv/)，克隆仓库后运行：

```bash
uv run paperspider
```

## 1. 选择会议

1. 点击顶部的数据集按钮，打开 **Datasets**。
2. 选择 PaperSpider 保存数据的基础目录。
3. 选择已有的会议和年份，点击 **Use selected**。
4. 如需新增数据集，点击 **Add Dataset**，选择会议和年份，再点击 **Fetch dataset**。

论文列表会保存在本地，下次可以直接打开。需要同步最新列表时，点击该数据集的 **Refresh**。

## 2. 使用 Filter

点击 **Add rule**，依次选择规则角色、字段、匹配方式和关键词：

- **Include**：论文必须符合该条件。
- **Prefer**：默认是偏好条件；设置 **Minimum preferred** 后，至少要符合指定数量的 Prefer 条件。
- **Exclude**：符合该条件的论文会被排除。

筛选范围可以是任意字段，也可以只检查标题、作者、摘要或关键词。不需要某条规则时，可以先取消其复选框而不必删除。设置完成后点击 **Apply**。

## 3. 进一步筛选

在工作台上方的 **Search papers** 中输入关键词。它只搜索当前筛选结果，不会改动 Filter 规则；清空搜索框即可回到完整的筛选结果。

## 4. 查看与下载

点击论文行后，右侧会显示标题、作者、分类、摘要和已有文件。

- 在右侧详情区复制或下载单篇摘要、打开单篇 PDF，或复制 BibTeX。
- 勾选多篇论文后，使用 **Download abstracts** 或 **Download PDFs** 批量下载。
- 使用表头复选框全选或清空当前可见论文，使用 **Invert** 反选。
- 展开 **Show log** 查看进度；批量任务运行时也可以在这里取消。

## 5. 导出结果

勾选需要的论文，点击 **Export selected**：

- 选择 **CSV** 或 **JSON**，可导出标题、作者和摘要。
- 选择 **Plain list**，按每行一个标题导出简单列表。

需要选中论文的 BibTeX 文件时，使用 **Export Bib**。

## 本地数据

PaperSpider 按以下结构保存数据：

```text
<基础目录>/<会议>/<年份>/
  papers.sqlite
  pdf/
  bib/
```

在 **Settings** 中可以调整请求间隔和界面外观。批量下载时建议保留适当的请求间隔。

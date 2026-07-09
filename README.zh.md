# PaperSpider（MVP）

[English README](README.md) | [中文 文档](docs/zh.md) | [Documentation](docs/en.md)

**最新动态**
- 2026-07-09：新增 AAAI、ICCV、IJCAI、FAST、USENIX Security、NDSS、VLDB 等 CCF A 会议适配器，并补充剩余 CCF A 会议路线文档。
- 2026-03-12：基于 SIGCOMM 官方 proceedings 页面与 DOI/Crossref 元数据，新增 SIGCOMM 会议适配器。
- 2026-03-12：基于官方 CVF Open Access 仓库，新增 CVPR 会议适配器。
- 2026-03-12：基于 ACL Anthology 与 USENIX 通用实现，新增 ACL、NAACL、OSDI、ATC 会议适配器。
- 2026-03-11：新增 EMNLP 与 NSDI 会议适配器，并补充单元测试。
- 2026-02-28：新增选中文章导出弹窗（CSV/JSON/纯文本列表），支持字段选择与一键复制。
- 2026-02-28：新增 ICML 与 ICLR 会议适配器，并补充单元测试。
- 2026-01-10：增加工作台优先流程、多条件筛选（Must/Should/Must not）、可取消下载、PDF/Bib 快捷操作与访问间隔设置。

一个基于 PyQt 的最小可用工具，用于获取会议论文列表、下载摘要/PDF，并用 SQLite 管理。

## 功能

- 会议适配器：NeurIPS、ICML、ICLR、AAAI、IJCAI、CVPR、ICCV、EMNLP、ACL、NAACL、SIGCOMM、NSDI、OSDI、ATC、FAST、USENIX Security、NDSS、VLDB
- 工作台优先 UI：从空状态或顶部数据集名称选择/管理数据集，再获取论文列表
- 筛选条件：Must/Should/Must not + 最小 Should 命中数，并支持在当前论文列表内快速搜索
- 论文表格专注显示元数据，Abstract/PDF/Bib 操作从表格列移出
- 详情面板可查看完整摘要，并执行摘要复制/下载、PDF 下载/打开、Bib 复制与定位操作
- 选中论文导出（CSV/JSON/纯文本列表），支持字段选择与一键复制
- 状态/日志区域显示进度，并支持取消摘要/PDF 下载
- 访问间隔设置（礼貌爬取）
- 数据按 `会议/年份` 组织：SQLite + `pdf/` + `bib/`

## 运行

```bash
uv run paperspider
```

也可以直接运行模块：

```bash
uv run -m paper_spider
```

## 测试

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## 说明

- 从工作台空状态或顶部数据集名称选择/创建数据集；基础目录在 Datasets 中设置，Settings 只用于设置访问间隔。
- 数据会存放在 `会议/年份/` 目录下。
- 摘要存 SQLite；bibtex 同时存 SQLite 并导出到文件。

## 许可证

Apache-2.0，详见 `LICENSE` 与 `NOTICE`。

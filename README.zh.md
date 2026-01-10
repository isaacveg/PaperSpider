# PaperSpider（MVP）

[English README](README.md) | [中文 文档](docs/zh.md) | [Documentation](docs/en.md)

**最新动态**
- 2026-01-10：增加工作台优先流程、多条件筛选（Must/Should/Must not）、可取消下载、PDF/Bib 快捷操作与访问间隔设置。

一个基于 PyQt 的最小可用工具，用于获取 NeurIPS 论文列表、下载摘要/PDF，并用 SQLite 管理。

## 功能

- NeurIPS 论文列表与详情抓取
- 工作台式 UI 与论文筛选、选择
- 筛选条件：Must/Should/Must not + 最小 Should 命中数
- 摘要下载（悬浮预览；点击缺失项可下载）
- PDF 下载（点击下载；双击打开；Ctrl+单击定位文件）
- Bibtex 导出（点击下载；双击复制；Ctrl+单击定位文件）
- 摘要/PDF 下载可取消
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

## 说明

- 在 Settings 中选择输出目录；数据会存放在 `会议/年份/` 目录下。
- 摘要存 SQLite；bibtex 同时存 SQLite 并导出到文件。

## 许可证

Apache-2.0，详见 `LICENSE` 与 `NOTICE`。

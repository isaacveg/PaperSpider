# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

"""Minimal Chinese/English UI copy selected from the system locale."""

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import QLibraryInfo, QLocale, QTranslator
from PyQt6.QtWidgets import QApplication

_LANGUAGE: Optional[str] = None
_QT_TRANSLATOR: Optional[QTranslator] = None

_ZH = {
    "PaperSpider Workspace": "PaperSpider 工作区",
    "All papers": "全部论文",
    "Filters": "筛选",
    "Conference datasets": "会议数据集",
    "Settings": "设置",
    "Add dataset": "添加数据集",
    "Search in results": "在结果中搜索",
    "Filter papers": "筛选论文",
    "No dataset selected": "未选择数据集",
    "No dataset loaded": "未加载数据集",
    "Choose a dataset to start": "选择一个数据集开始",
    "Choose dataset": "选择数据集",
    "Papers / authors": "论文 / 作者",
    "Abstract": "摘要",
    "PDF": "PDF",
    "Abstract available": "已有摘要",
    "No abstract available": "暂无摘要",
    "PDF available": "已有 PDF",
    "No PDF available": "暂无 PDF",
    "Download abstracts": "下载摘要",
    "Download PDFs": "下载 PDF",
    "Export": "导出",
    "Invert": "反选",
    "Ready": "就绪",
    "Task log": "任务日志",
    "Cancel": "取消",
    "Confirm": "确认",
    "Loading papers...": "正在加载论文...",
    "Applying filters...": "正在应用筛选...",
    "Fetching paper list...": "正在抓取论文列表...",
    "Downloading abstracts...": "正在下载摘要...",
    "Downloading PDFs...": "正在下载 PDF...",
    "Downloading abstracts and PDFs...": "正在下载摘要和 PDF...",
    "Fetch this dataset": "抓取此数据集",
    "Open datasets": "打开数据集",
    "Clear search": "清空搜索",
    "Clear filters": "清空筛选",
    "No papers match the quick filter": "没有论文符合搜索条件",
    "Clear the quick filter or try a broader keyword.": "清空搜索或尝试更宽泛的关键词。",
    "No papers match the current filters": "没有论文符合当前筛选条件",
    "Try clearing filters or lowering the minimum Prefer match count.": "尝试清空筛选或降低偏好条件的最低匹配数。",
    "Select a base folder, conference, and year before fetching papers.": "请先选择基础目录、会议和年份，再抓取论文。",
    "Open Datasets and fetch the paper list before browsing papers.": "请打开数据集并抓取论文列表后再浏览。",
    "Unknown authors": "未知作者",
    "Uncategorized": "未分类",
    "No paper selected": "未选择论文",
    "Select a row to preview details.": "选择一篇论文查看详情。",
    "Abstract will appear here when available.": "摘要下载后会显示在这里。",
    "Download abstract": "下载摘要",
    "Copy abstract": "复制摘要",
    "Open PDF": "打开 PDF",
    "Download PDF": "下载 PDF",
    "Copy BibTeX": "复制 BibTeX",
    "Local files": "本地文件",
    "BibTeX copied to clipboard.": "BibTeX 已复制到剪贴板。",
    "Copied bibtex: {path}": "已复制 BibTeX：{path}",
    "Abstract copied to clipboard.": "摘要已复制到剪贴板。",
    "Copied bibtex to clipboard": "BibTeX 已复制到剪贴板",
    "Copied abstract to clipboard": "摘要已复制到剪贴板",
    "Missing file: {path}": "文件不存在：{path}",
    "Canceled": "已取消",
    "Finished with issues": "完成但有错误",
    "Done": "完成",
    "Error": "错误",
    "Missing": "缺少信息",
    "Select": "选择",
    "Busy": "正在运行",
    "Please choose a dataset first.": "请先选择数据集。",
    "Please select papers first.": "请先选择论文。",
    "Abstract download already running. Use the cancel control in the status bar.": "摘要下载正在进行，请使用底部状态栏的取消按钮。",
    "PDF download already running. Use the cancel control in the status bar.": "PDF 下载正在进行，请使用底部状态栏的取消按钮。",
    "Abstract download already running.": "摘要下载正在进行。",
    "PDF download already running.": "PDF 下载正在进行。",
    "Conference not available": "会议不可用",
    "Loaded {count} papers": "已加载 {count} 篇论文",
    "Showing {visible} of {filtered} filtered papers ({total} total)": "显示 {visible} / {filtered} 篇筛选结果（共 {total} 篇）",
    "Error: {message}": "错误：{message}",
    "Downloaded {count} {artifact}": "已下载 {count} 个{artifact}",
    "Skipped {count} already available": "跳过 {count} 个已有文件",
    "Failed {count}": "失败 {count} 个",
    "Failed {artifact}: {title} ({message})": "失败 {artifact}：{title}（{message}）",
    "Canceling abstract download...": "正在取消摘要下载...",
    "Canceling PDF download...": "正在取消 PDF 下载...",
    "Refresh": "刷新",
    "Refresh dataset": "刷新数据集",
    "Datasets": "数据集",
    "Base folder": "基础目录",
    "Folder": "目录",
    "Browse": "浏览",
    "Conference": "会议",
    "Year": "年份",
    "Status": "状态",
    "Papers": "论文数",
    "Actions": "操作",
    "Fetched": "已获取",
    "Add Dataset": "添加数据集",
    "New dataset": "新数据集",
    "Fetch dataset": "抓取数据集",
    "Use selected": "使用选中项",
    "Search datasets...": "搜索数据集...",
    "Storage: {path}": "存储位置：{path}",
    "Storage: Not selected": "存储位置：未选择",
    "Select output directory": "选择输出目录",
    "Open in folder": "在文件夹中打开",
    "Delete dataset": "删除数据集",
    "Dataset options": "数据集选项",
    "Dataset folder not found.": "数据集文件夹不存在。",
    "This removes all local files for this dataset and moves it to .trash. You will need to fetch it again. Continue?": "这会移除该数据集的全部本地文件（移动到 .trash），之后需要重新抓取。是否继续？",
    "Failed to delete dataset.": "删除数据集失败。",
    "Dataset deleted. Fetch it again to use it.": "数据集已删除，需要时请重新抓取。",
    "This will move the dataset folder to .trash. Continue?": "这会将会话数据文件夹移动到 .trash，是否继续？",
    "Delete": "删除",
    "Please choose a conference.": "请选择会议。",
    "Invalid year": "年份无效",
    "Enter a four-digit conference year.": "请输入四位会议年份。",
    "Year must be between {minimum} and {maximum}.": "年份必须在 {minimum} 到 {maximum} 之间。",
    "Please choose a base folder first.": "请先选择基础目录。",
    "Failed to move dataset to .trash": "无法将数据集移动到 .trash",
    "PaperSpider - Settings": "PaperSpider - 设置",
    "Request Interval": "请求间隔",
    "Delay Between Requests": "请求间隔",
    "Time to wait between consecutive requests to the server.": "连续请求服务器之间的等待时间。",
    "Appearance": "外观",
    "Theme": "主题",
    "Follow the system appearance or choose light or dark.": "跟随系统外观，或选择浅色/深色。",
    "Theme Color": "主题色",
    "Choose the accent color for buttons and highlights.": "选择按钮和高亮的强调色。",
    "Restore Defaults": "恢复默认",
    "Save / Close": "保存 / 关闭",
    "System": "跟随系统",
    "Light": "浅色",
    "Dark": "深色",
    "Blue": "蓝色",
    "Forest": "森林绿",
    "Green": "绿色",
    "Purple": "紫色",
    "Orange": "橙色",
    "Slate": "石板灰",
    "Export Selected Papers": "导出选中论文",
    "Format": "格式",
    "Plain text list": "纯文本列表",
    "Include fields": "包含字段",
    "Authors": "作者",
    "Generate": "生成",
    "Download": "下载",
    "Copy": "复制",
    "Untitled paper": "未命名论文",
    "Show in folder": "在文件夹中显示",
    "Collapse sidebar": "收起侧边栏",
    "Show sidebar": "显示侧边栏",
    "Hide details": "收起详情",
    "Show details": "显示详情",
    "Fetching BibTeX...": "正在获取 BibTeX...",
    "BibTeX not found": "未找到 BibTeX",
    "abstracts": "摘要",
    "PDFs": "PDF",
    "Copied": "已复制",
    "Close": "关闭",
    "Invalid export options": "导出选项无效",
    "Generated export content will appear here.": "生成的导出内容会显示在这里。",
    "Select at least one field.": "至少选择一个导出字段。",
    "Add rule": "添加规则",
    "Add an Include rule": "添加一条包含规则",
    "Apply": "应用",
    "Clear": "清空",
    "Include": "包含",
    "Prefer": "偏好",
    "Exclude": "排除",
    "Any field": "任意字段",
    "Title": "标题",
    "Category": "分类",
    "Keywords": "关键词",
    "contains": "包含",
    "does not contain": "不包含",
    "Include = required, Prefer = optional, Exclude = remove matches": "包含 = 必须匹配，偏好 = 可选加分，排除 = 移除匹配",
    "Remove this rule": "删除此规则",
    "Include rules must match. Prefer rules can contribute to a minimum. Exclude rules remove matches.": "包含条件必须满足，偏好条件可计入最低匹配数，排除条件会移除论文。",
    "Minimum preferred matches": "偏好条件最低匹配数",
    "Require at least N Prefer rules to match": "要求至少匹配 N 条偏好条件",
    "keyword, author, title...": "关键词、作者、标题...",
    "{count} paper": "{count} 篇论文",
    "{count} papers": "{count} 篇论文",
    "{count} match": "{count} 篇匹配",
    "{count} matches": "{count} 篇匹配",
    "{count} selected": "已选 {count} 篇",
}


def _detect_language() -> str:
    override = (os.environ.get("PAPERSPIDER_LANG") or "").strip().lower()
    if override in {"zh", "en"}:
        return override
    if QLocale.system().language() == QLocale.Language.Chinese:
        return "zh"
    return "en"


def current_language() -> str:
    """Return the active UI language, honoring PAPERSPIDER_LANG for tests."""

    global _LANGUAGE
    if _LANGUAGE is None:
        _LANGUAGE = _detect_language()
    return _LANGUAGE


def set_language(language: str) -> None:
    """Override the UI language; widget text built afterwards uses it."""

    global _LANGUAGE
    normalized = language.strip().lower()
    if normalized not in {"zh", "en"}:
        raise ValueError("language must be 'zh' or 'en'")
    _LANGUAGE = normalized


def reset_language() -> None:
    """Forget the cached language so the next call re-detects it."""

    global _LANGUAGE
    _LANGUAGE = None


def tr(text: str, **kwargs) -> str:
    """Translate English UI copy to the active language."""

    template = _ZH.get(text, text) if current_language() == "zh" else text
    if kwargs:
        return template.format(**kwargs)
    return template


def paper_count(count: int) -> str:
    key = "{count} paper" if count == 1 else "{count} papers"
    return tr(key, count=count)


def match_count(count: int) -> str:
    key = "{count} match" if count == 1 else "{count} matches"
    return tr(key, count=count)


def selected_count(count: int) -> str:
    return tr("{count} selected", count=count)


_TRACK_ZH = {
    "main": "主会",
    "technical": "技术",
    "workshop": "研讨会",
}
_TYPE_ZH = {
    "conference": "会议论文",
    "long": "长文",
    "short": "短文",
    "poster": "海报",
    "demo": "演示",
}


def display_category(track: str, paper_type: str) -> str:
    """Format a paper category for the active language."""

    track = (track or "").strip()
    paper_type = (paper_type or "").strip()
    if current_language() == "zh":
        return (
            f"{_TRACK_ZH.get(track, track)} / "
            f"{_TYPE_ZH.get(paper_type, paper_type)}"
        ).strip(" /")
    return f"{track} / {paper_type}".strip(" /")


def install_qt_translations(app: QApplication) -> None:
    """Load Qt's own Chinese catalog for standard dialogs and buttons."""

    global _QT_TRANSLATOR
    if current_language() != "zh" or _QT_TRANSLATOR is not None:
        return
    translator = QTranslator(app)
    translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load("qtbase_zh_CN", translations):
        app.installTranslator(translator)
        _QT_TRANSLATOR = translator
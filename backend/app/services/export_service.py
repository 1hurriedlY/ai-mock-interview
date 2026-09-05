"""报告导出服务：把面试评分报告渲染成 DOCX / PDF 文件。

职责：
- 接收 InterviewReport + 关联 InterviewSession，拼装结构化内容（两种格式内容一致）
- 用 python-docx 渲染 .docx；用 reportlab 渲染 .pdf（中文：优先系统 TTF，回退 STSong-Light CID 字体）
- 文件写入 config.EXPORT_DIR，命名 report_{report_id}.docx / .pdf
- 不处理数据库与权限校验：由路由层确认报告存在且归属当前用户后再调用

导出内容结构：
  标题 / 基本信息（岗位、面试官、时间）/ 综合得分 / 面试总评 /
  五维能力评分 / 岗位匹配分析 / 改进建议 / 表情表现分析（有表情数据时）
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from .. import config
from ..models import InterviewReport, InterviewSession
from ..services.agents.question_agent import ROLE_NAMES

logger = logging.getLogger(__name__)

# 五维评分展示顺序（dimensions dict 键已是中文，这里只保证输出顺序稳定）
_DIM_ORDER = ["专业技能", "沟通表达", "逻辑思维", "项目经验", "岗位匹配"]

# PDF 系统中文字体候选（Windows 常见字体）；.ttc 需指定 subfontIndex
_FONT_CANDIDATES = [
    ("msyh.ttc", 0),      # 微软雅黑
    ("simhei.ttf", 0),    # 黑体
    ("simsun.ttc", 0),    # 宋体
]


def export_path(report_id: int, fmt: str) -> Path:
    """导出文件在磁盘上的确定性路径（供下载路由复用，不重复生成）。"""
    return config.EXPORT_DIR / f"report_{report_id}.{fmt.lower()}"


def write_export(
    report: InterviewReport,
    session: InterviewSession,
    fmt: str,
    messages: list[dict] | None = None,
) -> dict:
    """渲染报告为文件并落盘，返回下载元信息。

    fmt 仅支持 docx / pdf。文件重复导出会覆盖同名旧文件。
    messages 为会话消息列表（含 reference），用于报告中的「逐题复盘」。
    """
    fmt = fmt.lower()
    if fmt not in ("docx", "pdf"):
        raise ValueError(f"不支持的导出格式：{fmt}")

    config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    ctx = _build_context(report, session, messages)
    path = export_path(report.id, fmt)

    if fmt == "docx":
        _render_docx(ctx, path)
    else:
        _render_pdf(ctx, path)

    return {
        "report_id": report.id,
        "format": fmt,
        "filename": path.name,
        "size": path.stat().st_size,
        "url": f"/api/report/{report.id}/download?format={fmt}",
    }


# ---------- 内容拼装 ----------
def _build_context(
    report: InterviewReport,
    session: InterviewSession,
    messages: list[dict] | None = None,
) -> dict:
    """把 ORM 报告（JSON 字符串字段）解析成渲染用的纯字典。"""
    dims = _load_json(report.dimensions, {})
    if not isinstance(dims, dict):
        dims = {}
    dims = {name: dims.get(name) for name in _DIM_ORDER}

    match = _load_json(report.match_analysis, {})
    if not isinstance(match, dict):
        match = {}

    suggestions = _load_json(report.suggestions, []) or []
    expr = _load_json(report.expression_analysis, {}) or {}
    if not isinstance(expr, dict):
        expr = {}

    created = report.created_at.strftime("%Y-%m-%d %H:%M") if report.created_at else ""
    return {
        "job_title": session.job_title or "",
        "role_name": ROLE_NAMES.get(session.interviewer_role, session.interviewer_role or ""),
        "created_at": created,
        "score": report.overall_score or 0,
        "summary": report.summary or "",
        "dimensions": dims,
        "match_level": str(match.get("match_level") or ""),
        "match_reason": str(match.get("reason") or ""),
        "strengths": list(match.get("strengths") or []),
        "gaps": list(match.get("gaps") or []),
        "suggestions": list(suggestions),
        "expr_comment": str(expr.get("comment") or ""),
        "expr_highlights": list(expr.get("highlights") or []),
        "qa_items": _qa_items_from_report(report, messages),
    }


def _qa_items_from_report(
    report: InterviewReport, messages: list[dict] | None
) -> list[dict]:
    """逐题复盘来源：优先报告里 AI 重新生成的参考答案(qna)；
    老报告没有 qna 时回退用会话消息里的面试参考要点。"""
    qna = _load_json(report.qna, [])
    if isinstance(qna, list) and qna:
        out = []
        for item in qna:
            question = str(item.get("question") or "").strip()
            if not question:
                continue
            out.append({
                "index": len(out) + 1,
                "question": question,
                "answer": str(item.get("answer") or ""),
                "ref": str(item.get("model_answer") or ""),
            })
        return out
    return _build_qa_items(messages)


def _build_qa_items(messages: list[dict] | None) -> list[dict]:
    """逐题复盘：面试官问题(含参考) + 紧随其后的用户回答，组成题目序列。"""
    if not messages:
        return []
    items = []
    for i, m in enumerate(messages):
        if m.get("role") != "assistant" or not m.get("reference"):
            continue
        answer_parts = []
        for nxt in messages[i + 1:]:
            if nxt.get("role") == "user":
                answer_parts.append(str(nxt.get("content") or ""))
            else:
                break
        items.append({
            "index": len(items) + 1,
            "question": str(m.get("content") or ""),
            "answer": "\n".join(answer_parts),
            "ref": str(m.get("reference") or ""),
        })
    return items


def _flat(text: str) -> str:
    """把文本里的换行压平成单行（docx/reportlab 段落不易渲染换行）。"""
    return " / ".join(line.strip() for line in str(text or "").splitlines() if line.strip())


def _load_json(raw: str | None, default):
    """安全解析 JSON 字符串字段；空或解析失败返回默认值。"""
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


# ---------- DOCX 渲染（python-docx） ----------
def _render_docx(ctx: dict, path: Path) -> None:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Pt

    doc = Document()

    # 中文字体：Normal 样式设为微软雅黑（含 eastAsia），保证中文不乱码
    normal = doc.styles["Normal"]
    normal.font.name = "Microsoft YaHei"
    normal.font.size = Pt(10.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

    # 标题
    doc.add_heading("模拟面试评估报告", level=0)
    meta = (
        f"目标岗位：{ctx['job_title']}　|　面试官：{ctx['role_name']}"
        + (f"　|　报告时间：{ctx['created_at']}" if ctx["created_at"] else "")
    )
    doc.add_paragraph(meta)

    # 综合得分
    score_p = doc.add_paragraph()
    run = score_p.add_run(f"综合得分：{ctx['score']} / 100")
    run.bold = True
    run.font.size = Pt(16)

    _doc_section(doc, "一、面试总评", [ctx["summary"]])

    dim_lines = [f"{name}：{val} 分" for name, val in ctx["dimensions"].items()]
    _doc_section(doc, "二、五维能力评分", dim_lines)

    # 岗位匹配分析：等级 + 理由
    doc.add_heading("三、岗位匹配分析", level=1)
    doc.add_paragraph(f"匹配度：{ctx['match_level'] or '—'}")
    doc.add_paragraph(f"分析：{ctx['match_reason'] or '—'}")

    # 面试优点与不足
    doc.add_heading("四、面试优点与不足", level=1)
    if ctx["strengths"]:
        doc.add_paragraph("优点：")
        for item in ctx["strengths"]:
            doc.add_paragraph(f"· {item}", style="List Bullet")
    else:
        doc.add_paragraph("优点：本次面试未识别到明显突出点。")
    if ctx["gaps"]:
        doc.add_paragraph("不足：")
        for item in ctx["gaps"]:
            doc.add_paragraph(f"· {item}", style="List Bullet")
    else:
        doc.add_paragraph("不足：本次面试暂未发现明显不足。")

    if ctx["suggestions"]:
        doc.add_heading("五、改进建议", level=1)
        for item in ctx["suggestions"]:
            doc.add_paragraph(f"· {item}", style="List Bullet")

    # 表情表现分析（有表情数据才输出）
    if ctx["expr_comment"] or ctx["expr_highlights"]:
        doc.add_heading("六、表情表现分析", level=1)
        doc.add_paragraph(ctx["expr_comment"] or "—")
        if ctx["expr_highlights"]:
            for item in ctx["expr_highlights"]:
                doc.add_paragraph(f"· {item}", style="List Bullet")

    # 逐题复盘（问题 / 你的回答 / 参考答案）
    if ctx["qa_items"]:
        doc.add_heading("七、面试逐题复盘", level=1)
        for qa in ctx["qa_items"]:
            doc.add_paragraph(f"第 {qa['index']} 题　面试官提问：{_flat(qa['question'])}")
            doc.add_paragraph(f"你的回答：{_flat(qa['answer']) if qa['answer'] else '本题未作答'}")
            doc.add_paragraph(f"参考答案：{_flat(qa['ref'])}")
            doc.add_paragraph("")

    doc.add_paragraph("")
    note = doc.add_paragraph("本报告由「模拟面试 AI 助手」自动生成，供自我复盘参考。")
    note.runs[0].italic = True

    doc.save(str(path))


def _doc_section(doc, title: str, items: list[str]) -> None:
    """加一个小节标题 + 若干段落（空内容段落跳过）。"""
    doc.add_heading(title, level=1)
    for item in items:
        if str(item).strip():
            doc.add_paragraph(str(item))


# ---------- PDF 渲染（reportlab） ----------
def _render_pdf(ctx: dict, path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    font = _register_pdf_font()

    st_title = ParagraphStyle(
        "title", fontName=font, fontSize=20, leading=28,
        alignment=TA_CENTER, spaceAfter=6,
    )
    st_meta = ParagraphStyle(
        "meta", fontName=font, fontSize=10, leading=16,
        alignment=TA_CENTER, textColor=colors.HexColor("#666666"), spaceAfter=16,
    )
    st_score = ParagraphStyle(
        "score", fontName=font, fontSize=16, leading=22,
        alignment=TA_CENTER, spaceAfter=14,
    )
    st_h = ParagraphStyle(
        "h", fontName=font, fontSize=13, leading=18,
        spaceBefore=14, spaceAfter=4, textColor=colors.HexColor("#2563EB"),
    )
    st_body = ParagraphStyle(
        "body", fontName=font, fontSize=11, leading=18,
        alignment=TA_LEFT, spaceAfter=2,
    )
    st_bullet = ParagraphStyle(
        "bullet", parent=st_body, leftIndent=16, bulletIndent=4,
        bulletFontName=font, spaceAfter=2,
    )
    st_note = ParagraphStyle(
        "note", fontName=font, fontSize=9, leading=14,
        textColor=colors.HexColor("#999999"), spaceBefore=20,
    )

    def p(text: str, style) -> Paragraph:
        return Paragraph(_clean(text), style)

    def bullet(text: str) -> Paragraph:
        return Paragraph(_clean(text), st_bullet, bulletText="•")

    story = [
        p("模拟面试评估报告", st_title),
        p(
            f"目标岗位:{_clean(ctx['job_title'])}　|　面试官:{_clean(ctx['role_name'])}"
            + (f"　|　报告时间:{_clean(ctx['created_at'])}" if ctx["created_at"] else ""),
            st_meta,
        ),
        p(f"综合得分：{ctx['score']} / 100", st_score),
        p("一、面试总评", st_h),
        p(ctx["summary"] or "—", st_body),
        p("二、五维能力评分", st_h),
    ]
    for name, val in ctx["dimensions"].items():
        story.append(p(f"{name}：{val} 分", st_body))

    story.append(p("三、岗位匹配分析", st_h))
    story.append(p(f"匹配度：{_clean(ctx['match_level'] or '—')}", st_body))
    story.append(p(f"分析:{_clean(ctx['match_reason'] or '—')}", st_body))

    # 面试优点与不足
    story.append(p("四、面试优点与不足", st_h))
    if ctx["strengths"]:
        story.append(p("优点：", st_body))
        for item in ctx["strengths"]:
            story.append(bullet(item))
    else:
        story.append(p("优点：本次面试未识别到明显突出点。", st_body))
    if ctx["gaps"]:
        story.append(p("不足：", st_body))
        for item in ctx["gaps"]:
            story.append(bullet(item))
    else:
        story.append(p("不足：本次面试暂未发现明显不足。", st_body))

    if ctx["suggestions"]:
        story.append(p("五、改进建议", st_h))
        for item in ctx["suggestions"]:
            story.append(bullet(item))

    if ctx["expr_comment"] or ctx["expr_highlights"]:
        story.append(p("六、表情表现分析", st_h))
        story.append(p(_clean(ctx["expr_comment"] or "—"), st_body))
        if ctx["expr_highlights"]:
            for item in ctx["expr_highlights"]:
                story.append(bullet(item))

    # 逐题复盘（问题 / 你的回答 / 参考答案）
    if ctx["qa_items"]:
        story.append(p("七、面试逐题复盘", st_h))
        for qa in ctx["qa_items"]:
            story.append(p(f"第 {qa['index']} 题　面试官提问：{_flat(qa['question'])}", st_body))
            story.append(
                p(
                    f"你的回答：{_flat(qa['answer']) if qa['answer'] else '本题未作答'}",
                    st_body,
                )
            )
            story.append(p(f"参考答案：{_flat(qa['ref'])}", st_body))
            story.append(Spacer(1, 6))

    story.append(Spacer(1, 16))
    story.append(p("本报告由「模拟面试 AI 助手」自动生成，供自我复盘参考。", st_note))

    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title="模拟面试评估报告", author="模拟面试 AI 助手",
    )
    doc.build(story)


def _register_pdf_font() -> str:
    """注册一个支持中文的 PDF 字体。

    优先 Windows 系统 TTF（嵌入后可被 PDF 阅读器正常检索文本），
    找不到时回退 reportlab 内置 STSong-Light CID 字体。
    """
    import os

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont

    font_dir = "C:/Windows/Fonts"
    if os.path.isdir(font_dir):
        for filename, sub in _FONT_CANDIDATES:
            fp = os.path.join(font_dir, filename)
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("CNFont", fp, subfontIndex=sub))
                    return "CNFont"
                except Exception as exc:
                    logger.warning("注册字体 %s 失败，回退 CID 字体：%s", filename, exc)

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception as exc:  # 理论不可达，兜底防御
        logger.exception("PDF 中文字体注册失败：%s", exc)
        raise


def _clean(text: str) -> str:
    """把任意文本转成 reportlab 可安全渲染的段落内容。

    转义 & < > 并把换行转成 <br/>（reportlab Paragraph 不解析裸换行）。
    """
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )

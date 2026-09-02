"""简历解析：从 PDF / DOCX / 纯文本中抽取文本内容。

支持：
- .pdf → pypdf 逐页抽取
- .docx → python-docx 抽取段落 + 表格
- .txt → 直接读取
其他格式抛出 ValueError。
"""
from pathlib import Path


def extract_text(file_path: str | Path, *, max_chars: int = 12000) -> str:
    """抽取文本并截断，避免超出模型上下文。"""
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _extract_pdf(path)
    elif suffix == ".docx":
        text = _extract_docx(path)
    elif suffix in (".txt", ".md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"不支持的简历格式：{suffix}（仅支持 pdf/docx/txt）")
    return text[:max_chars]


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts)


def _extract_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    lines: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            lines.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                lines.append(" | ".join(cells))
    return "\n".join(lines)

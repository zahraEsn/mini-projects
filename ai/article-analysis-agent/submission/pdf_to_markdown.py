"""
pdf_to_markdown.py — تبدیل PDF به Markdown

⚠️  این فایل را تغییر ندهید — فقط از آن استفاده کنید.
این فایل با PyMuPDF (fitz) متن هر PDF را استخراج و به Markdown ساده تبدیل می‌کند.

استفاده:

    from pdf_to_markdown import convert_folder

    articles = convert_folder("input_pdfs/")
    # articles: list[ArticleMarkdown]
    for a in articles:
        print(a.filename, len(a.markdown))
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class ArticleMarkdown:
    filename: str       # نام فایل PDF (بدون پسوند)
    source_path: str    # مسیر کامل فایل PDF
    markdown: str        # محتوای Markdown استخراج‌شده
    page_count: int


def convert_pdf(pdf_path: str | Path) -> ArticleMarkdown:
    """تبدیل یک فایل PDF به Markdown."""
    pdf_path = Path(pdf_path)
    doc = fitz.open(str(pdf_path))

    parts = [f"# {pdf_path.stem}\n"]
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if text:
            parts.append(f"\n<!-- صفحه {page_num + 1} -->\n\n{text}")

    page_count = len(doc)
    doc.close()

    return ArticleMarkdown(
        filename=pdf_path.stem,
        source_path=str(pdf_path),
        markdown="\n".join(parts),
        page_count=page_count,
    )


def convert_folder(folder_path: str | Path, pattern: str = "*.pdf") -> list[ArticleMarkdown]:
    """
    تبدیل همه فایل‌های PDF یک فولدر به Markdown.

    Parameters:
        folder_path: مسیر فولدر شامل PDF ها
        pattern: الگوی نام فایل (پیش‌فرض: *.pdf)

    Returns:
        لیستی از ArticleMarkdown — یکی برای هر PDF
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"فولدر پیدا نشد: {folder}")

    pdf_files = sorted(folder.glob(pattern))
    if not pdf_files:
        return []

    return [convert_pdf(p) for p in pdf_files]

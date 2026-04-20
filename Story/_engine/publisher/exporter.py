"""출판 파이프라인 — TXT / PDF / EPUB 내보내기 (03_완성본/)"""
import json
from datetime import datetime
from rich.console import Console
from _engine.manager.story_manager import get_all_chapters, get_status
from _engine.paths import TXT_DIR, PDF_DIR, EPUB_DIR

console = Console()


# ── TXT 내보내기 ──────────────────────────────────────────────
def export_txt(chapters: list[dict] | None = None, filename: str | None = None) -> Path:
    """전체 소설을 하나의 TXT 파일로 내보내기"""
    if chapters is None:
        chapters = get_all_chapters()
    if not chapters:
        raise ValueError("내보낼 챕터가 없습니다.")

    
    TXT_DIR.mkdir(parents=True, exist_ok=True)

    title = chapters[0].get("outline", {}).get("arc", "소설")
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out_name = filename or f"novel_full_{ts}.txt"
    out_path = TXT_DIR / out_name

    with open(out_path, "w", encoding="utf-8") as f:
        for ch in chapters:
            f.write(ch["content"])
            f.write("\n\n" + "─" * 40 + "\n\n")

    console.print(f"[bold green]✅ TXT 내보내기 완료: {out_path}[/bold green]")
    return out_path


# ── PDF 내보내기 ──────────────────────────────────────────────
def export_pdf(chapters: list[dict] | None = None, filename: str | None = None) -> Path:
    """전체 소설을 PDF로 내보내기"""
    try:
        from fpdf import FPDF
    except ImportError:
        raise ImportError("PDF 내보내기를 위해 'pip install fpdf2' 를 실행하세요.")

    if chapters is None:
        chapters = get_all_chapters()
    if not chapters:
        raise ValueError("내보낼 챕터가 없습니다.")

    
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = PDF_DIR / (filename or f"novel_{ts}.pdf")

    # 한글 폰트 설정 (시스템에 맞춰 경로 조정)
    FONT_CANDIDATES = [
        "C:/Windows/Fonts/malgun.ttf",       # 맑은 고딕 (Windows)
        "C:/Windows/Fonts/NanumGothic.ttf",  # 나눔고딕
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Linux
    ]

    class KoreanPDF(FPDF):
        def header(self):
            pass

        def footer(self):
            self.set_y(-15)
            self.set_font("Korean", size=9)
            self.cell(0, 10, f"{self.page_no()}", align="C")

    pdf = KoreanPDF()

    # 폰트 로드
    font_loaded = False
    for font_path in FONT_CANDIDATES:
        if Path(font_path).exists():
            pdf.add_font("Korean", "", font_path, uni=True)
            pdf.add_font("Korean", "B", font_path, uni=True)
            font_loaded = True
            break

    if not font_loaded:
        console.print("[yellow]⚠️  한글 폰트를 찾지 못했습니다. 기본 폰트 사용 (한글 깨짐 가능)[/yellow]")
        pdf.add_font = lambda *a, **k: None

    pdf.set_auto_page_break(auto=True, margin=20)

    for ch in chapters:
        pdf.add_page()
        pdf.set_font("Korean", "B", 14)
        pdf.cell(0, 12, f"{ch['chapter']}화. {ch['title']}", ln=True, align="C")
        pdf.ln(6)
        pdf.set_font("Korean", size=11)

        # 본문을 줄 단위로 추가
        for line in ch["content"].split("\n"):
            line = line.strip()
            if not line:
                pdf.ln(4)
                continue
            pdf.multi_cell(0, 7, line)

        pdf.ln(10)

    pdf.output(str(out_path))
    console.print(f"[bold green]✅ PDF 내보내기 완료: {out_path}[/bold green]")
    return out_path


# ── EPUB 내보내기 ─────────────────────────────────────────────
def export_epub(chapters: list[dict] | None = None, filename: str | None = None, novel_title: str = "판타지 소설") -> Path:
    """전체 소설을 EPUB으로 내보내기"""
    try:
        from ebooklib import epub
    except ImportError:
        raise ImportError("EPUB 내보내기를 위해 'pip install ebooklib' 를 실행하세요.")

    if chapters is None:
        chapters = get_all_chapters()
    if not chapters:
        raise ValueError("내보낼 챕터가 없습니다.")

    
    EPUB_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = EPUB_DIR / (filename or f"novel_{ts}.epub")

    book = epub.EpubBook()
    book.set_identifier(f"fantasy-novel-{ts}")
    book.set_title(novel_title)
    book.set_language("ko")
    book.add_author("주디AI스튜디오")

    spine = ["nav"]
    toc = []

    for ch in chapters:
        content_html = "<br/>\n".join(
            f"<p>{line}</p>" if line.strip() else "<br/>"
            for line in ch["content"].split("\n")
        )
        chapter_html = f"""<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{ch['chapter']}화. {ch['title']}</title></head>
<body>
<h2>{ch['chapter']}화. {ch['title']}</h2>
{content_html}
</body>
</html>"""

        epub_ch = epub.EpubHtml(
            title=f"{ch['chapter']}화. {ch['title']}",
            file_name=f"chapter_{ch['chapter']:03d}.xhtml",
            lang="ko",
        )
        epub_ch.content = chapter_html
        book.add_item(epub_ch)
        spine.append(epub_ch)
        toc.append(epub.Link(epub_ch.file_name, f"{ch['chapter']}화. {ch['title']}", f"ch{ch['chapter']}"))

    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(str(out_path), book)
    console.print(f"[bold green]✅ EPUB 내보내기 완료: {out_path}[/bold green]")
    return out_path


def export_all(novel_title: str = "판타지 소설"):
    """TXT + PDF + EPUB 모두 한 번에 내보내기"""
    chapters = get_all_chapters()
    console.print(f"\n[bold]📦 전체 내보내기 시작 ({len(chapters)}화)[/bold]")
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    export_txt(chapters, f"novel_full_{ts}.txt")
    export_pdf(chapters, f"novel_{ts}.pdf")
    export_epub(chapters, f"novel_{ts}.epub", novel_title)
    console.print("\n[bold green]🎉 모든 형식 내보내기 완료![/bold green]")

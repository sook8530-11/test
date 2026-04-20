"""연재 관리 모듈 — 챕터 현황, 통계, 연속성 체크"""
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from _engine.paths import CHAPTER_DIR, DRAFT_DIR, chapter_json_path, draft_path

console = Console()


def get_all_chapters() -> list[dict]:
    """저장된 모든 챕터 목록 반환 (정렬)"""
    if not CHAPTER_DIR.exists():
        return []
    files = sorted(CHAPTER_DIR.glob("chapter_*.json"))
    chapters = []
    for f in files:
        with open(f, encoding="utf-8") as fp:
            chapters.append(json.load(fp))
    return chapters


def get_status() -> dict:
    """현재 연재 현황 반환"""
    chapters = get_all_chapters()
    if not chapters:
        return {"total": 0, "last_chapter": 0, "total_words": 0, "chapters": []}

    total_words = sum(c.get("word_count", 0) for c in chapters)
    last = chapters[-1]

    return {
        "total": len(chapters),
        "last_chapter": last["chapter"],
        "last_title": last["title"],
        "last_created": last.get("created_at", ""),
        "total_words": total_words,
        "avg_words": total_words // len(chapters),
        "chapters": [
            {
                "chapter": c["chapter"],
                "title": c["title"],
                "word_count": c.get("word_count", 0),
                "created_at": c.get("created_at", ""),
            }
            for c in chapters
        ],
    }


def print_status():
    """연재 현황을 테이블로 출력"""
    status = get_status()
    if status["total"] == 0:
        console.print("[yellow]아직 작성된 챕터가 없습니다.[/yellow]")
        return

    console.print(f"\n[bold]📚 연재 현황[/bold]")
    console.print(f"  완성 화수: [cyan]{status['total']}화[/cyan]")
    console.print(f"  마지막 화: [cyan]{status['last_chapter']}화 — {status['last_title']}[/cyan]")
    console.print(f"  총 글자 수: [cyan]{status['total_words']:,}자[/cyan]")
    console.print(f"  평균 글자 수: [cyan]{status['avg_words']:,}자/화[/cyan]\n")

    table = Table(title="챕터 목록")
    table.add_column("화수", style="bold", width=6)
    table.add_column("제목", width=30)
    table.add_column("글자수", justify="right", width=10)
    table.add_column("작성일", width=20)

    for c in status["chapters"]:
        created = c["created_at"][:10] if c["created_at"] else "-"
        table.add_row(
            f"{c['chapter']}화",
            c["title"],
            f"{c['word_count']:,}",
            created,
        )
    console.print(table)


def get_chapter(chapter_num: int) -> dict:
    """특정 챕터 데이터 반환"""
    path = chapter_json_path(chapter_num)
    if not path.exists():
        raise FileNotFoundError(f"{chapter_num}화 파일이 없습니다.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_next_chapter_num() -> int:
    """다음에 작성해야 할 챕터 번호"""
    chapters = get_all_chapters()
    if not chapters:
        return 1
    return chapters[-1]["chapter"] + 1


def delete_chapter(chapter_num: int):
    """챕터 삭제 (재작성 시 사용)"""
    json_p = chapter_json_path(chapter_num)
    if json_p.exists():
        json_p.unlink()
        console.print(f"[yellow]{chapter_num}화 JSON 삭제됨[/yellow]")
    # 02_AI가_쓰는_것/ 에서도 같은 화수의 TXT 삭제
    for p in DRAFT_DIR.glob(f"{chapter_num:03d}화_*.txt"):
        p.unlink()
        console.print(f"[yellow]{p.name} 삭제됨[/yellow]")

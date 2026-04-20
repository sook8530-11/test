"""
판타지 소설 자동화 시스템 — 메인 CLI
사용법: python main.py --help
"""
import sys
import io

# Windows 터미널 UTF-8 강제 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

app = typer.Typer(
    name="fantasy-novel",
    help="판타지 소설 자동화 시스템",
    add_completion=False,
)
world_app = typer.Typer(help="세계관 관련 명령")
char_app = typer.Typer(help="캐릭터 관련 명령")
plot_app = typer.Typer(help="플롯 관련 명령")
chapter_app = typer.Typer(help="챕터 작성 명령")
publish_app = typer.Typer(help="출판 내보내기 명령")
schedule_app = typer.Typer(help="자동 스케줄 명령")

app.add_typer(world_app, name="world")
app.add_typer(char_app, name="character")
app.add_typer(plot_app, name="plot")
app.add_typer(chapter_app, name="chapter")
app.add_typer(publish_app, name="publish")
app.add_typer(schedule_app, name="schedule")
my_app = typer.Typer(help="내 세계관 직접 입력 명령 (신규)")
app.add_typer(my_app, name="my")

console = Console()


# ── 세계관 ────────────────────────────────────────────────────
@world_app.command("build")
def world_build(hint: str = typer.Option("", "--hint", "-h", help="추가 설정 힌트")):
    """세계관을 자동 생성합니다"""
    from _engine.generator.world_builder import build_world
    world = build_world(hint)
    console.print(f"\n[bold] {world['world_name']}[/bold]")
    console.print(world["overview"])


@world_app.command("show")
def world_show():
    """저장된 세계관을 출력합니다"""
    from _engine.generator.world_builder import load_world
    import json
    world = load_world()
    console.print(Panel(
        f"[bold]{world['world_name']}[/bold]\n\n{world['overview']}\n\n"
        f"[cyan]핵심 갈등:[/cyan] {world['central_conflict']}",
        title=" 세계관",
    ))


# ── 캐릭터 ───────────────────────────────────────────────────
@char_app.command("create")
def char_create(
    main: int = typer.Option(3, "--main", "-m", help="주인공 수"),
    sub: int = typer.Option(4, "--sub", "-s", help="조연 수"),
):
    """캐릭터를 자동 생성합니다"""
    from _engine.generator.character_creator import create_characters
    chars = create_characters(main, sub)
    console.print(f"\n[bold]주인공 {len(chars['main_characters'])}명, 조연 {len(chars['sub_characters'])}명 생성 완료[/bold]")
    for c in chars["main_characters"]:
        console.print(f"  ✦ [cyan]{c['name']}[/cyan] — {c['role']}: {c['personality'][:50]}...")


@char_app.command("show")
def char_show():
    """저장된 캐릭터 목록을 출력합니다"""
    from _engine.generator.character_creator import load_characters
    chars = load_characters()
    console.print("\n[bold] 주인공[/bold]")
    for c in chars["main_characters"]:
        console.print(f"  [cyan]{c['name']}[/cyan] ({c['age']}세) — {c['motivation']}")
    console.print("\n[bold] 조연[/bold]")
    for c in chars["sub_characters"]:
        console.print(f"  {c['name']} — {c['role']}")


# ── 플롯 ─────────────────────────────────────────────────────
@plot_app.command("generate")
def plot_generate():
    """전체 플롯을 자동 생성합니다"""
    from _engine.generator.plot_generator import generate_plot
    plot = generate_plot()
    console.print(f"\n[bold] {plot['title']}[/bold]")
    console.print(f"[dim]{plot['logline']}[/dim]")
    console.print(f"\n아크 수: {len(plot['arcs'])} | 챕터 수: {len(plot['chapter_outlines'])}")


@plot_app.command("extend")
def plot_extend(chapter: int = typer.Argument(..., help="아웃라인을 생성할 화수")):
    """특정 화의 아웃라인이 없을 때 자동으로 생성합니다"""
    from _engine.generator.plot_generator import auto_extend_outline
    outline = auto_extend_outline(chapter)
    console.print(f"\n[bold]{chapter}화: {outline['title']}[/bold]")
    console.print(outline["summary"])


@plot_app.command("show")
def plot_show(chapter: int = typer.Option(0, "--chapter", "-c", help="특정 챕터 아웃라인 보기")):
    """플롯 정보를 출력합니다"""
    from _engine.generator.plot_generator import load_plot, get_chapter_outline
    if chapter:
        outline = get_chapter_outline(chapter)
        console.print(Panel(
            f"[bold]{outline['title']}[/bold]\n\n"
            f"{outline['summary']}\n\n"
            f"[cyan]핵심 장면:[/cyan] {outline['key_scene']}\n"
            f"[cyan]복선:[/cyan] {outline['ending_hook']}",
            title=f" {chapter}화 아웃라인",
        ))
    else:
        plot = load_plot()
        console.print(f"\n[bold]{plot['title']}[/bold]")
        console.print(f"[dim]{plot['synopsis'][:200]}...[/dim]\n")
        for arc in plot["arcs"]:
            console.print(f"  [cyan]Arc {arc['arc_number']}[/cyan]: {arc['arc_name']} ({arc['chapters']}화)")


# ── 챕터 작성 ────────────────────────────────────────────────
@chapter_app.command("write")
def chapter_write(
    num: int = typer.Option(0, "--num", "-n", help="작성할 화수 (0=다음 화)"),
):
    """챕터를 자동 작성합니다"""
    from _engine.generator.chapter_writer import write_chapter
    from _engine.manager.story_manager import get_next_chapter_num
    chapter_num = num if num > 0 else get_next_chapter_num()
    write_chapter(chapter_num)


@chapter_app.command("batch")
def chapter_batch(
    start: int = typer.Argument(..., help="시작 화수"),
    end: int = typer.Argument(..., help="종료 화수"),
):
    """여러 챕터를 연속으로 작성합니다 (예: chapter batch 1 10)"""
    from _engine.generator.chapter_writer import write_chapters_range
    write_chapters_range(start, end)


@chapter_app.command("show")
def chapter_show(num: int = typer.Argument(..., help="볼 화수")):
    """특정 챕터 내용을 출력합니다"""
    from _engine.manager.story_manager import get_chapter
    ch = get_chapter(num)
    console.print(Panel(ch["content"][:2000] + ("..." if len(ch["content"]) > 2000 else ""),
                        title=f" {num}화. {ch['title']}"))


@chapter_app.command("rewrite")
def chapter_rewrite(num: int = typer.Argument(..., help="재작성할 화수")):
    """특정 챕터를 삭제하고 재작성합니다"""
    from _engine.manager.story_manager import delete_chapter
    from _engine.generator.chapter_writer import write_chapter
    delete_chapter(num)
    write_chapter(num)


# ── 현황 ─────────────────────────────────────────────────────
@app.command("status")
def status():
    """현재 연재 현황을 확인합니다"""
    from _engine.manager.story_manager import print_status
    print_status()


# ── 출판 ─────────────────────────────────────────────────────
@publish_app.command("txt")
def pub_txt():
    """전체 소설을 TXT로 내보냅니다"""
    from _engine.publisher.exporter import export_txt
    export_txt()


@publish_app.command("pdf")
def pub_pdf():
    """전체 소설을 PDF로 내보냅니다"""
    from _engine.publisher.exporter import export_pdf
    export_pdf()


@publish_app.command("epub")
def pub_epub(title: str = typer.Option("판타지 소설", "--title", "-t")):
    """전체 소설을 EPUB으로 내보냅니다"""
    from _engine.publisher.exporter import export_epub
    export_epub(novel_title=title)


@publish_app.command("all")
def pub_all(title: str = typer.Option("판타지 소설", "--title", "-t")):
    """TXT + PDF + EPUB 모두 내보냅니다"""
    from _engine.publisher.exporter import export_all
    export_all(novel_title=title)


# ── 스케줄러 ─────────────────────────────────────────────────
@schedule_app.command("daily")
def schedule_daily(time: str = typer.Option("09:00", "--time", "-t", help="매일 실행 시간 HH:MM")):
    """매일 지정된 시간에 다음 화를 자동 생성합니다"""
    from _engine.scheduler.auto_writer import run_scheduler
    run_scheduler(time)


@schedule_app.command("interval")
def schedule_interval(minutes: int = typer.Option(60, "--minutes", "-m", help="실행 간격(분)")):
    """지정된 분 간격으로 다음 화를 자동 생성합니다 (테스트용)"""
    from _engine.scheduler.auto_writer import run_interval_scheduler
    run_interval_scheduler(minutes)


@schedule_app.command("once")
def schedule_once():
    """지금 당장 다음 화를 자동 생성합니다"""
    from _engine.scheduler.auto_writer import auto_write_next
    auto_write_next()


# ── 전체 셋업 ─────────────────────────────────────────────────
@app.command("setup")
def setup(hint: str = typer.Option("", "--hint", "-h", help="세계관 힌트")):
    """세계관 → 캐릭터 → 플롯을 한 번에 자동 생성합니다 (처음 시작할 때)"""
    console.print(Panel(
        "  판타지 소설 자동화 시스템\n세계관 → 캐릭터 → 플롯 순서로 생성합니다",
        title="SETUP",
        style="bold cyan",
    ))

    from _engine.generator.world_builder import build_world
    from _engine.generator.character_creator import create_characters
    from _engine.generator.plot_generator import generate_plot

    console.print("\n[bold cyan]STEP 1/3 — 세계관 생성[/bold cyan]")
    world = build_world(hint)

    console.print("\n[bold cyan]STEP 2/3 — 캐릭터 생성[/bold cyan]")
    chars = create_characters()

    console.print("\n[bold cyan]STEP 3/3 — 플롯 생성[/bold cyan]")
    plot = generate_plot()

    console.print(Panel(
        f"[bold green]✅ 셋업 완료![/bold green]\n\n"
        f"세계관: {world['world_name']}\n"
        f"캐릭터: 주인공 {len(chars['main_characters'])}명, 조연 {len(chars['sub_characters'])}명\n"
        f"플롯: {len(plot['chapter_outlines'])}화 아웃라인 생성\n\n"
        f"다음 명령으로 첫 화를 작성하세요:\n"
        f"  [cyan]python main.py chapter write[/cyan]",
        title=" 셋업 완료",
    ))


# ── 내 세계관 직접 입력 ───────────────────────────────────────
@my_app.command("open")
def my_open():
    """01_내가_쓰는_것/ 폴더의 3개 파일을 바로 열어줍니다"""
    import os
    from _engine.paths import WORLD_JSON, CHAR_JSON, PLOT_JSON
    files = {"세계관": WORLD_JSON, "캐릭터": CHAR_JSON, "플롯": PLOT_JSON}
    console.print(Panel(
        "[bold]다음 3개 파일을 채워주세요.[/bold]\n\n"
        "작성 후 바로 chapter write 를 실행할 수 있습니다.",
        title="내 세계관 입력",
    ))
    for label, path in files.items():
        console.print(f"  [{label}] {path}")
        try:
            os.startfile(str(path))
        except Exception:
            pass


@my_app.command("status")
def my_status():
    """현재 입력된 세계관/캐릭터/플롯 요약을 출력합니다"""
    import json
    from _engine.paths import WORLD_JSON, CHAR_JSON, PLOT_JSON

    if WORLD_JSON.exists():
        with open(WORLD_JSON, encoding="utf-8") as f:
            w = json.load(f)
        console.print(f"[bold cyan]세계관:[/bold cyan] {w.get('world_name','?')} — {w.get('overview','')[:80]}...")
    else:
        console.print("[yellow]세계관: 미입력 (01_내가_쓰는_것/세계관.json)[/yellow]")

    if CHAR_JSON.exists():
        with open(CHAR_JSON, encoding="utf-8") as f:
            c = json.load(f)
        mains = [x["name"] for x in c.get("main_characters", [])]
        console.print(f"[bold cyan]주인공:[/bold cyan] {', '.join(mains)}")
    else:
        console.print("[yellow]캐릭터: 미입력 (01_내가_쓰는_것/캐릭터.json)[/yellow]")

    if PLOT_JSON.exists():
        with open(PLOT_JSON, encoding="utf-8") as f:
            p = json.load(f)
        n_outlines = len(p.get("chapter_outlines", []))
        console.print(f"[bold cyan]플롯:[/bold cyan] {p.get('title','?')} ({n_outlines}화 아웃라인)")
    else:
        console.print("[yellow]플롯: 미입력 (01_내가_쓰는_것/플롯.json)[/yellow]")


if __name__ == "__main__":
    app()

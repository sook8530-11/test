"""자동 연재 스케줄러 — 정해진 시간에 다음 화를 자동 생성"""
import schedule
import time
from datetime import datetime
from rich.console import Console
from _engine.manager.story_manager import get_next_chapter_num, get_status
from _engine.generator.chapter_writer import write_chapter
from _engine.paths import SCHED_LOG

console = Console()


def _log(message: str):
    log_path = SCHED_LOG
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")
    console.print(f"[dim][{ts}][/dim] {message}")


def auto_write_next():
    """다음 화를 자동으로 작성"""
    try:
        status = get_status()
        next_num = get_next_chapter_num()
        _log(f"🤖 자동 생성 시작 — {next_num}화")
        write_chapter(next_num)
        _log(f"✅ {next_num}화 자동 생성 완료")
    except Exception as e:
        _log(f"❌ 자동 생성 실패: {e}")


def run_scheduler(cron_time: str = "09:00"):
    """
    매일 지정된 시간에 다음 화 자동 생성.
    cron_time 형식: "HH:MM" (예: "09:00")
    """
    console.print(f"\n[bold cyan]⏰ 스케줄러 시작 — 매일 {cron_time}에 자동 생성[/bold cyan]")
    console.print("[dim]종료하려면 Ctrl+C를 누르세요[/dim]\n")

    schedule.every().day.at(cron_time).do(auto_write_next)
    _log(f"스케줄러 등록: 매일 {cron_time}")

    while True:
        schedule.run_pending()
        time.sleep(60)


def run_interval_scheduler(minutes: int = 60):
    """
    지정된 분 간격으로 다음 화 자동 생성 (테스트용).
    """
    console.print(f"\n[bold cyan]⏰ 인터벌 스케줄러 — {minutes}분마다 자동 생성[/bold cyan]")
    console.print("[dim]종료하려면 Ctrl+C를 누르세요[/dim]\n")

    schedule.every(minutes).minutes.do(auto_write_next)
    _log(f"인터벌 스케줄러 등록: {minutes}분마다")

    while True:
        schedule.run_pending()
        time.sleep(30)

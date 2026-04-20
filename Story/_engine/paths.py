"""
중앙 경로 모듈 — 모든 파일 경로를 한 곳에서 관리
디렉토리 구조가 바뀌면 이 파일만 수정하면 됩니다.
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent  # 프로젝트 루트

# ── 01 사용자 입력 영역 ───────────────────────────────────────
USER_DIR   = ROOT / "01_내가_쓰는_것"
WORLD_JSON = USER_DIR / "세계관.json"
CHAR_JSON  = USER_DIR / "캐릭터.json"
PLOT_JSON  = USER_DIR / "플롯.json"

# ── 02 AI 생성 원고 ───────────────────────────────────────────
DRAFT_DIR  = ROOT / "02_AI가_쓰는_것"

# ── 03 완성본 출판 ────────────────────────────────────────────
OUTPUT_DIR = ROOT / "03_완성본"
PDF_DIR    = OUTPUT_DIR / "pdf"
EPUB_DIR   = OUTPUT_DIR / "epub"
TXT_DIR    = OUTPUT_DIR / "txt"

# ── _추적 자동 관리 ───────────────────────────────────────────
TRACK_DIR   = ROOT / "_추적"
CHAPTER_DIR = TRACK_DIR / "챕터_데이터"
CHAR_STATE  = TRACK_DIR / "캐릭터_상태.json"
LORE_JSON   = TRACK_DIR / "로어_누적.json"
SCHED_LOG   = TRACK_DIR / "scheduler.log"

# ── 설정 ─────────────────────────────────────────────────────
STORY_CONFIG = ROOT / "소설설정.json"


def ensure_dirs():
    """필요한 디렉토리를 모두 생성"""
    for d in [USER_DIR, DRAFT_DIR, PDF_DIR, EPUB_DIR, TXT_DIR, CHAPTER_DIR, TRACK_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def draft_path(chapter_num: int, title: str = "") -> Path:
    """02_AI가_쓰는_것/ 안의 챕터 TXT 경로"""
    safe_title = title.replace("/", "_").replace("\\", "_")[:20]
    name = f"{chapter_num:03d}화_{safe_title}.txt" if safe_title else f"{chapter_num:03d}화.txt"
    return DRAFT_DIR / name


def chapter_json_path(chapter_num: int) -> Path:
    """_추적/챕터_데이터/ 안의 챕터 JSON 경로"""
    return CHAPTER_DIR / f"chapter_{chapter_num:03d}.json"

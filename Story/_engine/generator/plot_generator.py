"""플롯 자동 생성 모듈"""
import json
from rich.console import Console
from _engine.claude_client import call_claude, call_claude_fast, load_story_config
from _engine.generator.world_builder import load_world
from _engine.generator.character_creator import load_characters, get_character_summary
from _engine.paths import PLOT_JSON, USER_DIR

console = Console()


SYSTEM_PROMPT = """당신은 판타지 소설 전문 플롯 설계자입니다.
서사 구조가 탄탄하고 독자를 끌어당기는 플롯을 설계합니다.
결과는 반드시 유효한 JSON 형식으로만 출력하세요. 다른 텍스트는 포함하지 마세요."""


def generate_plot() -> dict:
    """전체 플롯(아크 구조 + 챕터별 요약) 생성"""
    config = load_story_config()
    world = load_world()
    char_summary = get_character_summary()
    total_chapters = config["target_chapters"]

    prompt = f"""다음 소설의 전체 플롯을 설계해주세요.

제목: {config['title']}
총 챕터 수: {total_chapters}화
세계관: {world['world_name']} — {world['overview']}
핵심 갈등: {world['central_conflict']}
등장인물:
{char_summary}
주요 테마: {', '.join(config['themes'])}

다음 JSON 구조로 출력하세요:
{{
  "title": "소설 제목",
  "logline": "한 줄 요약",
  "synopsis": "전체 줄거리 요약 (500자 이상)",
  "arcs": [
    {{
      "arc_number": 1,
      "arc_name": "아크 이름",
      "chapters": "1-15",
      "description": "이 아크에서 일어나는 일",
      "key_events": ["주요 사건 목록"],
      "character_development": "캐릭터 성장 포인트"
    }}
  ],
  "chapter_outlines": [
    {{
      "chapter": 1,
      "title": "챕터 제목",
      "arc": "아크 번호",
      "summary": "이번 화 내용 요약 (100자 이상)",
      "key_scene": "핵심 장면",
      "emotional_tone": "감정적 톤",
      "ending_hook": "다음 화로 넘어가는 복선"
    }}
  ],
  "climax_chapter": 클라이맥스_챕터_번호,
  "resolution": "결말 방향"
}}

chapter_outlines는 총 {total_chapters}개 챕터 전부 포함해야 합니다."""

    console.print(f"[bold cyan]플롯 생성 중... (총 {total_chapters}화)[/bold cyan]")
    raw = call_claude(SYSTEM_PROMPT, prompt, max_tokens=8000)

    plot = json.loads(raw.strip())

    USER_DIR.mkdir(parents=True, exist_ok=True)
    with open(PLOT_JSON, "w", encoding="utf-8") as f:
        json.dump(plot, f, ensure_ascii=False, indent=2)

    console.print(f"[bold green]플롯 저장 완료: {PLOT_JSON}[/bold green]")
    return plot


def load_plot() -> dict:
    if not PLOT_JSON.exists():
        raise FileNotFoundError(
            f"플롯 파일이 없습니다: {PLOT_JSON}\n"
            "01_내가_쓰는_것/플롯.json 을 작성하세요."
        )
    with open(PLOT_JSON, encoding="utf-8") as f:
        return json.load(f)


def get_chapter_outline(chapter_num: int) -> dict:
    """특정 챕터의 아웃라인 반환"""
    plot = load_plot()
    for outline in plot.get("chapter_outlines", []):
        if outline["chapter"] == chapter_num:
            return outline
    raise ValueError(f"{chapter_num}화 아웃라인을 찾을 수 없습니다.")


def _find_arc_for_chapter(plot: dict, chapter_num: int) -> dict | None:
    """챕터 번호가 속한 아크를 반환"""
    for arc in plot.get("arcs", []):
        chapters_range = arc.get("chapters", "")
        try:
            start, end = map(int, chapters_range.split("-"))
            if start <= chapter_num <= end:
                return arc
        except Exception:
            pass
    # 아크 범위 밖이면 마지막 아크 반환
    arcs = plot.get("arcs", [])
    return arcs[-1] if arcs else None


def auto_extend_outline(chapter_num: int) -> dict:
    """
    Fix 2: 아웃라인 자동 확장
    plot.json에 해당 화 아웃라인이 없을 때 아크 정보를 바탕으로 자동 생성 후 저장.
    스케줄러가 아웃라인 부재로 멈추는 문제 해결.
    """
    plot = load_plot()

    # 이미 있으면 그냥 반환
    for o in plot.get("chapter_outlines", []):
        if o["chapter"] == chapter_num:
            return o

    arc = _find_arc_for_chapter(plot, chapter_num)
    world = load_world()
    char_summary = get_character_summary()

    # 직전 3화 아웃라인으로 흐름 파악
    prev_outlines = [
        o for o in plot.get("chapter_outlines", [])
        if chapter_num - 4 <= o["chapter"] < chapter_num
    ]
    prev_block = "\n".join(
        f"{o['chapter']}화 — {o['title']}: {o['summary'][:80]}"
        for o in prev_outlines
    ) if prev_outlines else "없음"

    arc_block = (
        f"아크: {arc['arc_name']}\n"
        f"아크 설명: {arc['description']}\n"
        f"주요 사건: {', '.join(arc.get('key_events', []))}"
    ) if arc else "아크 정보 없음"

    prompt = f"""판타지 소설 {chapter_num}화의 아웃라인을 만들어주세요.

소설: {plot.get('title','')}
{arc_block}

이전 흐름:
{prev_block}

세계관: {world.get('world_name','')} — {world.get('central_conflict','')}
등장인물: {char_summary[:300]}

JSON만 출력:
{{
  "chapter": {chapter_num},
  "title": "제목",
  "arc": {arc.get('arc_number', 1) if arc else 1},
  "summary": "이번 화 내용 (100자 이상)",
  "key_scene": "핵심 장면",
  "emotional_tone": "감정 톤",
  "ending_hook": "다음 화 복선"
}}"""

    console.print(f"[dim]{chapter_num}화 아웃라인 자동 생성 중...[/dim]")
    raw = call_claude_fast(
        "판타지 소설 플롯 설계자. JSON만 출력.",
        prompt,
        max_tokens=600,
    )
    new_outline = json.loads(raw.strip())

    # plot.json에 추가 저장
    plot.setdefault("chapter_outlines", []).append(new_outline)
    plot["chapter_outlines"].sort(key=lambda o: o["chapter"])
    with open(PLOT_JSON, "w", encoding="utf-8") as f:
        json.dump(plot, f, ensure_ascii=False, indent=2)

    console.print(f"[green]{chapter_num}화 아웃라인 자동 생성 완료: {new_outline['title']}[/green]")
    return new_outline

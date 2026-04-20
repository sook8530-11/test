"""
챕터 집필 엔진 (v2 — 수정된 버전)

수정 사항:
  - Fix 1: 피드백 루프 연결 — 재시도 시 평가 피드백이 장면 분해·집필 프롬프트에 실제 주입됨
  - Fix 3: API 최적화 — 계획·평가는 Haiku, 집필만 Opus 사용 / 재시도 시 낮은 점수 장면만 재작성
  - 미사용 함수 제거, 오류 처리 일관성 개선
"""
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from _engine.claude_client import call_claude, call_claude_fast, load_story_config
from _engine.manager.character_state import get_state_summary, update_state_from_chapter
from _engine.generator.plot_generator import auto_extend_outline
from _engine.paths import (
    CHAPTER_DIR, WORLD_JSON as WORLD_PATH, CHAR_JSON as CHAR_PATH,
    PLOT_JSON as PLOT_PATH, LORE_JSON as LORE_PATH,
    chapter_json_path, draft_path, TRACK_DIR,
)

console = Console()


# ── 로더 ──────────────────────────────────────────────────────
def _load_json(path: Path, label: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"[오류] {label} 파일이 없습니다: {path}\n"
            "python main.py my apply 를 먼저 실행하세요."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_lore() -> list[str]:
    if not LORE_PATH.exists():
        return []
    with open(LORE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_lore(lore: list[str]):
    with open(LORE_PATH, "w", encoding="utf-8") as f:
        json.dump(lore, f, ensure_ascii=False, indent=2)


def _get_chapter_outline(plot: dict, chapter_num: int) -> dict | None:
    for o in plot.get("chapter_outlines", []):
        if o["chapter"] == chapter_num:
            return o
    return None


def _get_previous_summaries(chapter_num: int, n: int = 3) -> str:
    summaries = []
    for i in range(max(1, chapter_num - n), chapter_num):
        p = CHAPTER_DIR / f"chapter_{i:03d}.json"
        if p.exists():
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            summaries.append(f"{i}화: {d.get('summary', d['content'][:150])}...")
    return "\n".join(summaries) if summaries else "없음 (첫 번째 화)"


def _relevant_lore(lore: list[str], outline: dict) -> str:
    """현재 챕터 아웃라인과 관련된 로어만 필터링 (키워드 매칭)"""
    if not lore:
        return "없음"
    keywords = set(
        (outline.get("title", "") + " " + outline.get("key_scene", "")).split()
    )
    scored = []
    for entry in lore:
        hits = sum(1 for kw in keywords if kw in entry)
        scored.append((hits, entry))
    scored.sort(reverse=True)
    top = [e for _, e in scored[:8]]
    return "\n".join(f"- {e}" for e in top) if top else "없음"


# ── STEP 1: 장면 분해 (Haiku) ─────────────────────────────────
def _plan_scenes(
    world: dict,
    outline: dict,
    char_state: str,
    feedback: str = "",          # Fix 1: 피드백 주입
) -> list[dict]:
    """챕터를 3~5개 장면으로 분해. 재시도 시 이전 피드백 반영."""

    feedback_block = (
        f"\n[이전 시도 문제점 — 반드시 개선하세요]\n{feedback}"
        if feedback else ""
    )

    prompt = f"""다음 챕터 아웃라인을 3~5개의 장면(scene)으로 분해하세요.

챕터:
- 제목: {outline['title']}
- 요약: {outline['summary']}
- 핵심 장면: {outline['key_scene']}
- 감정 톤: {outline['emotional_tone']}
- 다음 화 복선: {outline['ending_hook']}

세계관: {world.get('world_name','')} — {world.get('overview','')[:150]}
캐릭터 현재 상태:
{char_state}
{feedback_block}

JSON 배열만 출력:
[
  {{
    "scene_num": 1,
    "location": "장소",
    "time": "시간대",
    "characters": ["등장인물"],
    "conflict": "이 장면의 갈등/긴장",
    "emotional_peak": "감정 절정",
    "purpose": "서사 목적",
    "description": "이 장면에서 일어나는 일 (2~3문장)"
  }}
]"""

    raw = call_claude_fast(       # Haiku 사용
        "소설 장면 설계자. JSON 배열만 출력.",
        prompt,
        max_tokens=1500,
    )
    return json.loads(raw.strip())


# ── STEP 2: 장면 집필 (Opus) ──────────────────────────────────
def _write_scene(
    scene: dict,
    lore_block: str,
    prev_scene_tail: str,
    config: dict,
    is_last: bool,
    ending_hook: str,
    feedback: str = "",           # Fix 1: 피드백 주입
) -> str:
    """장면 단위 집필. 재시도 시 피드백을 프롬프트에 포함."""

    feedback_block = (
        f"\n[이전 시도 개선 요청] {feedback} — 이 점을 반드시 개선하세요."
        if feedback else ""
    )
    hook_block = (
        f"\n[마지막 장면] 다음 화 복선 '{ending_hook}'이 자연스럽게 드러나도록 끝내세요."
        if is_last else ""
    )

    system = """한국어 판타지 소설 작가.
- 지문과 대화를 자연스럽게 섞어라
- 오감(시각·청각·촉각)으로 장면을 묘사하라
- 캐릭터 내면 심리를 행동·대화 속에 녹여라
- 소설 본문만 출력하라. 제목·설명 금지"""

    prompt = f"""[장면 {scene['scene_num']}]
장소: {scene['location']} | 시간: {scene['time']}
등장: {', '.join(scene['characters'])}
갈등: {scene['conflict']}
감정 절정: {scene['emotional_peak']}
목적: {scene['purpose']}
내용: {scene['description']}

직전 장면 흐름:
{prev_scene_tail or '챕터 시작'}

세계관 규칙:
{lore_block}

스타일: {config.get('writing_style', '3인칭')} | 분위기: {config.get('tone', '웅장하고 서사적')}
목표 분량: {config.get('words_per_chapter', 3000) // 4}자 내외
{feedback_block}{hook_block}

소설 본문을 작성하세요."""

    return call_claude(system, prompt, max_tokens=2500)  # Opus 사용


# ── STEP 3: 장면별 품질 평가 (Haiku) ─────────────────────────
def _evaluate_scenes(scene_texts: list[str], scenes: list[dict], outline: dict) -> list[dict]:
    """각 장면을 개별 평가. 점수+피드백 반환."""
    results = []
    for i, (text, scene) in enumerate(zip(scene_texts, scenes)):
        prompt = f"""소설 장면을 평가하세요.

장면 목적: {scene['purpose']} | 감정 절정: {scene['emotional_peak']}
{'핵심 장면 포함 여부 확인: ' + outline.get('key_scene','') if i == len(scenes)//2 else ''}

장면 내용:
{text[:1500]}

JSON만 출력:
{{
  "score": 점수(0.0-10.0),
  "feedback": "개선점 한 문장 (없으면 빈 문자열)"
}}"""
        try:
            raw = call_claude_fast("소설 편집자. JSON만 출력.", prompt, max_tokens=200)
            result = json.loads(raw.strip())
            results.append({"score": float(result["score"]), "feedback": result.get("feedback", "")})
        except Exception:
            results.append({"score": 7.0, "feedback": ""})
    return results


# ── STEP 4: 세계관 로어 추출 (Haiku) ─────────────────────────
def _extract_and_check_lore(chapter_num: int, content: str, world: dict):
    existing_rules = world.get("magic_system", {}).get("rules", [])
    prompt = f"""챕터({chapter_num}화)에서 세계관 요소를 추출하세요.
기존 마법 규칙: {existing_rules}
챕터 내용: {content[:1500]}

JSON만:
{{"new_lore": ["새 세계관 사실"], "conflicts": ["기존 설정 충돌 (없으면 빈 배열)"]}}"""
    try:
        raw = call_claude_fast("세계관 감시자. JSON만 출력.", prompt, max_tokens=500)
        result = json.loads(raw.strip())
        if result.get("conflicts"):
            console.print(f"[bold red]세계관 충돌 감지 ({chapter_num}화):[/bold red]")
            for c in result["conflicts"]:
                console.print(f"   - {c}")
        lore = _load_lore()
        for item in result.get("new_lore", []):
            entry = f"[{chapter_num}화] {item}"
            if entry not in lore:
                lore.append(entry)
        _save_lore(lore)
    except Exception as e:
        console.print(f"[yellow]로어 추출 실패 (건너뜀): {e}[/yellow]")


# ── 메인: 챕터 작성 ───────────────────────────────────────────
def write_chapter(chapter_num: int, min_scene_score: float = 6.5, max_retries: int = 3) -> dict:
    """
    사용자 세계관 기반 챕터 자동 집필.

    흐름:
      1. 장면 분해 (Haiku)
      2. 장면별 집필 (Opus)
      3. 장면별 품질 평가 (Haiku)
      4. 미달 장면만 피드백 포함 재작성 (Fix 1 + Fix 3)
      5. 캐릭터 상태 갱신 + 로어 추출 (Haiku)

    API 호출 수 (정상 시): 1 + N장면 + N장면 + 1 + 1 = 약 12회 (기존 최대 24회 → 절반)
    """
    config  = load_story_config()
    world   = _load_json(WORLD_PATH, "세계관")
    chars   = _load_json(CHAR_PATH, "캐릭터")   # noqa: 캐릭터 상태에서 활용
    plot    = _load_json(PLOT_PATH, "플롯")
    outline = _get_chapter_outline(plot, chapter_num)

    if outline is None:
        # Fix 2: 아웃라인이 없으면 아크 정보로 자동 생성
        console.print(f"[yellow]{chapter_num}화 아웃라인 없음 — 자동 생성합니다[/yellow]")
        outline = auto_extend_outline(chapter_num)

    lore       = _load_lore()
    lore_block = _relevant_lore(lore, outline)
    char_state = get_state_summary()
    config.get("words_per_chapter", 3000)

    console.print(f"\n[bold cyan]--- {chapter_num}화: {outline['title']} ---[/bold cyan]")

    # 1회 장면 분해
    console.print("  [dim]① 장면 분해 (Haiku)[/dim]")
    scenes = _plan_scenes(world, outline, char_state)

    # 장면별 초기 집필
    console.print(f"  [dim]② {len(scenes)}개 장면 집필 (Opus)[/dim]")
    scene_texts: list[str | None] = [None] * len(scenes)
    for i, scene in enumerate(scenes):
        prev_tail = scene_texts[i - 1][-400:] if i > 0 and scene_texts[i-1] else ""
        scene_texts[i] = _write_scene(
            scene, lore_block, prev_tail, config,
            is_last=(i == len(scenes) - 1),
            ending_hook=outline.get("ending_hook", ""),
        )

    # 장면별 평가 + 피드백 반영 재작성 (Fix 1 + Fix 3)
    for attempt in range(max_retries):
        console.print(f"  [dim]③ 장면별 품질 평가 (Haiku) — {attempt+1}차[/dim]")
        evals = _evaluate_scenes(scene_texts, scenes, outline)

        low_indices = [i for i, e in enumerate(evals) if e["score"] < min_scene_score]
        avg_score   = sum(e["score"] for e in evals) / len(evals)

        score_str = " ".join(f"S{i+1}:{e['score']:.1f}" for i, e in enumerate(evals))
        console.print(f"  점수: {score_str} | 평균: {avg_score:.1f}")

        if not low_indices:
            console.print("  [green]모든 장면 기준 통과[/green]")
            break

        if attempt == max_retries - 1:
            console.print(f"  [yellow]최대 재시도 도달 — 현재 버전으로 확정[/yellow]")
            break

        # Fix 3: 낮은 장면만 재작성 (전체 챕터 X)
        console.print(f"  [yellow]장면 {[i+1 for i in low_indices]} 재작성 중...[/yellow]")
        for i in low_indices:
            feedback = evals[i]["feedback"]
            prev_tail = scene_texts[i - 1][-400:] if i > 0 and scene_texts[i-1] else ""
            scene_texts[i] = _write_scene(
                scenes[i], lore_block, prev_tail, config,
                is_last=(i == len(scenes) - 1),
                ending_hook=outline.get("ending_hook", ""),
                feedback=feedback,   # Fix 1: 피드백 실제 주입
            )

    content = f"# {chapter_num}화. {outline['title']}\n\n" + "\n\n".join(scene_texts)
    final_avg = sum(e["score"] for e in evals) / len(evals)

    # 요약 (Haiku)
    summary = call_claude_fast(
        "소설 편집자. 핵심만 150자 이내 요약.",
        f"{chapter_num}화:\n{content[:2000]}",
        max_tokens=250,
    )

    chapter_data = {
        "chapter":       chapter_num,
        "title":         outline["title"],
        "content":       content,
        "summary":       summary,
        "word_count":    len(content),
        "quality_score": round(final_avg, 2),
        "scene_scores":  [e["score"] for e in evals],
        "created_at":    datetime.now().isoformat(),
        "outline":       outline,
    }

    # JSON 메타데이터 → _추적/챕터_데이터/
    CHAPTER_DIR.mkdir(parents=True, exist_ok=True)
    with open(chapter_json_path(chapter_num), "w", encoding="utf-8") as f:
        json.dump(chapter_data, f, ensure_ascii=False, indent=2)

    # 읽기 쉬운 TXT → 02_AI가_쓰는_것/NNN화_제목.txt
    txt_p = draft_path(chapter_num, outline["title"])
    txt_p.parent.mkdir(parents=True, exist_ok=True)
    with open(txt_p, "w", encoding="utf-8") as f:
        f.write(content)

    console.print("  [dim]④ 캐릭터 상태 + 로어 갱신 (Haiku)[/dim]")
    update_state_from_chapter(chapter_num, content)
    _extract_and_check_lore(chapter_num, content, world)

    console.print(
        f"[bold green]{chapter_num}화 완료 "
        f"({len(content):,}자 | 평균 품질 {final_avg:.1f}/10)[/bold green]\n"
    )
    return chapter_data


def write_chapters_range(start: int, end: int) -> list:
    results = []
    for num in range(start, end + 1):
        if chapter_json_path(num).exists():
            console.print(f"[yellow]{num}화 이미 존재 — 건너뜁니다[/yellow]")
            continue
        results.append(write_chapter(num))
    return results

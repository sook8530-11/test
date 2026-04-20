"""동적 캐릭터 상태 추적기 — 매 화마다 감정/관계/성장을 자동 갱신 (StoryDaemon 방식)"""
import json
from rich.console import Console
from _engine.claude_client import call_claude
from _engine.paths import CHAR_STATE as STATE_PATH, CHAR_JSON as CHAR_PATH, TRACK_DIR

console = Console()


def _load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    # 최초: 캐릭터 기본 상태로 초기화
    if not CHAR_PATH.exists():
        return {}
    with open(CHAR_PATH, encoding="utf-8") as f:
        chars = json.load(f)
    state = {}
    for c in chars.get("main_characters", []):
        state[c["name"]] = {
            "chapter_last_updated": 0,
            "current_emotion": "초기 상태",
            "relationship_changes": {},
            "arc_progress": "시작",
            "open_conflicts": [],
            "known_facts": [],
        }
    return state


def _save_state(state: dict):
    TRACK_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_state_summary() -> str:
    """챕터 작성 프롬프트에 삽입할 캐릭터 현재 상태 요약"""
    state = _load_state()
    if not state:
        return "캐릭터 상태 정보 없음 (첫 번째 화)"
    lines = []
    for name, s in state.items():
        relationships = "; ".join(f"{k}: {v}" for k, v in s.get("relationship_changes", {}).items())
        conflicts = ", ".join(s.get("open_conflicts", []))
        lines.append(
            f"[{name}] 현재감정: {s['current_emotion']} | "
            f"성장단계: {s['arc_progress']} | "
            f"미해결갈등: {conflicts or '없음'} | "
            f"관계변화: {relationships or '없음'}"
        )
    return "\n".join(lines)


def update_state_from_chapter(chapter_num: int, chapter_content: str):
    """챕터 내용을 분석해 캐릭터 상태를 자동 갱신"""
    state = _load_state()
    if not state:
        return

    names = list(state.keys())
    prompt = f"""다음 소설 챕터({chapter_num}화)를 읽고 각 캐릭터의 상태 변화를 JSON으로 추출하세요.

분석할 캐릭터: {', '.join(names)}

챕터 내용:
{chapter_content[:3000]}

다음 JSON 형식으로만 출력하세요:
{{
  "캐릭터이름": {{
    "current_emotion": "현재 감정 상태 (구체적으로)",
    "relationship_changes": {{"상대방이름": "관계 변화 설명"}},
    "arc_progress": "성장 단계 (예: 각성 직전, 시련 중반, 성장 완료)",
    "new_conflicts": ["이 화에서 새로 생긴 갈등"],
    "resolved_conflicts": ["이 화에서 해결된 갈등"],
    "new_facts": ["이 화에서 알게 된 새로운 사실"]
  }}
}}

변화가 없는 캐릭터는 빈 객체 {{}}로 표시하세요."""

    try:
        raw = call_claude(
            "당신은 소설 분석가입니다. JSON만 출력하세요.",
            prompt,
            max_tokens=1500,
        )
        updates = json.loads(raw.strip())

        for name, update in updates.items():
            if name not in state or not update:
                continue
            s = state[name]
            s["chapter_last_updated"] = chapter_num
            if update.get("current_emotion"):
                s["current_emotion"] = update["current_emotion"]
            if update.get("arc_progress"):
                s["arc_progress"] = update["arc_progress"]
            if update.get("relationship_changes"):
                s["relationship_changes"].update(update["relationship_changes"])
            for c in update.get("new_conflicts", []):
                if c not in s["open_conflicts"]:
                    s["open_conflicts"].append(c)
            for c in update.get("resolved_conflicts", []):
                if c in s["open_conflicts"]:
                    s["open_conflicts"].remove(c)
            for f in update.get("new_facts", []):
                if f not in s["known_facts"]:
                    s["known_facts"].append(f)

        _save_state(state)
        console.print(f"[dim]{chapter_num}화 캐릭터 상태 갱신 완료[/dim]")
    except Exception as e:
        console.print(f"[yellow]⚠️  캐릭터 상태 갱신 실패 (건너뜀): {e}[/yellow]")

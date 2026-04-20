"""세계관 자동 생성 모듈"""
import json
from rich.console import Console
from _engine.claude_client import call_claude, load_story_config
from _engine.paths import WORLD_JSON, USER_DIR

console = Console()

SYSTEM_PROMPT = """당신은 판타지 소설 전문 세계관 설계자입니다.
작가의 설정을 바탕으로 풍부하고 일관성 있는 판타지 세계를 구축합니다.
결과는 반드시 유효한 JSON 형식으로만 출력하세요. 다른 텍스트는 포함하지 마세요."""


def build_world(theme_hint: str = "") -> dict:
    """세계관을 생성하고 01_내가_쓰는_것/세계관.json에 저장"""
    config = load_story_config()

    prompt = f"""다음 설정으로 판타지 소설의 세계관을 만들어주세요.

소설 장르: {config['genre']}
시대 배경: {config['world_setting']['era']}
마법 체계: {config['world_setting']['magic_system']}
지리적 특성: {config['world_setting']['geography']}
주요 테마: {', '.join(config['themes'])}
추가 힌트: {theme_hint if theme_hint else '없음'}

다음 JSON 구조로 출력하세요:
{{
  "world_name": "세계 이름",
  "overview": "세계관 전체 개요 (300자 이상)",
  "history": "역사적 배경 (200자 이상)",
  "geography": {{
    "continents": ["대륙 이름 목록"],
    "key_locations": [
      {{"name": "장소명", "description": "설명", "significance": "소설에서의 중요성"}}
    ]
  }},
  "magic_system": {{
    "name": "마법 체계 이름",
    "rules": ["마법 규칙 목록"],
    "power_source": "마법의 원천",
    "limitations": ["마법의 제약 조건"]
  }},
  "factions": [
    {{"name": "세력명", "description": "설명", "goal": "목표", "relationship": "다른 세력과의 관계"}}
  ],
  "culture_and_society": "문화와 사회 구조 설명",
  "central_conflict": "세계의 핵심 갈등"
}}"""

    console.print("[bold cyan]세계관 생성 중...[/bold cyan]")
    raw = call_claude(SYSTEM_PROMPT, prompt, max_tokens=4000)
    world_data = json.loads(raw.strip())

    USER_DIR.mkdir(parents=True, exist_ok=True)
    with open(WORLD_JSON, "w", encoding="utf-8") as f:
        json.dump(world_data, f, ensure_ascii=False, indent=2)

    console.print(f"[bold green]세계관 저장 완료: {WORLD_JSON}[/bold green]")
    return world_data


def load_world() -> dict:
    if not WORLD_JSON.exists():
        raise FileNotFoundError(
            f"세계관 파일이 없습니다: {WORLD_JSON}\n"
            "01_내가_쓰는_것/세계관.json 을 작성하세요."
        )
    with open(WORLD_JSON, encoding="utf-8") as f:
        return json.load(f)

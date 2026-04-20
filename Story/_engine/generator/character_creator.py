"""캐릭터 자동 생성 모듈"""
import json

from rich.console import Console
from _engine.claude_client import call_claude, load_story_config
from _engine.paths import CHAR_JSON, USER_DIR
from _engine.generator.world_builder import load_world

console = Console()




SYSTEM_PROMPT = """당신은 판타지 소설 전문 캐릭터 디자이너입니다.
입체적이고 매력적인 캐릭터를 설계합니다.
결과는 반드시 유효한 JSON 형식으로만 출력하세요. 다른 텍스트는 포함하지 마세요."""


def create_characters(num_main: int = 3, num_sub: int = 4) -> dict:
    """주인공 및 조연 캐릭터를 생성하고 저장"""
    config = load_story_config()
    world = load_world()

    prompt = f"""다음 세계관에 맞는 판타지 소설 캐릭터들을 만들어주세요.

세계관: {world['world_name']}
세계 개요: {world['overview']}
핵심 갈등: {world['central_conflict']}
마법 체계: {world['magic_system']['name']}
소설 테마: {', '.join(config['themes'])}

주인공 {num_main}명, 조연 {num_sub}명을 만들어주세요.

다음 JSON 구조로 출력하세요:
{{
  "main_characters": [
    {{
      "name": "이름",
      "age": 나이(숫자),
      "role": "역할 (주인공/히로인 등)",
      "appearance": "외모 묘사",
      "personality": "성격 묘사",
      "background": "출생 및 성장 배경",
      "motivation": "주요 동기와 목표",
      "abilities": ["능력 목록"],
      "weakness": "약점 또는 내면의 갈등",
      "relationships": {{"캐릭터명": "관계 설명"}},
      "character_arc": "이 캐릭터의 성장 여정"
    }}
  ],
  "sub_characters": [
    {{
      "name": "이름",
      "age": 나이(숫자),
      "role": "역할",
      "appearance": "외모 묘사",
      "personality": "성격",
      "background": "배경",
      "motivation": "동기",
      "abilities": ["능력"],
      "relationship_to_main": "주인공과의 관계"
    }}
  ]
}}"""

    console.print("[bold cyan]캐릭터 생성 중...[/bold cyan]")
    raw = call_claude(SYSTEM_PROMPT, prompt, max_tokens=5000)
    characters = json.loads(raw.strip())

    USER_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHAR_JSON, "w", encoding="utf-8") as f:
        json.dump(characters, f, ensure_ascii=False, indent=2)

    console.print(f"[bold green]캐릭터 저장 완료: {CHAR_JSON}[/bold green]")
    return characters


def load_characters() -> dict:
    if not CHAR_JSON.exists():
        raise FileNotFoundError(
            f"캐릭터 파일이 없습니다: {CHAR_JSON}\n"
            "01_내가_쓰는_것/캐릭터.json 을 작성하세요."
        )
    with open(CHAR_JSON, encoding="utf-8") as f:
        return json.load(f)


def get_character_summary() -> str:
    """챕터 작성에 쓸 캐릭터 요약 텍스트 반환"""
    characters = load_characters()
    lines = []
    for c in characters.get("main_characters", []):
        lines.append(f"- {c['name']} ({c['role']}): {c['personality']} / 목표: {c['motivation']}")
    for c in characters.get("sub_characters", []):
        lines.append(f"- {c['name']} ({c['role']}): {c['personality']}")
    return "\n".join(lines)

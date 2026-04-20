"""Claude API 클라이언트 — 모든 생성 모듈의 공통 기반"""
import os
import json
from dotenv import load_dotenv
import anthropic
from _engine.paths import STORY_CONFIG

load_dotenv()


def get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise EnvironmentError(
            "[오류] .env 파일에 ANTHROPIC_API_KEY가 없습니다.\n"
            ".env 파일을 열어 API 키를 입력하세요."
        )
    return anthropic.Anthropic(api_key=api_key)


def get_model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-opus-4-6")


def load_story_config() -> dict:
    with open(STORY_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def call_claude(system: str, prompt: str, max_tokens: int = 4000) -> str:
    """Claude API 단일 호출 — 집필용 (고품질 모델)"""
    client = get_client()
    model = get_model()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def call_claude_fast(system: str, prompt: str, max_tokens: int = 1500) -> str:
    """Claude API 단일 호출 — 계획/평가용 (빠르고 저렴한 모델)"""
    client = get_client()
    # 계획·평가는 haiku로, 집필만 고품질 모델 사용
    fast_model = os.getenv("CLAUDE_FAST_MODEL", "claude-haiku-4-5-20251001")
    response = client.messages.create(
        model=fast_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text

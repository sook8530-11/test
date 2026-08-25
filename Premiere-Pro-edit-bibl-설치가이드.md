# Premiere Auto-Edit 설치 가이드

원본 저장소: https://github.com/biblcontentofficial-art/Premiere-Pro-edit-bibl
(MIT · 확인 시점 최신 커밋 `c98666c` — 2026-07-19)

말하는 영상에서 무음·추임새·말더듬을 제거하고 -14 LUFS 음량 정리 + 컷 정렬 자막까지 만들어
프리미어에 가져올 수 있는 FCP7 XML 시퀀스로 내보내는 로컬 도구입니다.

---

## 1. 요구사항

| 항목 | 필요 버전 | 비고 |
|------|-----------|------|
| OS | **macOS (Apple Silicon)** | `mlx-whisper`가 애플 실리콘 전용 — 인텔 맥/윈도우/리눅스에서는 자막(음성인식) 단계가 동작하지 않음 |
| Python | 3.10 이상 | |
| ffmpeg | 최신 | `ffprobe` 포함 |
| Premiere Pro | 25.0 이상 | FCP7 XML 가져오기 |

## 2. 설치 (맥 기준)

```bash
# 1) 받기
git clone https://github.com/biblcontentofficial-art/Premiere-Pro-edit-bibl.git
cd Premiere-Pro-edit-bibl

# 2) 시스템 도구
brew install ffmpeg

# 3) 파이썬 의존성 (가상환경 권장)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt      # mlx-whisper, numpy

# 4) 실행 권한
chmod +x edit.sh batch.sh
```

## 3. 설치 확인

```bash
ffmpeg -version | head -1
python3 -c "import mlx_whisper; print('mlx-whisper OK')"

# 엔진 동작 확인 (영상 측정 + 프리셋 추천 — ffmpeg만 사용)
python3 engine/analyze_video.py "테스트영상.mp4"
```

`=== 영상 분석 ===` 과 `>> 추천 프리셋: ...` 이 나오면 정상입니다.

첫 실행 시 Whisper 모델(`mlx-community/whisper-large-v3-turbo`, 약 1.5GB)을
Hugging Face에서 자동 다운로드하므로 시간이 걸립니다.

## 4. 사용

```bash
./edit.sh "원본영상.mp4"                 # 표준 프리셋
./edit.sh "원본영상.mp4" --preset 보수    # 덜 자름
./edit.sh "원본영상.mp4" --preset 공격    # 타이트하게
./batch.sh "촬영본폴더" 표준              # 폴더 일괄 처리
```

결과는 `output/` 에 생성됩니다.

| 파일 | 용도 |
|------|------|
| `*_cut.xml` | 프리미어 `파일 > 가져오기`(Cmd+I) → 시퀀스 |
| `*_cut_audio.wav` | 정리된 오디오 (XML이 자동 연결) |
| `*_cut.srt` / `.vtt` / `.ass` | 자막 — 타임라인에 드래그 |
| `*_words.json` | 받아쓰기 캐시 (설정만 바꿔 재실행할 때 재전사 생략) |
| `*_report.html` | 잘린 구간·자연스러움 주의 구간 리포트 |

## 5. 설정

`engine/config.py`의 프리셋(보수/표준/공격)을 쓰거나, 루트에 `config.json`을 만들어 덮어씁니다.

```bash
cp config.json.example config.json
```

자주 만지는 값: `NOISE_DB`(무음 판정 임계값 — 낮출수록 작은 끝음 보존),
`MIN_SILENCE`(컷 최소 무음 길이), `FILLER_PHRASES`(제거할 추임새 목록), `TARGET_LUFS`(목표 라우드니스).

---

## 6. 이 원격 컨테이너에서 확인한 내용

이 세션의 실행 환경은 **Ubuntu 24.04 / x86_64 (리눅스)** 이라 맥 전용 부분은 여기서 끝까지 검증할 수 없습니다.
확인 결과:

- 클론 — 정상
- `ffmpeg` 6.1.1 + `ffprobe` 설치 — 정상
- `pip install -r requirements.txt` — 설치 자체는 성공 (mlx 0.32.1, mlx-whisper 0.4.3, numpy 2.4.6)
- `engine/analyze_video.py` 스모크 테스트 (합성 12초 클립) — 정상 동작, 무음 감지·라우드니스 측정·프리셋 추천 출력 확인
- `import mlx_whisper` — **실패** (`ImportError: libmlx.so`). 리눅스 x86_64에서는 mlx 런타임이 없어 자막(전사) 단계가 동작하지 않음

즉 컷 계산·음량 측정 등 ffmpeg 기반 기능은 이 환경에서도 돌지만,
**자막 생성을 포함한 전체 파이프라인(`./edit.sh`)은 애플 실리콘 맥에서 실행해야 합니다.**

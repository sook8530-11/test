@echo off
echo ========================================
echo   판타지 소설 자동화 시스템 - 설치
echo ========================================
echo.

echo [1/3] Python 가상환경 생성...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/3] 패키지 설치...
pip install -r requirements.txt

echo [3/3] .env 파일 생성...
if not exist .env (
    copy .env.example .env
    echo .env 파일을 생성했습니다.
    echo .env 파일을 열어서 ANTHROPIC_API_KEY를 입력하세요!
) else (
    echo .env 파일이 이미 존재합니다.
)

echo.
echo ========================================
echo   설치 완료!
echo ========================================
echo.
echo 다음 단계:
echo   1. .env 파일에 ANTHROPIC_API_KEY 입력
echo   2. config\story_config.json에서 소설 설정 수정
echo   3. python main.py setup  (세계관+캐릭터+플롯 자동 생성)
echo   4. python main.py chapter write  (첫 번째 화 작성)
echo.
pause

# 가이드 웹 배포 순서 (아침에)

웹 파일은 `web/`에 준비돼 있다. GitHub Actions 워크플로(`.github/workflows/pages.yml`)가 `web/` 폴더만 GitHub Pages로 올린다.

## 사용자가 할 일 (약 10분)
1. GitHub CLI 설치 후 로그인 (PowerShell)
   ```powershell
   winget install --id GitHub.cli
   ```
   터미널을 새로 연 뒤:
   ```powershell
   gh auth login
   ```
   (GitHub.com → HTTPS → 브라우저 로그인)
2. GoatCounter 가입: https://www.goatcounter.com/signup → 사이트 코드(예: `kbo-guide` → `kbo-guide.goatcounter.com`)를 정해서 Claude에게 알려주기
3. 저장소 이름·공개 여부 정하기 (무료 계정의 Pages는 **공개 저장소**가 필요). 추천 이름: `kbo-gameday-tourism`

## Claude가 할 일 (코드를 받으면 바로)
1. `web/index.html`의 GoatCounter 주석을 풀고 사이트 코드 넣기
2. 배포 URL로 `og:url`·`og:image` 절대경로 넣기, 푸터에 GitHub 저장소 링크
3. 첫 커밋 → `gh repo create <이름> --public --source . --push`
4. Pages를 워크플로 방식으로 켜기: `gh api -X POST repos/<계정>/<이름>/pages -f build_type=workflow`
5. 배포 URL 확인 → 체크포인트 3 보고(미리보기 URL)

## 공개 저장소에 올라가지 않는 것 (.gitignore)
- `.env`(API 키), `forms/`(참가서류: 작성본에 개인정보), `submission/*.hwp|*.pdf`
- `data/raw/api/`(API 응답 캐시), `data/raw/kbo/*.csv`와 `data/processed/kbo_games_clean.csv`(라이선스 표기 없는 제3자 정리본 → `analysis/00_fetch_kbo.py`로 다시 받게 함)

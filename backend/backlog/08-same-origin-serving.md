# 08. 프론트 정적 파일을 같은 출처에서 서빙

상태: 대기
의존: 01, frontend 항목 7(`src/api/` 전환)

## 목표
발표 때 서버 하나만 띄우면 근로자 화면·센터 화면·API가 같은 주소에서 동작하게 한다. `frontend/dist`를 FastAPI가 정적 파일로 서빙하고, 같은 출처이므로 CORS 설정이 필요 없어진다. 다른 기기(휴대폰)에서 접속하는 시연을 위한 것이다.

## 범위
- 하는 것
  - `app/settings.py`에 `STATIC_DIR`(기본 빈 값 = 서빙 안 함) 추가
  - `app/main.py`: `STATIC_DIR`이 있으면 `/api` 외 경로를 정적 파일로, 없는 경로는 `index.html`로 돌려준다(SPA 라우팅). `/api/*`는 정적 파일보다 먼저 매칭된다
  - `README.md` "실행"에 발표용 명령 추가: `npm --prefix frontend run build` → `STATIC_DIR=../frontend/dist uv run fastapi run app/main.py --host 0.0.0.0`
  - `tests/test_static.py`: 임시 폴더에 `index.html`을 두고 `/`, `/center`, `/없는경로`가 `index.html`을, `/api/health`가 JSON을 돌려주는지
- 하지 않는 것
  - 도커·클라우드 배포(`chore/`), HTTPS, 프론트 빌드 설정 변경, 인증

## API·파일
- 변경되는 API 없음. `/`와 프론트 경로가 새로 응답한다
- 추가: `tests/test_static.py`
- 수정: `app/main.py`, `app/settings.py`, `.env.example`, `README.md`

## 완료 기준
- [ ] `uv run pytest` 통과. `STATIC_DIR`이 빈 기본 상태에서 모든 기존 테스트가 그대로 통과한다
- [ ] 프론트를 빌드해 위 명령으로 띄운 뒤, 같은 Wi-Fi의 휴대폰에서 `http://<맥 IP>:8000/`로 근로자 화면이 열리고 전송한 사례가 PC의 `/center`에 나타난다(확인 결과를 `## 결과`에)
- [ ] `STATIC_DIR` 없이 띄우면 `/`가 404이고 `/api/health`는 그대로다
- [ ] `README.md`에 발표용 실행 명령이 있다

## 결과

## 메모
- 프론트가 API 모드(`VITE_API_BASE=/api`)로 빌드되어 있어야 한다. 그 전환은 frontend 항목 7이며, 이 항목은 그 뒤에 한다
- 휴대폰 시연에서 119 안내가 네트워크 실패로 늦으면 안 되므로, 프론트의 "응급 판정 실패 시 브라우저 규칙 대체"가 켜져 있는지 시연 전에 확인한다

/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 비어 있으면 단독 모드, 값이 있으면 API 모드(개발은 `/api`). README "API 연결" */
  readonly VITE_API_BASE?: string;
  /** 통화 ICE 서버(JSON 배열). 비어 있으면 Google 공개 STUN, `[]`이면 같은 망에서만 붙는다. README "API 연결" */
  readonly VITE_ICE_SERVERS?: string;
  /** Google OAuth 웹 클라이언트 ID. 서버 GOOGLE_CLIENT_ID와 같은 값(비밀값 아님). 서버가 WORKER_AUTH=google일 때만 쓴다(backlog 28) */
  readonly VITE_GOOGLE_CLIENT_ID?: string;
  /** 센터 머리글 "근로자 화면 열기"가 여는 주소. 비어 있으면 같은 출처의 `/`. 맥미니 배포는 `https://app.for-nav.com/`(backlog 58) */
  readonly VITE_WORKER_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

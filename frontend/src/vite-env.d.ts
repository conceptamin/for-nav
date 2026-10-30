/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 비어 있으면 단독 모드, 값이 있으면 API 모드(개발은 `/api`). README "API 연결" */
  readonly VITE_API_BASE?: string;
  /** 통화 ICE 서버(JSON 배열). 비어 있으면 Google 공개 STUN, `[]`이면 같은 망에서만 붙는다. README "API 연결" */
  readonly VITE_ICE_SERVERS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

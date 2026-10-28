/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 비어 있으면 단독 모드, 값이 있으면 API 모드(개발은 `/api`). README "API 연결" */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

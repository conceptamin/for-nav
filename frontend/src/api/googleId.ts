// Google Identity Services(backlog 28). 근로자 실제 로그인에서만 스크립트를 불러오고 Google이 그리는 공식 버튼을 붙인다.
// 버튼을 누르면 Google 팝업이 ID 토큰(credential)을 주고, 화면은 그것을 auth.ts의 loginWithGoogle로 서버에 보낸다.
// 화면은 전역 `google`을 직접 쓰지 않고 이 파일만 부른다. ID 토큰은 저장하거나 console에 찍지 않는다.
// 타입은 쓰는 부분만 여기 적는다(@types/google.accounts를 들이지 않는다).

const GSI_SRC = 'https://accounts.google.com/gsi/client';
/** 스크립트를 기다리는 시간. 넘기면 실패로 보인다 */
export const GSI_TIMEOUT_MS = 10000;

const CLIENT_ID = (import.meta.env.VITE_GOOGLE_CLIENT_ID ?? '').trim();

interface GsiButtonOptions {
  type: 'standard';
  theme: 'outline';
  size: 'large';
  shape: 'pill';
  text: 'signin_with';
  logo_alignment: 'left';
  locale: string;
  width: number;
}

interface GoogleAccountsId {
  initialize(config: {
    client_id: string;
    callback: (response: { credential?: string }) => void;
    ux_mode: 'popup';
    auto_select: boolean;
    cancel_on_tap_outside: boolean;
  }): void;
  renderButton(parent: HTMLElement, options: GsiButtonOptions): void;
}

declare global {
  interface Window {
    google?: { accounts?: { id?: GoogleAccountsId } };
  }
}

/** 빌드에 클라이언트 ID가 들어 있는가(`VITE_GOOGLE_CLIENT_ID`) */
export function hasGoogleClientId(): boolean {
  return CLIENT_ID !== '';
}

let loading: Promise<GoogleAccountsId> | null = null;

/** 스크립트를 한 번만 불러온다. 실패(오프라인·차단·시간 초과)하면 다음 호출에서 다시 시도한다 */
function loadGsi(): Promise<GoogleAccountsId> {
  const ready = window.google?.accounts?.id;
  if (ready) return Promise.resolve(ready);
  loading ??= new Promise<GoogleAccountsId>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = GSI_SRC;
    script.async = true;
    const timer = window.setTimeout(() => fail(), GSI_TIMEOUT_MS);
    const fail = () => {
      window.clearTimeout(timer);
      script.remove();
      loading = null;
      reject(new Error('gsi'));
    };
    script.onload = () => {
      window.clearTimeout(timer);
      const id = window.google?.accounts?.id;
      if (id) resolve(id);
      else fail();
    };
    script.onerror = fail;
    document.head.appendChild(script);
  });
  return loading;
}

/**
 * `parent` 안에 공식 Google 로그인 버튼을 그린다. 누르고 로그인하면 `onCredential(ID 토큰)`을 부른다.
 * 스크립트를 불러오지 못하면 예외를 던진다(화면이 실패 문구를 보인다).
 */
export async function renderGoogleButton(parent: HTMLElement, locale: string, onCredential: (credential: string) => void): Promise<void> {
  const id = await loadGsi();
  id.initialize({
    client_id: CLIENT_ID,
    callback: (r) => {
      if (r.credential) onCredential(r.credential);
    },
    ux_mode: 'popup',
    auto_select: false,
    cancel_on_tap_outside: true,
  });
  // Google 버튼 너비는 200~400px 사이 숫자만 받는다. 바닥 버튼 폭에 맞춘다
  const width = Math.round(Math.min(400, Math.max(200, parent.clientWidth)));
  parent.replaceChildren();
  id.renderButton(parent, { type: 'standard', theme: 'outline', size: 'large', shape: 'pill', text: 'signin_with', logo_alignment: 'left', locale, width });
}

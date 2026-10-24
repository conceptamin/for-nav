// 브라우저 저장소 래퍼. 사생활 보호 모드 등에서 실패해도 앱이 멈추지 않게 한다.

export function readJson<T>(store: Storage, key: string, fallback: T): T {
  try {
    const raw = store.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function writeJson(store: Storage, key: string, value: unknown): void {
  try {
    store.setItem(key, JSON.stringify(value));
  } catch {
    // 저장 실패는 무시한다(데모).
  }
}

export function removeKey(store: Storage, key: string): void {
  try {
    store.removeItem(key);
  } catch {
    // 무시
  }
}

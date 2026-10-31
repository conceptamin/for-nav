// Android 뒤로 가기의 앱 규칙(README "뒤로 가기"). 호스트가 window.fornav.onBack()을 부르면 host.ts가 이 처리기를 먼저 묻는다.
// - 첫 화면(/ 언어 선택, /home)에서는 false: 호스트가 앱을 뒤로 보낸다.
// - 앱 바에 ←가 있으면 그것을 누른 것과 같게 한다. 화면이 useScreenBar로 등록한 동작(S-05의 단계 되돌리기 등)이 그대로 돈다.
//   frontend/의 WorkerLayout이 그리는 버튼(.w-header .back)을 찾는다. 이 선택자는 frontend/CLAUDE.md "경계"에 적혀 있다.
// - 그 밖(앱 바를 숨긴 화면, /__host)은 undefined: host.ts의 기본 동작(라우터 이력이 있으면 한 화면 뒤로).

import { setBackHandler } from './host';

export const ROOT_PATHS = ['/', '/home'];

export function backPolicy(): boolean | undefined {
  if (ROOT_PATHS.includes(window.location.pathname)) return false;
  const back = document.querySelector<HTMLButtonElement>('.w-header button.back');
  if (back) {
    back.click();
    return true;
  }
  return undefined;
}

export function installBackPolicy(): void {
  setBackHandler(backPolicy);
}

// 호스트 연결 확인 화면(/__host). 개발 확인용이라 문구는 한국어·영어 고정이고 i18n 키를 만들지 않는다(design.md "호스트 확인 화면").
// 다리가 감지한 것, init으로 받은 값, 주고받은 메시지의 type만 보인다. 본문은 보이지 않는다.

import { useEffect, useRef, useState } from 'react';
import {
  GoogleSignInError,
  hasSeenPushOpen,
  listenHostSpeech,
  onBack,
  PROTOCOL,
  requestGoogleIdToken,
  requestPushToken,
} from '../bridge/host';
import { useHost } from '../bridge/HostProvider';

const API_BASE = (import.meta.env.VITE_API_BASE ?? '').trim();

export function HostCheckPage() {
  const host = useHost();
  const [backResult, setBackResult] = useState<string>('—');
  const [signInResult, setSignInResult] = useState<string>('—');

  // 받아쓰기 시험. 받아쓴 글은 보이지 않고 글자 수·확정 문장 수·오류 종류만 보인다
  const [speechResult, setSpeechResult] = useState<string>('—');
  const stopSpeech = useRef<(() => void) | null>(null);
  useEffect(() => () => stopSpeech.current?.(), []);
  const toggleSpeech = () => {
    if (stopSpeech.current) {
      stopSpeech.current();
      stopSpeech.current = null;
      setSpeechResult((r) => `${r} · 끔 · stopped`);
      return;
    }
    let finals = 0;
    setSpeechResult('듣는 중 · listening');
    const lang = host.locale ?? navigator.language;
    stopSpeech.current = listenHostSpeech(lang, {
      onText: (text, final) => {
        if (final) finals += 1;
        setSpeechResult(`${lang} · 확정 ${finals}문장 · 말하는 중 ${text.length}자`);
      },
      onError: (error) => {
        stopSpeech.current = null;
        setSpeechResult(`speechError ${error}`);
      },
    });
  };

  // 결과 종류만 보인다. 토큰은 보이지도 찍지도 않는다
  const trySignIn = () => {
    setSignInResult('기다리는 중 · waiting');
    requestGoogleIdToken().then(
      () => setSignInResult('성공 · idToken 받음'),
      (e: unknown) => setSignInResult(e instanceof GoogleSignInError ? e.kind : 'failed'),
    );
  };

  // 푸시 시험(backlog 08). 결과 종류만 보인다. FCM 토큰은 보이지도 찍지도 않는다
  const [pushResult, setPushResult] = useState<string>(host.present ? '—' : '호스트 없음 · no host');
  const tryPush = () => {
    setPushResult('기다리는 중 · waiting');
    requestPushToken().then(
      (token) => setPushResult(token ? 'token 받음 · received' : '거부 · denied'),
      () => setPushResult('실패 · failed'),
    );
  };

  const rows: [string, string][] = [
    ['호스트 · Host', host.present ? `있음 (${host.transport})` : '없음 (브라우저 · browser)'],
    ['init 받음 · init received', host.ready ? '예 · yes' : '아니요 · not yet'],
    ['platform', host.platform ?? '—'],
    ['appVersion', host.appVersion ?? '—'],
    ['locale', `${host.locale ?? '—'} (navigator: ${navigator.language})`],
    ['features', host.features.length === 0 ? '[]' : host.features.join(', ')],
    ['insets (px)', `top ${host.insets.top} · right ${host.insets.right} · bottom ${host.insets.bottom} · left ${host.insets.left}`],
    ['API 모드 · API mode', API_BASE === '' ? '단독 · standalone' : `API (${API_BASE})`],
    ['출처 · origin', window.location.origin],
    ['protocol', String(PROTOCOL)],
    ['pushOpen 받음 · received', hasSeenPushOpen() ? '예 · yes' : '아니요 · no'],
  ];

  return (
    <div className="host-check">
      <h1>호스트 연결 확인</h1>
      <p className="muted">Host bridge check · 이 화면은 개발 확인용이다. 근로자 화면은 backlog 02부터다.</p>

      <section className="card">
        <table>
          <tbody>
            {rows.map(([k, v]) => (
              <tr key={k}>
                <th scope="row">{k}</th>
                <td>{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>시험 링크 · Test links</h2>
        <p className="muted">호스트가 init을 보낸 뒤에만 openExternal로 나간다. 그 전과 브라우저에서는 기본 동작이다.</p>
        <p className="links">
          <a className="btn" href="tel:119">
            📞 119
          </a>
          <a className="btn secondary" href="https://map.kakao.com/link/search/%EC%9A%B8%EC%82%B0%EB%8C%80%ED%95%99%EA%B5%90%EB%B3%91%EC%9B%90">
            🗺 카카오맵 · Kakao Map
          </a>
        </p>
        <p className="links">
          <button
            type="button"
            className="btn secondary"
            onClick={() => setBackResult(onBack() ? 'true (뒤로 갔다)' : 'false (갈 곳 없음)')}
          >
            onBack() 호출 · call
          </button>
          <span className="muted">→ {backResult}</span>
        </p>
        <p className="links">
          <button type="button" className="btn secondary" onClick={trySignIn}>
            Google 로그인 시험 · Try sign-in
          </button>
          <span className="muted">→ {signInResult}</span>
        </p>
        <p className="links">
          <button type="button" className="btn secondary" onClick={toggleSpeech}>
            받아쓰기 시험 · Try speech
          </button>
          <span className="muted">→ {speechResult}</span>
        </p>
        <p className="links">
          <button type="button" className="btn secondary" onClick={tryPush}>
            푸시 시험 · Try push
          </button>
          <span className="muted">→ {pushResult}</span>
        </p>
      </section>

      <section className="card">
        <h2>메시지 기록 · Messages (type only)</h2>
        {host.log.length === 0 ? (
          <p className="muted">아직 없음 · none</p>
        ) : (
          <ul className="log">
            {host.log.map((e, i) => (
              <li key={`${e.at}-${i}`}>
                <code>{e.dir === 'out' ? '→ host' : '← host'}</code> {e.type} <span className="muted">{e.at.slice(11, 19)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2>브라우저에서 호스트 흉내 · Fake a host</h2>
        <p className="muted">개발자 도구 콘솔에 두 줄을 차례로 넣는다(새로고침 없음). 첫 줄이 통로, 둘째 줄이 호스트의 init이다. 셋째 줄은 Google 로그인 시험을 누른 뒤 넣는 응답이다. 넷째·다섯째 줄은 푸시 시험의 응답과 알림 탭이다. README "호스트 계약" · backlog 01·08 완료 기준.</p>
        <pre>{`window.ForNav = { postMessage: (s) => console.log('host<-', JSON.parse(s).type) }
window.fornav.receive({ protocol: 1, type: 'init', platform: 'android', appVersion: '0.0.1', locale: 'vi-VN', insets: { top: 24, right: 0, bottom: 48, left: 0 }, features: ['googleSignIn', 'speech', 'push'] })
window.fornav.receive({ protocol: 1, type: 'googleSignInResult', error: 'canceled' })
window.fornav.receive({ protocol: 1, type: 'pushToken', error: 'denied' })
window.fornav.receive({ protocol: 1, type: 'pushOpen', caseId: 'C-251031-001' })`}</pre>
      </section>
    </div>
  );
}

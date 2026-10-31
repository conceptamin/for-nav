// 통화 패널(backlog 26). 근로자 S-12 전송 완료 화면과 센터 C-02가 같이 쓴다.
// 문구는 props로 받는다(근로자는 i18n, 센터는 한국어 고정). 신호·음성·받아쓰기는 api/call.ts의 useCall이 한다.
// 단독 모드에서는 부르는 쪽이 isCallAvailable()로 이 패널을 그리지 않는다.
// 센터 C-02 상담 카드(backlog 51)는 자막을 대화(스크립트)에, 상태·버튼은 대화 바깥 통화 줄(footer)에 그린다.

import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import { createPortal } from 'react-dom';
import { useCall, type CallAuth, type CallEndReason, type CallStopReason } from '../api/call';
import type { Caption, ChatRole } from '../domain/centerCase';
import type { Lang } from '../domain/vocab';

export interface CallLabels {
  start: string;
  accept: string;
  decline: string;
  hangup: string;
  mute: string;
  unmute: string;
  calling: string;
  ringing: string;
  connecting: string;
  inCall: string;
  ended: Record<CallEndReason, string>;
  /** idle인데 상대가 이 사례 화면에 없다. 걸기 버튼이 막힌다 */
  peerAway: string;
  micDenied: string;
  noCaption: string;
  /** 이 브라우저·주소에서는 통화할 수 없다(WebRTC·마이크 없음, HTTP 주소) */
  unsupported: string;
  me: string;
  other: string;
  translating: string;
  machineTranslated: string;
  socketConnecting: string;
  socketReconnecting: string;
  /** unauthorized(4401)는 센터에만 온다. 근로자 문구에는 없고, 없으면 denied 문구를 쓴다 */
  stopped: Record<Exclude<CallStopReason, 'unauthorized'>, string> & { unauthorized?: string };
}

const mmss = (ms: number) => {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
};

/**
 * lang은 내가 말하는 언어(받아쓰기 언어)다. 근로자는 앱 언어, 센터는 ko.
 * `relogin`: 센터 세션이 끝나 멈췄을 때(4401) 멈춤 줄 안에 붙는 다시 로그인 링크
 * `scroller`: 새 자막이 오면 맨 아래로 옮길 스크롤 상자. 없으면 자막 목록 자신
 * `footer`: 상태 줄·안내·버튼 줄을 그릴 자리(카드의 통화 줄). 없으면 자막 목록 바로 위
 */
export function CallPanel({
  caseId,
  auth,
  lang,
  labels,
  locale,
  relogin,
  scroller,
  footer,
}: {
  caseId: string;
  auth: CallAuth;
  lang: Lang;
  labels: CallLabels;
  locale: string;
  relogin?: ReactNode;
  scroller?: RefObject<HTMLElement | null>;
  footer?: HTMLElement | null;
}) {
  const call = useCall(caseId, auth, lang);
  const me: ChatRole = auth.role;
  const other: ChatRole = me === 'worker' ? 'center' : 'worker';
  const audio = useRef<HTMLAudioElement>(null);
  const log = useRef<HTMLDivElement>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (audio.current) audio.current.srcObject = call.remoteStream;
  }, [call.remoteStream]);

  // 통화 시간은 1초마다 다시 그린다
  useEffect(() => {
    if (call.connectedAt === null) return;
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [call.connectedAt]);

  const lines = call.captions.length + call.pending.length + (call.interim.worker ? 1 : 0) + (call.interim.center ? 1 : 0);
  // 새 줄이 오면 목록 맨 아래로 바로 옮긴다(스크롤 효과 없음)
  useEffect(() => {
    const box = scroller?.current ?? log.current;
    if (box) box.scrollTop = box.scrollHeight;
  }, [lines, call.interim.worker, call.interim.center, scroller]);

  if (!call.supported) {
    return (
      <div className="call">
        <div className="notice warn" role="status">
          {labels.unsupported}
        </div>
      </div>
    );
  }

  const open = call.socket === 'open';
  // busy(4409)는 다시 연결을 이어 가면서 이유만 보인다
  const stopped = (call.socket === 'stopped' || call.stopReason === 'busy') && call.stopReason;
  const time = (iso: string) => new Date(iso).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit', hour12: false });
  const who = (from: ChatRole) => (from === me ? labels.me : labels.other);

  let status = '';
  if (call.state === 'calling') status = labels.calling;
  else if (call.state === 'ringing') status = labels.ringing;
  else if (call.state === 'connecting') status = labels.connecting;
  else if (call.state === 'in-call') status = labels.inCall;
  else if (call.state === 'ended' && call.endReason) status = labels.ended[call.endReason];
  if ((call.state === 'idle' || call.state === 'ended') && !stopped) {
    if (!open) status = call.socket === 'reconnecting' ? labels.socketReconnecting : labels.socketConnecting;
    else if (!call.peer[other]) status = status ? `${status} ${labels.peerAway}` : labels.peerAway;
  }

  // 상대 말은 번역을 크게, 내 말은 원문을 크게 보인다. 번역이 없으면(skipped·rejected) 원문만
  const captionLine = (c: Caption) => {
    const mine = c.from === me;
    const ok = c.translation === 'ok' && c.translated !== null;
    const main = !mine && ok ? { text: c.translated!, lang: c.translatedLang } : { text: c.text, lang: c.lang };
    const sub = !ok ? null : mine ? { text: c.translated!, lang: c.translatedLang } : { text: c.text, lang: c.lang };
    return (
      <div key={c.id} className={`call-cap${mine ? ' mine' : ''}`}>
        <span className="call-meta">
          {who(c.from)} · {time(c.at)}
          {ok && <> · {labels.machineTranslated}</>}
        </span>
        <p className="call-main" lang={main.lang} dir="auto">
          {main.text}
        </p>
        {sub && (
          <p className="call-sub" lang={sub.lang} dir="auto">
            {sub.text}
          </p>
        )}
      </div>
    );
  };

  const plainLine = (key: string, from: ChatRole, text: string, kind: 'pending' | 'interim') => (
    <div key={key} className={`call-cap ${kind}${from === me ? ' mine' : ''}`}>
      <span className="call-meta">
        {who(from)}
        {kind === 'pending' && <> · {labels.translating}</>}
      </span>
      <p className="call-main" dir="auto">
        {text}
      </p>
    </div>
  );

  const idle = call.state === 'idle' || call.state === 'ended';
  const controls = (
    <>
      {status && (
        <div className="call-head">
          <p className="call-state" role="status">
            {status}
          </p>
          {call.connectedAt !== null && <span className="call-time">{mmss(now - call.connectedAt)}</span>}
        </div>
      )}
      {stopped && (
        <div className="notice warn" role="status">
          {call.stopReason === 'unauthorized'
            ? (labels.stopped.unauthorized ?? labels.stopped.denied)
            : labels.stopped[call.stopReason as Exclude<CallStopReason, 'unauthorized'>]}
          {call.stopReason === 'unauthorized' && relogin && <> {relogin}</>}
        </div>
      )}
      {call.micDenied && (
        <div className="notice warn" role="alert">
          {labels.micDenied}
        </div>
      )}
      {call.state === 'in-call' && !call.captionSupport && <p className="small muted">{labels.noCaption}</p>}
      <div className="call-actions">
        {idle && (
          <button type="button" className="btn" disabled={!open || !call.peer[other]} onClick={call.start}>
            {labels.start}
          </button>
        )}
        {call.state === 'ringing' && (
          <>
            <button type="button" className="btn" onClick={call.accept}>
              {labels.accept}
            </button>
            <button type="button" className="btn secondary" onClick={call.decline}>
              {labels.decline}
            </button>
          </>
        )}
        {call.state === 'in-call' && (
          <button type="button" className="btn secondary" aria-pressed={call.muted} onClick={call.toggleMute}>
            {call.muted ? labels.unmute : labels.mute}
          </button>
        )}
        {(call.state === 'calling' || call.state === 'connecting' || call.state === 'in-call') && (
          <button type="button" className="btn danger" onClick={call.hangup}>
            {labels.hangup}
          </button>
        )}
      </div>
    </>
  );

  return (
    <div className="call">
      {footer ? createPortal(controls, footer) : controls}
      {(lines > 0 || call.state === 'in-call') && (
        <div className="call-log" ref={log} aria-live="polite">
          {call.captions.map(captionLine)}
          {call.pending.map((p, i) => plainLine(`p-${i}`, p.from, p.text, 'pending'))}
          {(['worker', 'center'] as const).map((r) => call.interim[r] && plainLine(`i-${r}`, r, call.interim[r], 'interim'))}
        </div>
      )}
      <audio ref={audio} autoPlay hidden />
    </div>
  );
}

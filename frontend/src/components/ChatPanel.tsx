// 상담 채팅 패널(backlog 25). 근로자 채팅 시트와 센터 C-02가 같이 쓴다.
// 문구는 props로 받는다(근로자는 i18n, 센터는 한국어 고정). 연결·다시 연결·읽음은 api/chat.ts의 useChat이 한다.
// 단독 모드에서는 부르는 쪽이 isChatAvailable()로 이 패널을 그리지 않는다.
// 흔한 메신저처럼 같은 사람이 같은 분에 이어 보낸 글을 묶고, 시각과 내 글의 읽음은 묶음 끝 말풍선 옆에 한 번만 쓴다(backlog 47).
// 번역이 붙은 글(backend 30)은 통화 자막처럼 상대 글은 번역을, 내 글은 원문을 크게 쓰고 다른 쪽을 작은 줄로 단다(backlog 49).

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode, type RefObject } from 'react';
import { createPortal } from 'react-dom';
import { chatMessageNumber, useChat, type ChatAuth, type ChatStopReason } from '../api/chat';
import type { ChatMessage, ChatRole } from '../domain/centerCase';
import { CHAT_MAX_LEN } from '../domain/centerCase';

export interface ChatLabels {
  empty: string;
  placeholder: string;
  send: string;
  /** 화면 읽기 프로그램에만 읽히는 보낸 사람 */
  me: string;
  other: string;
  /** 내 글 옆: 상대가 읽었다 / 아직 안 읽었다 */
  read: string;
  unread: string;
  connecting: string;
  reconnecting: string;
  /** unauthorized(4401)는 센터에만 온다. 근로자 문구에는 없고, 없으면 denied 문구를 쓴다 */
  stopped: Record<Exclude<ChatStopReason, 'unauthorized'>, string> & { unauthorized?: string };
  rejected: string;
  /** 보낸 글이 번역을 거쳐 되돌아오기 전(backlog 49) */
  translating: string;
  /** 번역이 붙은 말풍선의 작은 줄 앞 표시 */
  machineTranslated: string;
}

const PEER: Record<ChatRole, ChatRole> = { worker: 'center', center: 'worker' };

interface Row {
  m: ChatMessage;
  mine: boolean;
  read: boolean;
  /** 날짜가 바뀌는 첫 글이면 그 날짜 */
  day: string | null;
  /** 묶음의 끝. 시각·읽음을 여기에만 쓴다 */
  last: boolean;
}

/**
 * `relogin`: 센터 세션이 끝나 멈췄을 때(4401) 멈춤 줄 안에 붙는 다시 로그인 링크
 * `active`: 지금 사람이 이 대화를 보고 있다(숨긴 시트면 false). 보고 있고 문서가 보일 때만 읽음을 보낸다
 * `scroller`: 새 글이 오면 맨 아래로 옮길 스크롤 상자. 없으면 메시지 목록 자신
 * `footer`: 입력줄과 상태 줄을 그릴 자리(시트 아래 고정 칸). 없으면 목록 바로 아래
 * `onSeen`: 근로자가 지금 이 대화를 보고 있을 때만 넘긴다. 받은 센터 메시지 수를 알린다(읽은 수, backlog 46)
 * `onPeerCount`: 받은 상대 메시지 수가 바뀔 때마다 알린다. 센터 상담 카드가 스크립트를 보는 사이 온 글을 표시한다(backlog 51)
 */
export function ChatPanel({
  caseId,
  auth,
  me,
  labels,
  locale,
  relogin,
  active = true,
  scroller,
  footer,
  onSeen,
  onPeerCount,
}: {
  caseId: string;
  auth: ChatAuth;
  me: ChatRole;
  labels: ChatLabels;
  locale: string;
  relogin?: ReactNode;
  active?: boolean;
  scroller?: RefObject<HTMLElement | null>;
  footer?: HTMLElement | null;
  onSeen?: (centerMessages: number) => void;
  onPeerCount?: (peerMessages: number) => void;
}) {
  const chat = useChat(caseId, auth);
  const [draft, setDraft] = useState('');
  const log = useRef<HTMLDivElement>(null);

  const centerCount = chat.messages.filter((m) => m.from === 'center').length;
  useEffect(() => {
    if (onSeen && chat.state === 'open') onSeen(centerCount);
  }, [onSeen, centerCount, chat.state]);

  const peerCount = chat.messages.filter((m) => m.from !== me).length;
  useEffect(() => {
    onPeerCount?.(peerCount);
  }, [onPeerCount, peerCount]);

  // 새 메시지가 오면 맨 아래로 바로 옮긴다(스크롤 효과 없음)
  useEffect(() => {
    const box = scroller?.current ?? log.current;
    if (box) box.scrollTop = box.scrollHeight;
  }, [chat.messages.length, chat.pending.length, scroller]);

  // 상대의 마지막 글까지 읽었다고 알린다. 숨긴 시트·다른 탭이면 보내지 않고, 다시 보이면 보낸다
  const lastPeer = [...chat.messages].reverse().find((m) => m.from !== me)?.id ?? null;
  const { markRead, state } = chat;
  useEffect(() => {
    if (!active || !lastPeer || state !== 'open') return;
    const mark = () => {
      if (document.visibilityState === 'visible') markRead(lastPeer);
    };
    mark();
    document.addEventListener('visibilitychange', mark);
    return () => document.removeEventListener('visibilitychange', mark);
  }, [active, lastPeer, state, markRead]);

  const canSend = chat.state === 'open' && draft.trim() !== '';
  // 세션이 끝나 멈췄으면 다시 로그인한 뒤 이어 쓸 수 있게 입력줄을 남긴다(보내기는 막힌다)
  const unauthorized = chat.state === 'stopped' && chat.stopReason === 'unauthorized';
  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    // 보낸 글은 서버가 되돌려 주면 목록에 나타난다. 연결이 닫혀 보내지 못하면 입력을 남긴다
    if (canSend && chat.send(draft)) setDraft('');
  };
  // Enter로 보내고 Shift+Enter는 줄바꿈. 한글 등 조합 중의 Enter는 글자 확정이라 보내지 않는다
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };
  const time = (iso: string) => new Date(iso).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit', hour12: false });
  const date = (iso: string) => new Date(iso).toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' });

  const peerRead = chat.read[PEER[me]];
  const rows: Row[] = chat.messages.map((m, i, list) => {
    const mine = m.from === me;
    const read = mine && chatMessageNumber(m.id) <= peerRead;
    const prev = list[i - 1];
    const next = list[i + 1];
    const day = !prev || date(prev.at) !== date(m.at) ? date(m.at) : null;
    const nextMine = next?.from === me;
    const last =
      !next ||
      next.from !== m.from ||
      time(next.at) !== time(m.at) ||
      date(next.at) !== date(m.at) ||
      (nextMine && chatMessageNumber(next.id) <= peerRead) !== read;
    return { m, mine, read, day, last };
  });

  // 상대 글은 번역이 크고 원문이 작다. 내 글은 원문이 크고 번역이 작다. 번역이 없으면 원문 하나(CallPanel과 같다)
  const lines = (m: ChatMessage, mine: boolean) => {
    const original = { text: m.text, lang: m.lang ?? undefined };
    if (m.translation !== 'ok' || !m.translated) return { main: original, sub: null };
    const translated = { text: m.translated, lang: m.translatedLang ?? undefined };
    return mine ? { main: original, sub: translated } : { main: translated, sub: original };
  };

  const bottom = (
    <>
      {chat.state === 'stopped' && chat.stopReason ? (
        <div className="notice warn" role="status">
          {unauthorized ? (labels.stopped.unauthorized ?? labels.stopped.denied) : labels.stopped[chat.stopReason as Exclude<ChatStopReason, 'unauthorized'>]}
          {unauthorized && relogin && <> {relogin}</>}
        </div>
      ) : (
        chat.state !== 'open' && (
          <p className="chat-state" role="status">
            {chat.state === 'reconnecting' ? labels.reconnecting : labels.connecting}
          </p>
        )
      )}
      {chat.rejected && (
        <div className="notice danger" role="alert">
          {labels.rejected}
        </div>
      )}
      {(chat.state !== 'stopped' || unauthorized) && (
        <form className="chat-input" onSubmit={submit}>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={labels.placeholder}
            aria-label={labels.placeholder}
            maxLength={CHAT_MAX_LEN}
            rows={1}
            dir="auto"
          />
          <button type="submit" className="chat-send" disabled={!canSend} aria-label={labels.send}>
            <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M12 19V5M5.5 11.5 12 5l6.5 6.5" />
            </svg>
          </button>
        </form>
      )}
    </>
  );

  return (
    <div className="chat">
      <div className="chat-log" ref={log} aria-live="polite">
        {rows.length === 0 && chat.pending.length === 0 ? (
          <p className="chat-sys">{labels.empty}</p>
        ) : (
          rows.map(({ m, mine, read, day, last }) => {
            const { main, sub } = lines(m, mine);
            return (
            <div key={m.id} className="chat-item">
              {day && <p className="chat-day">{day}</p>}
              <div className={`chat-row${mine ? ' mine' : ''}${last ? ' last' : ''}`}>
                <div className={`chat-msg${mine ? ' mine' : ''}`}>
                  <span className="sr-only">{mine ? labels.me : labels.other}: </span>
                  <p dir="auto" lang={main.lang}>
                    {main.text}
                  </p>
                  {sub && (
                    <div className="chat-sub">
                      <span className="chat-mt">{labels.machineTranslated}</span>
                      <p dir="auto" lang={sub.lang}>
                        {sub.text}
                      </p>
                    </div>
                  )}
                </div>
                {last && (
                  <span className="chat-meta">
                    {mine && <span className={read ? 'chat-read' : undefined}>{read ? labels.read : labels.unread}</span>}
                    <time dateTime={m.at}>{time(m.at)}</time>
                  </span>
                )}
              </div>
            </div>
            );
          })
        )}
        {chat.pending.map((p) => (
          <div key={`pending-${p.key}`} className="chat-row mine last">
            <div className="chat-msg mine pending">
              <span className="sr-only">{labels.me}: </span>
              <p dir="auto">{p.text}</p>
            </div>
            <span className="chat-meta" role="status">
              {labels.translating}
            </span>
          </div>
        ))}
      </div>
      {footer ? createPortal(bottom, footer) : bottom}
    </div>
  );
}

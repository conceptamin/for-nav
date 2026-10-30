// 상담 채팅 패널(backlog 25). 근로자 S-12 전송 완료 화면과 센터 C-02가 같이 쓴다.
// 문구는 props로 받는다(근로자는 i18n, 센터는 한국어 고정). 연결·다시 연결은 api/chat.ts의 useChat이 한다.
// 단독 모드에서는 부르는 쪽이 isChatAvailable()로 이 패널을 그리지 않는다.

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from 'react';
import { useChat, type ChatAuth, type ChatStopReason } from '../api/chat';
import type { ChatRole } from '../domain/centerCase';
import { CHAT_MAX_LEN } from '../domain/centerCase';

export interface ChatLabels {
  empty: string;
  placeholder: string;
  send: string;
  me: string;
  other: string;
  connecting: string;
  reconnecting: string;
  /** unauthorized(4401)는 센터에만 온다. 근로자 문구에는 없고, 없으면 denied 문구를 쓴다 */
  stopped: Record<Exclude<ChatStopReason, 'unauthorized'>, string> & { unauthorized?: string };
  rejected: string;
}

/** `relogin`: 센터 세션이 끝나 멈췄을 때(4401) 멈춤 줄 안에 붙는 다시 로그인 링크 */
export function ChatPanel({
  caseId,
  auth,
  me,
  labels,
  locale,
  relogin,
}: {
  caseId: string;
  auth: ChatAuth;
  me: ChatRole;
  labels: ChatLabels;
  locale: string;
  relogin?: ReactNode;
}) {
  const chat = useChat(caseId, auth);
  const [draft, setDraft] = useState('');
  const log = useRef<HTMLDivElement>(null);

  // 새 메시지가 오면 목록 맨 아래로 바로 옮긴다(스크롤 효과 없음)
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [chat.messages.length]);

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

  return (
    <div className="chat">
      <div className="chat-log" ref={log} aria-live="polite">
        {chat.messages.length === 0 ? (
          <p className="small muted">{labels.empty}</p>
        ) : (
          chat.messages.map((m) => (
            <div key={m.id} className={`chat-msg${m.from === me ? ' mine' : ''}`}>
              <span className="chat-meta">
                {m.from === me ? labels.me : labels.other} · {time(m.at)}
              </span>
              <p dir="auto">{m.text}</p>
            </div>
          ))
        )}
      </div>
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
            rows={2}
            dir="auto"
          />
          <button type="submit" className="btn" disabled={!canSend}>
            {labels.send}
          </button>
        </form>
      )}
    </div>
  );
}

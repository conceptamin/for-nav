// 근로자·센터 상담 채팅(WS /api/center/cases/{id}/chat, backend 14). 단독/API 모드 분기는 여기에만 있다.
// 단독 모드에는 서버가 없으므로 채팅이 없다. 화면은 isChatAvailable()로 패널째 숨긴다.
// 센터 경로처럼 대체하지 않는다. 끊기면 CHAT_RECONNECT_MS 뒤 다시 붙고, 4403·4404·4000·4401이면 멈춘 이유를 보인다.
// 역할별 "어디까지 읽었나"는 history.read와 read 프레임으로 받고, 내가 읽은 자리는 markRead로 보낸다(backend 28).
// 서버는 번역한 뒤에 메시지를 되돌려 준다(backend 30). 그동안 보낸 글은 pending으로 들고 있다.
// C-01 접수함은 useChatDigests로 사례마다 센터로 붙어 새 채팅 수와 근로자 마지막 글 시각만 본다(읽음을 보내지 않는다, backlog 53).
// 메시지 본문·토큰은 console에 찍지 않는다. 끊김 기록은 닫힘 코드만 남긴다.

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ChatMessage, ChatRole } from '../domain/centerCase';
import { CHAT_MAX_LEN } from '../domain/centerCase';
import { isApiMode, wsUrl } from './http';

/** 예상하지 못한 끊김 뒤 다시 연결하기까지 기다리는 시간 */
export const CHAT_RECONNECT_MS = 3000;

/** 근로자는 S-12 전송 응답의 chatToken으로, 센터는 역할로 붙는다. 서버가 센터 로그인을 쓰면 직원 세션 쿠키가 함께 실린다(backend 17) */
export type ChatAuth = { role: 'worker'; token: string } | { role: 'center' };

export type ChatState = 'connecting' | 'open' | 'reconnecting' | 'stopped';
/** denied: 4403(역할·토큰), missing: 4404(사례 없음), reset: 4000(데모 초기화), unauthorized: 4401(센터 직원 세션 없음, backend 17) */
export type ChatStopReason = 'denied' | 'missing' | 'reset' | 'unauthorized';

const STOP_CODES: Record<number, ChatStopReason> = { 4403: 'denied', 4404: 'missing', 4000: 'reset', 4401: 'unauthorized' };

export interface Chat {
  /** 서버가 준 순서 그대로. 내 메시지도 서버가 되돌려 준 것만 있다 */
  messages: ChatMessage[];
  /** 보냈지만 서버가 아직 되돌려 주지 않은 내 글(번역 중, backend 30). 보낸 순서 */
  pending: PendingMessage[];
  state: ChatState;
  stopReason: ChatStopReason | null;
  /** 마지막으로 보낸 글을 서버가 받지 않았다(error 프레임). 다음에 보내면 지워진다 */
  rejected: boolean;
  /** 역할별로 읽은 마지막 메시지 번호(`m-<n>`의 n). 읽은 것이 없으면 0 */
  read: Record<ChatRole, number>;
  /** 이 연결의 역할이 id까지 읽었다고 알린다. 이미 그 뒤까지 읽었거나 연결이 열려 있지 않으면 보내지 않는다 */
  markRead: (id: string) => void;
  /** 앞뒤 공백을 지운 1~CHAT_MAX_LEN자를 보낸다. 연결이 열려 있지 않거나 길이가 벗어나면 보내지 않고 false */
  send: (text: string) => boolean;
}

/** 상담 채팅을 쓸 수 있는가. 단독 모드에는 서버가 없다 */
export function isChatAvailable(): boolean {
  return isApiMode();
}

/** `m-<n>`의 n. 형식이 다르면 0 */
export function chatMessageNumber(id: string): number {
  const m = /^m-(\d+)$/.exec(id);
  return m ? Number(m[1]) : 0;
}

export interface PendingMessage {
  key: number;
  text: string;
}

const NO_READ: Record<ChatRole, number> = { worker: 0, center: 0 };

const readNumber = (v: unknown) => (typeof v === 'string' ? chatMessageNumber(v) : 0);

const isMessage = (m: unknown): m is ChatMessage => {
  const x = m as Partial<ChatMessage> | null;
  return Boolean(x && typeof x.id === 'string' && typeof x.text === 'string' && (x.from === 'worker' || x.from === 'center') && typeof x.at === 'string');
};

/** 사례 하나의 채팅방에 붙는다. caseId·역할·토큰이 바뀌면 새로 붙고, 화면을 떠나면 닫는다 */
export function useChat(caseId: string, auth: ChatAuth): Chat {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [state, setState] = useState<ChatState>('connecting');
  const [stopReason, setStopReason] = useState<ChatStopReason | null>(null);
  const [rejected, setRejected] = useState(false);
  const [read, setRead] = useState<Record<ChatRole, number>>(NO_READ);
  const [pending, setPending] = useState<PendingMessage[]>([]);
  const pendingKey = useRef(0);
  const socket = useRef<WebSocket | null>(null);
  // 서버가 알려 준 내 역할의 읽은 자리. 같은 값을 다시 보내지 않으려고 렌더와 따로 둔다
  const myRead = useRef(0);
  const role = auth.role;
  const token = auth.role === 'worker' ? auth.token : null;

  useEffect(() => {
    if (!isApiMode()) return;
    const q = new URLSearchParams({ role });
    if (token) q.set('token', token);
    const url = wsUrl(`/center/cases/${encodeURIComponent(caseId)}/chat?${q}`);
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let wasOpen = false;

    const connect = (again: boolean) => {
      setState(again ? 'reconnecting' : 'connecting');
      const ws = new WebSocket(url);
      socket.current = ws;
      ws.onopen = () => {
        if (disposed) return;
        wasOpen = true;
        setState('open');
      };
      ws.onmessage = (e) => {
        if (disposed || typeof e.data !== 'string') return;
        let frame: { type?: string; messages?: unknown; message?: unknown; read?: Partial<Record<ChatRole, unknown>>; role?: unknown; upTo?: unknown };
        try {
          frame = JSON.parse(e.data);
        } catch {
          return;
        }
        if (frame.type === 'history' && Array.isArray(frame.messages)) {
          // 다시 붙을 때마다 서버가 전체를 다시 준다. 통째로 바꿔야 겹치지 않는다
          setMessages(frame.messages.filter(isMessage));
          // 끊긴 사이 보낸 글이 서버에 닿았는지 알 수 없다. 닿았으면 history에 있다
          setPending([]);
          const marks = { worker: readNumber(frame.read?.worker), center: readNumber(frame.read?.center) };
          myRead.current = marks[role];
          setRead(marks);
        } else if (frame.type === 'read' && (frame.role === 'worker' || frame.role === 'center')) {
          const who: ChatRole = frame.role;
          const n = readNumber(frame.upTo);
          if (who === role) myRead.current = Math.max(myRead.current, n);
          setRead((r) => (n > r[who] ? { ...r, [who]: n } : r));
        } else if (frame.type === 'message' && isMessage(frame.message)) {
          const m = frame.message;
          setMessages((list) => (list.some((x) => x.id === m.id) ? list : [...list, m]));
          // 되돌아온 내 글과 같은 글의 번역 중 줄을 하나 지운다. 같은 글이 없으면 가장 오래된 것
          if (m.from === role)
            setPending((list) => {
              const i = list.findIndex((p) => p.text === m.text);
              return list.filter((_, j) => j !== (i < 0 ? 0 : i));
            });
        } else if (frame.type === 'error') {
          // 받지 않은 글은 되돌아오지 않는다. 어느 글인지 알 수 없어 가장 오래된 번역 중 줄을 지운다
          setPending((list) => list.slice(1));
          setRejected(true);
        }
      };
      ws.onclose = (e) => {
        if (disposed) return;
        socket.current = null;
        setPending([]);
        const reason = STOP_CODES[e.code];
        if (reason) {
          console.warn(`[chat] 닫힘 ${e.code} → 멈춤`);
          setState('stopped');
          setStopReason(reason);
          return;
        }
        // 서버가 꺼져 있으면 다시 붙을 때마다 실패하므로, 열려 있던 연결이 끊길 때만 한 번 남긴다
        if (wasOpen) console.warn(`[chat] 닫힘 ${e.code} → ${CHAT_RECONNECT_MS}ms 뒤 다시 연결`);
        wasOpen = false;
        setState('reconnecting');
        timer = setTimeout(() => connect(true), CHAT_RECONNECT_MS);
      };
    };

    setMessages([]);
    setPending([]);
    setRead(NO_READ);
    myRead.current = 0;
    setStopReason(null);
    setRejected(false);
    connect(false);
    return () => {
      disposed = true;
      if (timer) clearTimeout(timer);
      const ws = socket.current;
      socket.current = null;
      // 연결 중에 닫으면 브라우저가 토큰이 든 주소를 콘솔 경고로 남긴다. 열린 뒤에 닫는다
      if (ws?.readyState === WebSocket.CONNECTING) ws.onopen = () => ws.close(1000);
      else ws?.close(1000);
    };
  }, [caseId, role, token]);

  const send = useCallback((text: string) => {
    const t = text.trim();
    const ws = socket.current;
    if (!t || t.length > CHAT_MAX_LEN || !ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(JSON.stringify({ type: 'message', text: t }));
    const key = ++pendingKey.current;
    setPending((list) => [...list, { key, text: t }]);
    setRejected(false);
    return true;
  }, []);

  const markRead = useCallback((id: string) => {
    const n = chatMessageNumber(id);
    const ws = socket.current;
    if (n <= myRead.current || !ws || ws.readyState !== WebSocket.OPEN) return;
    // 서버가 되돌려 주기 전에 같은 값을 또 보내지 않게 먼저 올려 둔다
    myRead.current = n;
    ws.send(JSON.stringify({ type: 'read', upTo: id }));
  }, []);

  return { messages, pending, state, stopReason, rejected, read, markRead, send };
}

/** C-01 접수함이 사례마다 보는 채팅 요약(backlog 53) */
export interface ChatDigest {
  /** 센터가 아직 읽지 않은 근로자 글 수(번호가 서버의 center 읽은 자리보다 큰 것) */
  unread: number;
  /** 근로자 마지막 글 시각(ISO). 근로자 글이 없으면 null */
  lastWorkerAt: string | null;
}

/**
 * 사례 하나의 채팅방에 센터로 붙어 요약만 지켜본다. read를 보내지 않으므로 읽음은 바뀌지 않는다.
 * 끊기면 CHAT_RECONNECT_MS 뒤 다시 붙고, 멈춤 코드면 마지막 요약을 그대로 두고 멈춘다. 닫는 함수를 돌려준다
 */
function watchChat(caseId: string, onDigest: (d: ChatDigest) => void): () => void {
  const url = wsUrl(`/center/cases/${encodeURIComponent(caseId)}/chat?${new URLSearchParams({ role: 'center' })}`);
  let disposed = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let current: WebSocket | null = null;
  let wasOpen = false;
  // 근로자 글의 번호와 시각, 센터가 읽은 자리
  let worker: { n: number; at: string }[] = [];
  let centerRead = 0;

  const publish = () =>
    onDigest({ unread: worker.filter((m) => m.n > centerRead).length, lastWorkerAt: worker.length ? worker[worker.length - 1].at : null });

  const connect = () => {
    const ws = new WebSocket(url);
    current = ws;
    ws.onopen = () => {
      wasOpen = true;
    };
    ws.onmessage = (e) => {
      if (disposed || typeof e.data !== 'string') return;
      let frame: { type?: string; messages?: unknown; message?: unknown; read?: Partial<Record<ChatRole, unknown>>; role?: unknown; upTo?: unknown };
      try {
        frame = JSON.parse(e.data);
      } catch {
        return;
      }
      if (frame.type === 'history' && Array.isArray(frame.messages)) {
        worker = frame.messages
          .filter(isMessage)
          .filter((m) => m.from === 'worker')
          .map((m) => ({ n: chatMessageNumber(m.id), at: m.at }));
        centerRead = readNumber(frame.read?.center);
        publish();
      } else if (frame.type === 'read' && frame.role === 'center') {
        centerRead = Math.max(centerRead, readNumber(frame.upTo));
        publish();
      } else if (frame.type === 'message' && isMessage(frame.message) && frame.message.from === 'worker') {
        const n = chatMessageNumber(frame.message.id);
        if (worker.some((m) => m.n === n)) return;
        worker = [...worker, { n, at: frame.message.at }];
        publish();
      }
    };
    ws.onclose = (e) => {
      if (disposed) return;
      current = null;
      if (STOP_CODES[e.code]) return;
      if (wasOpen) console.warn(`[chat-watch] 닫힘 ${e.code} → ${CHAT_RECONNECT_MS}ms 뒤 다시 연결`);
      wasOpen = false;
      timer = setTimeout(connect, CHAT_RECONNECT_MS);
    };
  };

  connect();
  return () => {
    disposed = true;
    if (timer) clearTimeout(timer);
    const ws = current;
    current = null;
    if (ws?.readyState === WebSocket.CONNECTING) ws.onopen = () => ws.close(1000);
    else ws?.close(1000);
  };
}

/**
 * 여러 사례의 채팅 요약을 지켜본다(C-01, backlog 53). 사례마다 연결 하나이고, 목록에서 빠진 사례는 닫고 새 사례만 연다.
 * 화면을 떠나면 모두 닫는다. 단독 모드에는 채팅이 없어 늘 빈 값이다. 아직 history를 받지 못한 사례는 값이 없다
 */
export function useChatDigests(caseIds: readonly string[]): Record<string, ChatDigest> {
  const [digests, setDigests] = useState<Record<string, ChatDigest>>({});
  const watchers = useRef(new Map<string, () => void>());
  // 폴링마다 새 배열이 와도 같은 사례 묶음이면 다시 붙지 않는다
  const key = [...new Set(caseIds)].sort().join('\n');

  useEffect(() => {
    if (!isApiMode()) return;
    const ids = new Set(key ? key.split('\n') : []);
    for (const [id, close] of watchers.current) {
      if (ids.has(id)) continue;
      close();
      watchers.current.delete(id);
      setDigests((d) => {
        const next = { ...d };
        delete next[id];
        return next;
      });
    }
    for (const id of ids) {
      if (!watchers.current.has(id)) watchers.current.set(id, watchChat(id, (dg) => setDigests((d) => ({ ...d, [id]: dg }))));
    }
  }, [key]);

  useEffect(() => {
    const map = watchers.current;
    return () => {
      map.forEach((close) => close());
      map.clear();
    };
  }, []);

  return digests;
}

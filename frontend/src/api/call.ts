// 근로자·센터 인터넷 통화와 실시간 번역 자막(WS /api/center/cases/{id}/call, backend 16, backlog 26).
// 음성은 브라우저끼리 WebRTC로 직접 오가고, 서버는 signal을 상대에게 그대로 중계하고 받아쓴 확정 문장(caption)을 번역해 양쪽에 보낸다.
// 걸기·받기·끊기와 SDP·ICE, 말하는 중 글은 모두 signal.data 안에 담는다(아래 "signal.data"). 서버는 data를 열어 보지 않는다.
// 단독 모드에는 서버가 없으므로 통화가 없다. 화면은 isCallAvailable()로 패널째 숨긴다.
// 걸거나 받을 때마다 서버에서 TURN이 든 ICE 서버 목록을 받는다(backend 31, backlog 56). 없거나 실패하면 STUN 기본값으로 건다.
// 다시 연결·멈춤 규칙은 useChat과 같다. 통화 중에 신호 연결이 끊겨도 이미 붙은 음성은 끊지 않는다.
// 자막 본문·SDP·ICE(IP 주소)·토큰은 console에 찍지 않는다. 끊김 기록은 닫힘 코드만 남긴다.

import { useCallback, useEffect, useRef, useState } from 'react';
import type { Caption, ChatRole } from '../domain/centerCase';
import { CAPTION_MAX_LEN } from '../domain/centerCase';
import type { Lang } from '../domain/vocab';
import { CHAT_RECONNECT_MS, type ChatAuth, type ChatState, type ChatStopReason } from './chat';
import { isApiMode, logFallback, requestJson, wsUrl } from './http';
import { isSpeechSupported, startSpeech } from './speech';

/** 거는 쪽이 이만큼 기다려도 상대가 받지 않으면 끊는다 */
export const CALL_RING_TIMEOUT_MS = 30000;

/** ICE 서버 목록을 기다리는 시간. 서버의 Cloudflare 호출 제한(3초)보다 조금 길다. 넘으면 STUN 기본값으로 건다 */
export const ICE_FETCH_TIMEOUT_MS = 4000;

/** 채팅과 같은 열쇠로 붙는다(근로자 chatToken, 센터 역할) */
export type CallAuth = ChatAuth;

/** STUN 기본값(결정 2-A). VITE_ICE_SERVERS(JSON 배열)로 바꾸고, `[]`이면 같은 망에서만 붙는다 */
export const DEFAULT_ICE_SERVERS: RTCIceServer[] = [{ urls: 'stun:stun.l.google.com:19302' }];

/**
 * idle → calling(내가 걸었음) / ringing(상대가 걸었음) → connecting(받음, 음성 연결 중) → in-call → ended.
 * 끝난 뒤(ended)에도 다시 걸 수 있다. 마이크 권한이 막히면 idle로 돌아간다(micDenied).
 */
export type CallState = 'idle' | 'calling' | 'ringing' | 'connecting' | 'in-call' | 'ended';
/** self: 내가 끊음, peer: 상대가 끊음, declined: 상대가 거절, no-answer: 30초 무응답(받는 쪽은 놓친 전화), peer-left: 상대 화면이 닫힘, failed: 연결 실패 */
export type CallEndReason = 'self' | 'peer' | 'declined' | 'no-answer' | 'peer-left' | 'failed';
/**
 * 채팅의 멈춤 이유 + busy: 4409(같은 역할이 이미 이 사례 통화에 붙어 있다, 다른 탭 등).
 * busy는 멈추지 않고 이유를 보인 채 다시 연결을 이어 간다. 새로고침·개발 모드 이중 마운트에서 옛 연결이 아직 안 끊긴 경우가 있고,
 * 다른 탭을 닫으면 저절로 붙게 하기 위해서다
 */
export type CallStopReason = ChatStopReason | 'busy';

const STOP_CODES: Record<number, ChatStopReason> = { 4403: 'denied', 4404: 'missing', 4000: 'reset', 4401: 'unauthorized' };
const CLOSE_BUSY = 4409;

/** 확정됐지만 서버 번역이 아직 오지 않은 문장. 같은 쪽 자막이 오면 앞에서부터 지운다 */
export interface PendingLine {
  from: ChatRole;
  text: string;
}

export interface Call {
  /** 이 브라우저·주소에서 통화할 수 있는가(WebRTC와 마이크). HTTP 주소의 휴대폰은 마이크가 없다. false면 연결하지 않는다 */
  supported: boolean;
  /** 신호 연결 상태. 채팅과 같은 규칙 */
  socket: ChatState;
  /** 멈춘 이유. busy만은 socket이 reconnecting인 채로 온다 */
  stopReason: CallStopReason | null;
  state: CallState;
  /** 마지막으로 끝난 이유. 다시 걸거나 전화가 오면 지워진다 */
  endReason: CallEndReason | null;
  /** 마이크 권한이 막혀 걸거나 받지 못했다. 다시 걸거나 받으면 지워진다 */
  micDenied: boolean;
  /** 지금 이 사례 통화 화면에 있는 역할(backend 16 joined·peer) */
  peer: Record<ChatRole, boolean>;
  /** 서버가 번역해 보낸 자막. 말한 순서(id). 화면을 떠나기 전까지 남는다(서버는 저장하지 않는다) */
  captions: Caption[];
  pending: PendingLine[];
  /** 말하는 중인 글. 확정되면 비워진다 */
  interim: Record<ChatRole, string>;
  muted: boolean;
  /** 이 브라우저·언어로 내 말을 받아쓸 수 있는가. false여도 통화와 상대 자막은 그대로다 */
  captionSupport: boolean;
  /** 음성이 붙은 시각(Date.now()). 통화 시간 표시용 */
  connectedAt: number | null;
  /** 상대 음성. 화면이 숨긴 audio로 재생한다 */
  remoteStream: MediaStream | null;
  start: () => void;
  accept: () => void;
  decline: () => void;
  hangup: () => void;
  toggleMute: () => void;
}

/** 통화 패널을 그릴 것인가. 단독 모드에는 서버가 없다 */
export function isCallAvailable(): boolean {
  return isApiMode();
}

function canCall(): boolean {
  return typeof RTCPeerConnection !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia);
}

function iceServers(): RTCIceServer[] {
  const raw = (import.meta.env.VITE_ICE_SERVERS ?? '').trim();
  if (!raw) return DEFAULT_ICE_SERVERS;
  try {
    const v: unknown = JSON.parse(raw);
    if (Array.isArray(v)) return v as RTCIceServer[];
  } catch {
    // 아래에서 기본값으로
  }
  console.warn('[call] VITE_ICE_SERVERS를 읽지 못함 → 기본 STUN');
  return DEFAULT_ICE_SERVERS;
}

/**
 * 서버가 주는 통화 ICE 서버(TURN 자격 증명 포함). 서버에 TURN이 없으면 빈 목록이고, 그때와 실패하면 fallback을 쓴다.
 * 주소에 토큰이 들어 있어 로그에는 고정된 경로 이름만 남긴다. 자격 증명은 찍지 않는다
 */
async function fetchIceServers(caseId: string, role: ChatRole, token: string | null, fallback: RTCIceServer[]): Promise<RTCIceServer[]> {
  const q = new URLSearchParams({ role });
  if (token) q.set('token', token);
  try {
    const r = await requestJson<{ iceServers?: unknown }>(`/center/cases/${encodeURIComponent(caseId)}/call/ice-servers?${q}`, { timeoutMs: ICE_FETCH_TIMEOUT_MS });
    if (Array.isArray(r?.iceServers) && r.iceServers.length > 0) return r.iceServers as RTCIceServer[];
  } catch (e) {
    logFallback('/center/cases/{id}/call/ice-servers', e);
  }
  return fallback;
}

/*
 * signal.data(이 앱끼리만 쓰는 형태, 서버는 그대로 중계한다)
 *   { call: 'ring' | 'accept' | 'decline' | 'hangup' }
 *   { sdp: RTCSessionDescriptionInit }   거는 쪽이 offer, 받는 쪽이 answer
 *   { ice: RTCIceCandidateInit }
 *   { speech: { text, final } }          말하는 중 글(final: false)과 확정 문장(final: true, 번역 전 "번역 중" 줄)
 */
interface SignalData {
  call?: unknown;
  sdp?: RTCSessionDescriptionInit;
  ice?: RTCIceCandidateInit;
  speech?: { text?: unknown; final?: unknown };
}

const isCaption = (c: unknown): c is Caption => {
  const x = c as Partial<Caption> | null;
  return Boolean(x && typeof x.id === 'string' && typeof x.text === 'string' && (x.from === 'worker' || x.from === 'center') && typeof x.at === 'string');
};
const captionNo = (c: Caption) => Number(c.id.replace(/\D/g, '')) || 0;
const NO_ONE: Record<ChatRole, boolean> = { worker: false, center: false };
const NO_INTERIM: Record<ChatRole, string> = { worker: '', center: '' };

interface Actions {
  start: () => void;
  accept: () => void;
  decline: () => void;
  hangup: () => void;
  toggleMute: () => void;
}

/**
 * 사례 하나의 통화방에 붙는다. caseId·역할·토큰·말하는 언어가 바뀌면 새로 붙고, 화면을 떠나면 통화를 끊고 닫는다.
 * lang은 내가 말하는 언어다(근로자는 앱 언어, 센터는 ko). 받아쓰기 언어를 정한다.
 * 통화 중에 언어를 바꿔도 다시 붙지 않는다(통화·자막이 끊기지 않게). 새 언어는 다음 받아쓰기부터 쓴다.
 */
export function useCall(caseId: string, auth: CallAuth, lang: Lang): Call {
  const [supported] = useState(canCall);
  const [socket, setSocket] = useState<ChatState>('connecting');
  const [stopReason, setStopReason] = useState<CallStopReason | null>(null);
  const [state, setState] = useState<CallState>('idle');
  const [endReason, setEndReason] = useState<CallEndReason | null>(null);
  const [micDenied, setMicDenied] = useState(false);
  const [peer, setPeer] = useState<Record<ChatRole, boolean>>(NO_ONE);
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [pending, setPending] = useState<PendingLine[]>([]);
  const [interim, setInterim] = useState<Record<ChatRole, string>>(NO_INTERIM);
  const [muted, setMuted] = useState(false);
  const [captionSupport, setCaptionSupport] = useState(isSpeechSupported);
  const [connectedAt, setConnectedAt] = useState<number | null>(null);
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const actions = useRef<Actions | null>(null);
  const speechLang = useRef(lang);
  speechLang.current = lang;
  const role = auth.role;
  const token = auth.role === 'worker' ? auth.token : null;

  useEffect(() => {
    if (!isApiMode() || !supported) return;
    const other: ChatRole = role === 'worker' ? 'center' : 'worker';
    const q = new URLSearchParams({ role });
    if (token) q.set('token', token);
    const url = wsUrl(`/center/cases/${encodeURIComponent(caseId)}/call?${q}`);
    const ice = iceServers();
    let disposed = false;
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let wasOpen = false;
    // 통화 한 번의 자원. teardown이 모두 정리한다
    let st: CallState = 'idle';
    let pc: RTCPeerConnection | null = null;
    let local: MediaStream | null = null;
    let ringTimer: ReturnType<typeof setTimeout> | null = null;
    let stopSpeech: (() => void) | null = null;
    let speechOk = isSpeechSupported();
    let isMuted = false;
    let lastInterim = '';
    let iceQueue: RTCIceCandidateInit[] = [];
    // 이번 통화의 ICE 서버. 걸거나 받을 때 마이크와 함께 받기 시작해 음성 연결을 만들 때 기다린다
    let iceReq: Promise<RTCIceServer[]> | null = null;
    // signal 처리는 앞의 것이 끝난 뒤에 한다(setRemoteDescription 전에 ICE를 넣지 않게)
    let chain: Promise<void> = Promise.resolve();
    const present: Record<ChatRole, boolean> = { ...NO_ONE };

    const set = (s: CallState) => {
      st = s;
      setState(s);
    };
    const isOpen = () => ws?.readyState === WebSocket.OPEN;
    const send = (frame: object) => {
      if (isOpen()) ws!.send(JSON.stringify(frame));
    };
    const signal = (data: object) => send({ type: 'signal', data });
    const clearRing = () => {
      if (ringTimer) clearTimeout(ringTimer);
      ringTimer = null;
    };

    const sayInterim = (text: string) => {
      if (text === lastInterim) return;
      lastInterim = text;
      signal({ speech: { text, final: false } });
      setInterim((i) => ({ ...i, [role]: text }));
    };

    const stopCaptions = () => {
      stopSpeech?.();
      stopSpeech = null;
      sayInterim('');
    };

    const startCaptions = () => {
      if (!speechOk || stopSpeech || isMuted || st !== 'in-call') return;
      stopSpeech = startSpeech(speechLang.current, {
        onText: (text, final) => {
          if (st !== 'in-call' || isMuted) return;
          if (!final) {
            sayInterim(text);
            return;
          }
          const t = text.slice(0, CAPTION_MAX_LEN);
          sayInterim('');
          if (!isOpen()) return;
          send({ type: 'caption', text: t });
          signal({ speech: { text: t, final: true } });
          setPending((p) => [...p, { from: role, text: t }]);
        },
        onUnsupported: () => {
          speechOk = false;
          stopSpeech = null;
          setCaptionSupport(false);
        },
      });
    };

    const teardown = () => {
      clearRing();
      stopCaptions();
      const p = pc;
      pc = null;
      p?.close();
      local?.getTracks().forEach((t) => t.stop());
      local = null;
      iceQueue = [];
      iceReq = null;
      isMuted = false;
      setMuted(false);
      setRemoteStream(null);
      setConnectedAt(null);
      // 상대의 번역 전 줄과 말하는 중 줄은 통화가 끝나면 지운다. 받은 자막은 남는다
      setPending((list) => list.filter((l) => l.from === role));
      setInterim(NO_INTERIM);
    };

    const end = (reason: CallEndReason) => {
      if (st === 'idle' || st === 'ended') return;
      teardown();
      setEndReason(reason);
      set('ended');
    };

    const getMic = () => navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true }, video: false });

    const loadIce = () => {
      iceReq = fetchIceServers(caseId, role, token, ice);
    };

    /** ICE 서버를 기다린 뒤 음성 연결을 만든다. 그사이 통화가 끝나거나 화면을 떠났으면 null */
    const makePc = async () => {
      const req = iceReq;
      const servers = await (req ?? Promise.resolve(ice));
      if (disposed || st !== 'connecting' || iceReq !== req) return null;
      const p = new RTCPeerConnection({ iceServers: servers });
      local?.getTracks().forEach((t) => p.addTrack(t, local!));
      p.onicecandidate = (e) => {
        if (e.candidate) signal({ ice: e.candidate.toJSON() });
      };
      p.ontrack = (e) => setRemoteStream(e.streams[0] ?? new MediaStream([e.track]));
      p.onconnectionstatechange = () => {
        if (pc !== p) return;
        const cs = p.connectionState;
        if (cs === 'connected' && st === 'connecting') {
          set('in-call');
          setConnectedAt(Date.now());
          startCaptions();
        } else if (cs === 'failed') {
          end('failed');
        } else if (cs === 'disconnected' && st === 'in-call' && (!present[other] || !isOpen())) {
          // 상대 창이 닫혔다. 신호 연결만 잠깐 끊긴 것이면 상대가 아직 있으므로 기다린다
          end('peer-left');
        }
      };
      pc = p;
      return p;
    };

    const flushIce = async (p: RTCPeerConnection) => {
      const queued = iceQueue;
      iceQueue = [];
      for (const c of queued) await p.addIceCandidate(c).catch(() => undefined);
    };

    const onSignal = async (d: SignalData) => {
      if (d.call === 'ring') {
        if (st === 'idle' || st === 'ended') {
          setEndReason(null);
          setMicDenied(false);
          set('ringing');
        } else if (st === 'calling' && role === 'worker' && local) {
          // 둘이 동시에 걸었다. 센터 쪽 걸기를 살리고 근로자는 받는 쪽이 된다(센터는 근로자의 ring을 무시한다)
          clearRing();
          set('connecting');
          signal({ call: 'accept' });
        }
      } else if (d.call === 'accept') {
        if (st !== 'calling' || !local) return;
        clearRing();
        set('connecting');
        const p = await makePc();
        if (!p) return;
        await p.setLocalDescription(await p.createOffer());
        signal({ sdp: p.localDescription });
      } else if (d.call === 'decline') {
        if (st === 'calling') end('declined');
      } else if (d.call === 'hangup') {
        // 받기 전에 거는 쪽이 끊었으면(30초 무응답 포함) 놓친 전화다
        end(st === 'ringing' ? 'no-answer' : 'peer');
      } else if (d.sdp) {
        if (st !== 'connecting' || !local) return;
        if (d.sdp.type === 'offer') {
          const p = pc ?? (await makePc());
          if (!p) return;
          await p.setRemoteDescription(d.sdp);
          await flushIce(p);
          await p.setLocalDescription(await p.createAnswer());
          signal({ sdp: p.localDescription });
        } else if (d.sdp.type === 'answer' && pc) {
          await pc.setRemoteDescription(d.sdp);
          await flushIce(pc);
        }
      } else if (d.ice) {
        if (pc?.remoteDescription) await pc.addIceCandidate(d.ice).catch(() => undefined);
        else iceQueue.push(d.ice);
      } else if (d.speech && typeof d.speech.text === 'string') {
        if (st !== 'in-call') return;
        const text = d.speech.text.slice(0, CAPTION_MAX_LEN);
        if (d.speech.final === true) {
          setPending((p) => [...p, { from: other, text }]);
          setInterim((i) => ({ ...i, [other]: '' }));
        } else {
          setInterim((i) => ({ ...i, [other]: text }));
        }
      }
    };

    const onPeer = (r: ChatRole, here: boolean) => {
      present[r] = here;
      setPeer({ ...present });
      if (r !== other || here) return;
      setInterim((i) => ({ ...i, [other]: '' }));
      if (st === 'calling' || st === 'ringing' || st === 'connecting') end('peer-left');
      else if (st === 'in-call' && pc?.connectionState !== 'connected') end('peer-left');
    };

    const onCaption = (c: Caption) => {
      setCaptions((list) => (list.some((x) => x.id === c.id) ? list : [...list, c].sort((a, b) => captionNo(a) - captionNo(b))));
      setPending((list) => {
        const i = list.findIndex((l) => l.from === c.from);
        return i < 0 ? list : [...list.slice(0, i), ...list.slice(i + 1)];
      });
    };

    const connect = (again: boolean) => {
      setSocket(again ? 'reconnecting' : 'connecting');
      const w = new WebSocket(url);
      ws = w;
      w.onopen = () => {
        if (disposed) return;
        wasOpen = true;
        setSocket('open');
        setStopReason(null);
      };
      w.onmessage = (e) => {
        if (disposed || typeof e.data !== 'string') return;
        let frame: { type?: string; role?: unknown; peers?: unknown; present?: unknown; data?: unknown; caption?: unknown };
        try {
          frame = JSON.parse(e.data);
        } catch {
          return;
        }
        if (frame.type === 'joined') {
          present.worker = false;
          present.center = false;
          present[role] = true;
          if (Array.isArray(frame.peers)) for (const r of frame.peers) if (r === 'worker' || r === 'center') present[r as ChatRole] = true;
          setPeer({ ...present });
        } else if (frame.type === 'peer' && (frame.role === 'worker' || frame.role === 'center')) {
          onPeer(frame.role, frame.present === true);
        } else if (frame.type === 'signal' && frame.data && typeof frame.data === 'object') {
          const d = frame.data as SignalData;
          chain = chain.then(() => onSignal(d)).catch(() => end('failed'));
        } else if (frame.type === 'caption' && isCaption(frame.caption)) {
          onCaption(frame.caption);
        }
      };
      w.onclose = (e) => {
        if (disposed) return;
        ws = null;
        present[other] = false;
        setPeer({ ...present, [role]: false });
        // 아직 음성이 붙기 전이면 신호 없이 이어갈 수 없다. 이미 붙은 음성은 그대로 둔다
        if (st === 'calling' || st === 'ringing' || st === 'connecting') end('failed');
        const reason = STOP_CODES[e.code];
        if (reason) {
          console.warn(`[call] 닫힘 ${e.code} → 멈춤`);
          setSocket('stopped');
          setStopReason(reason);
          return;
        }
        if (e.code === CLOSE_BUSY) setStopReason('busy');
        if (wasOpen || e.code === CLOSE_BUSY) console.warn(`[call] 닫힘 ${e.code} → ${CHAT_RECONNECT_MS}ms 뒤 다시 연결`);
        wasOpen = false;
        setSocket('reconnecting');
        reconnectTimer = setTimeout(() => connect(true), CHAT_RECONNECT_MS);
      };
    };

    actions.current = {
      start: () => {
        if ((st !== 'idle' && st !== 'ended') || !present[other] || !isOpen()) return;
        setEndReason(null);
        setMicDenied(false);
        set('calling');
        loadIce();
        getMic().then(
          (stream) => {
            if (disposed || st !== 'calling') {
              stream.getTracks().forEach((t) => t.stop());
              return;
            }
            local = stream;
            signal({ call: 'ring' });
            ringTimer = setTimeout(() => {
              signal({ call: 'hangup' });
              end('no-answer');
            }, CALL_RING_TIMEOUT_MS);
          },
          () => {
            if (disposed || st !== 'calling') return;
            setMicDenied(true);
            set('idle');
          },
        );
      },
      accept: () => {
        if (st !== 'ringing') return;
        setMicDenied(false);
        set('connecting');
        loadIce();
        getMic().then(
          (stream) => {
            if (disposed || st !== 'connecting') {
              stream.getTracks().forEach((t) => t.stop());
              return;
            }
            local = stream;
            signal({ call: 'accept' });
          },
          () => {
            if (disposed || st !== 'connecting') return;
            signal({ call: 'decline' });
            teardown();
            setMicDenied(true);
            set('idle');
          },
        );
      },
      decline: () => {
        if (st !== 'ringing') return;
        signal({ call: 'decline' });
        teardown();
        set('idle');
      },
      hangup: () => {
        if (st !== 'calling' && st !== 'connecting' && st !== 'in-call') return;
        signal({ call: 'hangup' });
        end('self');
      },
      toggleMute: () => {
        if (!local) return;
        isMuted = !isMuted;
        local.getAudioTracks().forEach((t) => (t.enabled = !isMuted));
        setMuted(isMuted);
        // 음소거 중에는 받아쓰기도 멈춘다(상대 목소리가 내 자막으로 찍히지 않게)
        if (isMuted) stopCaptions();
        else startCaptions();
      },
    };

    setCaptions([]);
    setPending([]);
    setInterim(NO_INTERIM);
    setPeer(NO_ONE);
    setStopReason(null);
    setEndReason(null);
    setMicDenied(false);
    setCaptionSupport(speechOk);
    set('idle');
    connect(false);
    return () => {
      if (st === 'calling' || st === 'connecting' || st === 'in-call') signal({ call: 'hangup' });
      else if (st === 'ringing') signal({ call: 'decline' });
      disposed = true;
      actions.current = null;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      teardown();
      const w = ws;
      ws = null;
      // 연결 중에 닫으면 브라우저가 토큰이 든 주소를 콘솔 경고로 남긴다. 열린 뒤에 닫는다
      if (w?.readyState === WebSocket.CONNECTING) w.onopen = () => w.close(1000);
      else w?.close(1000);
    };
  }, [caseId, role, token, supported]);

  const start = useCallback(() => actions.current?.start(), []);
  const accept = useCallback(() => actions.current?.accept(), []);
  const decline = useCallback(() => actions.current?.decline(), []);
  const hangup = useCallback(() => actions.current?.hangup(), []);
  const toggleMute = useCallback(() => actions.current?.toggleMute(), []);

  return {
    supported,
    socket,
    stopReason,
    state,
    endReason,
    micDenied,
    peer,
    captions,
    pending,
    interim,
    muted,
    captionSupport,
    connectedAt,
    remoteStream,
    start,
    accept,
    decline,
    hangup,
    toggleMute,
  };
}

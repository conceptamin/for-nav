// 센터 채팅 시트(backlog 39). 하단 독의 채팅 아이콘이 지금 화면 위에 연다. 페이지를 옮기지 않는다.
// 보낸 요청이 없으면 요청(종류 → 보낼 내용 → 전송 동의 → 보내기)을 대화로 묻고, 보내면 같은 시트가 센터 채팅으로 이어진다.
// 다시 붙을 수 있는 요청이 하나라도 있으면 독 아이콘으로 열 때 채팅 목록(새 요청 버튼 + 요청 줄)부터 보이고, 줄을 누르면 그 요청의 대화다(backlog 53).
// S-13 요청 줄·S-12 전송·푸시 알림은 목록을 건너뛰고 그 요청의 대화를 연다. 머리의 ←로 목록, 📞로 통화 패널과 오간다.
// 목록을 보는 동안에도 마지막으로 연 요청의 채팅·통화는 숨겨 둔 채 붙어 있다.
// 부르는 쪽(WorkerLayout)은 한 번 연 시트를 닫아도 숨기기만 한다. 채팅 연결·통화가 끊기지 않게 하려는 것이다.
// S-12 페이지(/center-request)와 전송·연락 문구를 같이 쓴다(useSendCenterRequest, workerChatLabels, workerCallLabels).
// S-12 전송 완료 화면의 `💬 센터와 대화` 버튼도 이 시트를 그 요청의 대화로 연다(backlog 44·52·53). 시트는 📞로 통화로 바꿀 수 있다고 안내한다.
// 흔한 메신저 틀이다(backlog 47): 머리(센터 마크·제목·요청 번호) / 대화 한 줄기 / 아래 고정 입력줄. 채팅 입력줄은 ChatPanel이 아래 칸에 그린다.

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { isSessionEnded } from '../api/auth';
import { isCallAvailable } from '../api/call';
import { sendCase } from '../api/center';
import { isChatAvailable } from '../api/chat';
import { useCenterSummary } from '../api/worker';
import { unreadCount, type CaseStatus, type NewCaseResponse } from '../domain/centerCase';
import type { CenterSummaryInput, RequestType } from '../domain/templates';
import { newIntake } from '../domain/triage';
import { LOCALES } from '../domain/vocab';
import type { MessageKey } from '../i18n';
import { formatIsoDate, useT } from '../i18n';
import { useApp } from '../state/AppState';
import { CallPanel, type CallLabels } from './CallPanel';
import { canResume, useCenterLink } from './centerLink';
import { ChatPanel, type ChatLabels } from './ChatPanel';
import { Chip, PolicyDisclaimer, toggleIn } from './common';

export const REQUEST_TYPES: RequestType[] = ['booking', 'interpret', 'policy', 'referral', 'other'];

/** 근로자가 보는 내 요청의 처리 상태 칩(backlog 46). 센터 화면의 StatusPill과 같은 pill 색을 쓴다 */
export function MyCaseStatus({ status }: { status: CaseStatus }) {
  const { t } = useT();
  return <span className={`pill ${status}`}>{t(`caseStatus.${status}` as MessageKey)}</span>;
}

/** 안 읽은 센터 메시지 수 배지(backlog 53, SEED notification-badge Large). 10 이상은 9+. label은 화면 읽기 프로그램만 읽는다 */
export function CountBadge({ n, label, className }: { n: number; label?: string; className?: string }) {
  return (
    <span className={className ? `count-badge ${className}` : 'count-badge'} aria-hidden={label ? undefined : true}>
      {label && <span className="sr-only">{label} </span>}
      {n > 9 ? '9+' : n}
    </span>
  );
}

/**
 * 내 센터 요청 한 줄(backlog 46·53): 요청 번호·보낸 날·처리 상태·안 읽은 수. S-13 목록과 시트의 채팅 목록이 같이 쓴다.
 * onOpen이 없으면(토큰이 없거나 서버가 모르는 요청) 누를 수 없다
 */
export function MyCaseRow({ id, onOpen }: { id: string; onOpen?: () => void }) {
  const app = useApp();
  const { t, lang } = useT();
  const { feed } = useCenterLink();
  const view = feed.cases[id];
  const sentAt = app.caseSentAt[id];
  const unread = unreadCount(view, app.seenCenterMessages[id]);
  const body = (
    <>
      <span>
        📨 <strong>{id}</strong>
        {sentAt && (
          <span className="small muted">
            {' '}
            · {t('myCaseSent')} {formatIsoDate(new Date(sentAt).toLocaleDateString('sv-SE', { timeZone: 'Asia/Seoul' }), lang)}
          </span>
        )}
      </span>
      <span className="my-case-state">
        {view && <MyCaseStatus status={view.status} />}
        {unread > 0 && <CountBadge n={unread} label={t('caseNewMsg')} />}
      </span>
    </>
  );
  return onOpen ? (
    <button type="button" className="row link my-case" onClick={onOpen}>
      {body}
    </button>
  ) : (
    <div className="row link my-case">{body}</div>
  );
}

type T = (key: MessageKey) => string;

export function workerChatLabels(t: T): ChatLabels {
  return {
    empty: t('chatEmpty'),
    placeholder: t('chatPlaceholder'),
    send: t('chatSend'),
    me: t('chatMe'),
    other: t('chatCenter'),
    read: t('chatRead'),
    unread: t('chatUnread'),
    connecting: t('chatConnecting'),
    reconnecting: t('chatReconnecting'),
    stopped: { denied: t('chatStopped'), missing: t('chatStopped'), reset: t('chatStopped') },
    rejected: t('chatRejected'),
    translating: t('liveCallTranslating'),
    machineTranslated: t('liveCallMachineTranslated'),
  };
}

export function workerCallLabels(t: T): CallLabels {
  return {
    start: t('liveCallStart'),
    accept: t('liveCallAccept'),
    decline: t('liveCallDecline'),
    hangup: t('liveCallHangup'),
    mute: t('liveCallMute'),
    unmute: t('liveCallUnmute'),
    calling: t('liveCallCalling'),
    ringing: t('liveCallRinging'),
    connecting: t('liveCallConnecting'),
    inCall: t('liveCallInCall'),
    ended: {
      self: t('liveCallEnded'),
      peer: t('liveCallEnded'),
      'peer-left': t('liveCallEnded'),
      declined: t('liveCallDeclined'),
      'no-answer': t('liveCallNoAnswer'),
      failed: t('liveCallFailed'),
    },
    peerAway: t('liveCallCenterAway'),
    micDenied: t('liveCallMicDenied'),
    noCaption: t('liveCallNoCaption'),
    unsupported: t('liveCallUnsupported'),
    me: t('liveCallMe'),
    other: t('liveCallCenter'),
    translating: t('liveCallTranslating'),
    machineTranslated: t('liveCallMachineTranslated'),
    socketConnecting: t('chatConnecting'),
    socketReconnecting: t('chatReconnecting'),
    stopped: { denied: t('chatStopped'), missing: t('chatStopped'), reset: t('chatStopped'), busy: t('chatReconnecting') },
  };
}

/**
 * 센터 요청 미리보기와 전송. S-12 페이지와 시트가 같이 쓴다.
 * 증상 입력이 없을 때의 대체 입력은 언어마다 한 번만 만든다(렌더마다 새 id·시각이면 미리보기를 끝없이 다시 부른다).
 * API 모드에서 실패하면 대체하지 않고 failed를 세운다. 서버 근로자 세션이 끝났으면 계정을 비워 진입 가드가 로그인으로 보낸다.
 */
export function useSendCenterRequest(types: RequestType[], preview: boolean) {
  const app = useApp();
  const { lang } = useT();
  const [sent, setSent] = useState<NewCaseResponse | null>(null);
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(false);
  const fallback = useMemo(() => newIntake(lang), [lang]);
  const intake = app.intake ?? fallback;
  const insurance = app.coverage?.input.insurance ?? null;
  // 미리보기는 요청 종류를 하나 이상 고른 뒤에만 만든다.
  // 통화·채팅은 domain의 ContactMethod에 없으므로 연락 희망은 보내지 않는다(backlog 29 메모).
  const input: CenterSummaryInput | null =
    preview && !sent && types.length
      ? {
          intake: { ...intake, language: lang },
          requestTypes: types,
          coverage: app.coverage?.result ?? null,
          insurance,
          contactMethod: null,
        }
      : null;
  const summary = useCenterSummary(input);

  const send = async () => {
    if (!types.length) return;
    const consented = [
      intake.symptoms.length ? '증상' : null,
      intake.bodyParts.length ? '부위' : null,
      intake.onset ? '시작 시점' : null,
      intake.workRelated ? '경위(업무 중 여부)' : null,
      intake.freeText ? '자유 입력 메모' : null,
      intake.district ? '구·군' : null,
      intake.industry ? '업종' : null,
      app.coverage ? '제도 경로 결과' : null,
    ].filter((x): x is string => Boolean(x));
    setSending(true);
    setFailed(false);
    try {
      // 요약·긴급도·운영 시간 외 여부·접수 번호는 받는 쪽이 같은 입력으로 계산한다(미리보기 값을 보내지 않는다).
      const r = await sendCase(
        {
          intake: { ...intake, language: lang },
          requestTypes: types,
          coverage: app.coverage?.result ?? null,
          insurance,
          contactMethod: null,
          contact: null,
          consentedItems: consented,
        },
        app.meta.centerHours,
      );
      app.addMyCase(r.case.id, r.case.createdAt, r.chatToken);
      setSent(r);
    } catch (e) {
      if (isSessionEnded(e)) {
        // 서버 근로자 세션이 끝났다(backend 21). 계정을 비우면 진입 가드가 로그인으로 보낸다
        app.endSession();
        return;
      }
      // 입력값은 그대로 둔다. 다시 시도는 같은 입력으로 보낸다.
      setFailed(true);
    } finally {
      setSending(false);
    }
  };

  // 시트에서 새 요청을 다시 시작할 때 앞 전송 결과를 비운다(backlog 53)
  const reset = useCallback(() => {
    setSent(null);
    setFailed(false);
  }, []);

  return { summary, sent, sending, failed, send, reset };
}

/** 운영 시간 안/밖 안내. 다음 운영일은 센터 날짜라 그날 정오(한국 시각)로 읽어 요일이 시간대에 따라 밀리지 않게 한다 */
export function CenterHoursNotice({ sent }: { sent: NewCaseResponse }) {
  const { t, lang } = useT();
  if (!sent.case.afterHours) return <div className="notice ok">{t('cenInHours')}</div>;
  const next = new Date(`${sent.nextOpenDate}T12:00:00+09:00`);
  return (
    <div className="notice warn">
      🌙 {t('cenAfterHours')}{' '}
      <strong>{next.toLocaleDateString(LOCALES[lang], { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'Asia/Seoul' })}</strong>
    </div>
  );
}

/** 시트 머리의 선 아이콘. 독 채팅 아이콘과 같은 선 굵기 */
function Icon({ children }: { children: ReactNode }) {
  return (
    <svg className="sheet-icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {children}
    </svg>
  );
}

export function CenterSheet({ id, open, onClose, focus }: { id: string; open: boolean; onClose: () => void; focus: { id: string | null } }) {
  const app = useApp();
  const { t, lang } = useT();
  const { feed, openCase: openLinkedCase } = useCenterLink();
  const [types, setTypes] = useState<RequestType[]>([]);
  const [agreed, setAgreed] = useState(false);
  const [talk, setTalk] = useState<'chat' | 'call'>('chat');
  // 채팅 목록에 보일 요청: 다시 붙을 수 있는 것, 최근에 보낸 것부터.
  // 상태를 아직 못 받았으면 토큰만 보고, 받은 뒤 서버가 모르는 사례(데모 초기화·서버 재시작)는 건너뛴다
  const listed = app.myCaseIds.filter((caseId) => canResume(feed, caseId, app.chatTokens[caseId]));
  // 보는 것: 채팅 목록 / 요청 하나의 대화 / 새 요청 대화. 목록에 보일 요청이 없으면 목록 대신 새 요청 대화
  const [view, setView] = useState<'list' | 'case' | 'new'>('list');
  const shown = view === 'list' && !listed.length ? 'new' : view;
  // 마지막으로 연 요청. 목록·새 요청을 보는 동안에도 그 채팅·통화를 숨겨 둔 채 붙여 둔다
  const [current, setCurrent] = useState<string | null>(null);
  const { summary, sent, sending, failed, send, reset } = useSendCenterRequest(types, open && shown === 'new');

  const openCase = useCallback((caseId: string) => {
    setCurrent(caseId);
    setView('case');
  }, []);
  // 다른 요청을 열면 채팅부터 보인다(앞 요청의 통화는 칸째 닫힌다)
  useEffect(() => {
    setTalk('chat');
  }, [current]);
  const startNew = () => {
    reset();
    setTypes([]);
    setAgreed(false);
    setView('new');
  };

  // 독 아이콘으로 열면 목록부터, 고른 사례(S-13·S-12·푸시)가 있으면 그 대화로. 여는 차례마다 focus가 새 값이다.
  // 효과가 아니라 렌더 중에 바꾼다. 효과로 바꾸면 지난번 대화가 한 번 그려지며 읽은 것으로 세어진다
  const [opened, setOpened] = useState<{ id: string | null } | null>(null);
  if (open && focus !== opened) {
    setOpened(focus);
    if (focus.id) openCase(focus.id);
    else setView('list');
  }

  // 시트 안에서 보낸 요청이 이제 붙여 둘 요청이다. 첫 요청이면 목록이 막 생겼으므로 보던 대화에 머문다
  useEffect(() => {
    if (!sent) return;
    setCurrent(sent.case.id);
    setView('new');
  }, [sent]);

  // 채팅·통화 칸에 붙는 요청과 그 칸이 보이는지. 새 요청 대화에서는 보낸 뒤에 보낸 요청의 채팅이 이어진다
  const paneCase = shown === 'new' && sent ? sent.case.id : current;
  const paneVisible = shown === 'case' || (shown === 'new' && Boolean(sent));
  // 머리에 보일 요청 번호
  const caseId = paneVisible ? paneCase : null;
  const token = paneCase ? app.chatTokens[paneCase] : undefined;
  const online = Boolean(token) && isChatAvailable();
  const canCall = online && isCallAvailable();
  const status = caseId ? feed.cases[caseId]?.status : undefined;
  // 그 요청의 대화가 보일 때만 읽은 것으로 센다. 목록을 보거나 닫아 둔 동안 온 글은 새 메시지다
  const { markCenterSeen } = app;
  const seeing = open && paneVisible;
  const onSeen = useMemo(() => (seeing && paneCase ? (n: number) => markCenterSeen(paneCase, n) : undefined), [seeing, paneCase, markCenterSeen]);
  // 센터가 걸면 그 요청의 통화 보기로 시트를 연다. 닫아 두었거나 목록을 보고 있어도 전화 온 것을 놓치지 않게 한다
  const onRing = () => {
    if (!paneCase) return;
    setTalk('call');
    openLinkedCase(paneCase);
  };

  const sheet = useRef<HTMLElement>(null);
  const body = useRef<HTMLDivElement>(null);
  // 채팅 입력줄을 그릴 아래 고정 칸. ChatPanel이 포털로 그린다
  const [foot, setFoot] = useState<HTMLDivElement | null>(null);

  // 열면 시트로 초점을 옮기고 Esc로 닫는다. 뒤 화면은 스크롤되지 않게 묶는다
  useEffect(() => {
    if (!open) return;
    sheet.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
    };
  }, [open, onClose]);

  // 대화를 열 때와 보낸 뒤에는 맨 아래(최근 글)를, 목록은 맨 위를 보인다. 숨겨 둔 사이 온 글은 숨긴 상자라 스크롤되지 않았다
  useEffect(() => {
    if (open && body.current) body.current.scrollTop = shown === 'list' ? 0 : body.current.scrollHeight;
  }, [open, sent, shown, current]);

  const typeLabel = (k: RequestType) => t(`req.${k}` as MessageKey);

  return (
    <>
      {open && <div className="sheet-scrim" onClick={onClose} aria-hidden="true" />}
      <section id={id} className="sheet" role="dialog" aria-labelledby={`${id}-title`} hidden={!open} ref={sheet} tabIndex={-1}>
        <header className="sheet-head">
          {shown !== 'list' && listed.length > 0 && (
            <button type="button" className="sheet-btn sheet-back" aria-label={t('back')} onClick={() => setView('list')}>
              <Icon>
                <path d="M15 5l-7 7 7 7" />
              </Icon>
            </button>
          )}
          <img className="sheet-avatar" src="/mark.png" alt="" width="36" height="36" />
          <div className="sheet-title">
            <h2 id={`${id}-title`}>{paneVisible && talk === 'call' && canCall ? t('liveCallTitle') : t('chatTitle')}</h2>
            {caseId && (
              <p>
                {t('cenCaseNo')} {caseId}
                {status && <MyCaseStatus status={status} />}
              </p>
            )}
          </div>
          {paneVisible && canCall && (
            <button
              type="button"
              className="sheet-btn"
              aria-label={talk === 'call' ? t('chatTitle') : t('liveCallTitle')}
              onClick={() => setTalk(talk === 'call' ? 'chat' : 'call')}
            >
              {talk === 'call' ? (
                <Icon>
                  <path d="M12 4c4.7 0 8.5 3.1 8.5 7s-3.8 7-8.5 7c-1 0-2-.15-2.9-.42L4.5 19.5l1.3-3.6C4.3 14.6 3.5 12.9 3.5 11c0-3.9 3.8-7 8.5-7Z" />
                </Icon>
              ) : (
                <Icon>
                  <path d="M6.6 3.5h2.2l1.4 4-2 1.3a11 11 0 0 0 7 7l1.3-2 4 1.4v2.2a2.1 2.1 0 0 1-2.3 2.1A15.6 15.6 0 0 1 4.5 5.8a2.1 2.1 0 0 1 2.1-2.3Z" />
                </Icon>
              )}
            </button>
          )}
          <button type="button" className="sheet-btn" aria-label={t('close')} onClick={onClose}>
            <Icon>
              <path d="M6 6l12 12M18 6 6 18" />
            </Icon>
          </button>
        </header>
        {/* 칸 순서를 보기마다 같게 두어(false 자리 포함) 아래 채팅·통화 칸이 목록을 오가도 다시 붙지 않게 한다 */}
        <div className={shown === 'list' ? 'sheet-body list' : 'sheet-body'} ref={body}>
          {shown === 'list' && (
            <div className="stack my-cases">
              <button type="button" className="btn secondary block" onClick={startNew}>
                ＋ {t('cenTitle')}
              </button>
              {listed.map((caseId) => (
                <MyCaseRow key={caseId} id={caseId} onOpen={() => openCase(caseId)} />
              ))}
              {feed.failed && <div className="notice info">{t('caseStatusFailed')}</div>}
            </div>
          )}
          {shown === 'new' && (
            <>
              <div className="chat-msg">
                <p>{t('cenIntro')}</p>
              </div>
              <div className="chat-msg">
                <p>{t('cenType')}</p>
                {!sent && <span className="chat-meta">{t('cenTypeHint')}</span>}
              </div>
              {sent ? (
                <div className="chat-msg mine">
                  <p>{types.map(typeLabel).join(', ')}</p>
                </div>
              ) : (
                <>
                  <div className="options" role="group" aria-label={t('cenType')}>
                    {REQUEST_TYPES.map((k) => (
                      <Chip key={k} pressed={types.includes(k)} onClick={() => setTypes(toggleIn(types, k))}>
                        {typeLabel(k)}
                      </Chip>
                    ))}
                  </div>
                  {!app.intake && <div className="notice info">{t('cenNoIntake')}</div>}
                </>
              )}
              {!sent && summary && (
                <div className="chat-msg">
                  <p>
                    <strong>{t('cenPreview')}</strong>
                  </p>
                  <div className="native-box">{summary.native}</div>
                  <span className="chat-meta">{t('cenPreviewKo')}</span>
                  {app.coverage && <PolicyDisclaimer infoDate={app.meta.infoDate} />}
                </div>
              )}
              {!sent && types.length > 0 && (
                <>
                  <label className="check">
                    <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
                    <span>{t('cenConsent')}</span>
                  </label>
                  {failed && (
                    <div className="notice danger with-retry" role="alert">
                      <span>{t('sendFailed')}</span>
                      <button type="button" className="btn secondary" disabled={sending || !agreed} onClick={() => void send()}>
                        {t('retry')}
                      </button>
                    </div>
                  )}
                  <button type="button" className="btn block" disabled={!agreed || sending} onClick={() => void send()}>
                    📨 {t('cenSend')}
                  </button>
                  <p className="footer-note">{t('cenHoursNote')}</p>
                </>
              )}
              {sent && (
                <>
                  <p className="chat-sys">
                    ✅ <strong>{t('cenSentTitle')}</strong>
                    <br />
                    {t('cenSentBody')}
                  </p>
                  <CenterHoursNotice sent={sent} />
                </>
              )}
            </>
          )}
          {shown === 'case' && (
            <div className="chat-msg">
              <p>{t('chatIntro')}</p>
            </div>
          )}
          {paneCase && (
            <div className="sheet-pane" key={paneCase} hidden={!paneVisible}>
              {/* 연락 방법을 따로 묻지 않으므로 통화로 바꾸는 머리의 📞을 알려 준다(backlog 44) */}
              {canCall && talk === 'chat' && <p className="chat-sys">{t('chatCallHint')}</p>}
              {/* 통화는 채팅을 보는 동안에도 숨긴 채 붙여 둔다. 그래야 센터에 근로자가 화면에 있는 것으로 보이고, 센터가 걸면 통화 보기로 바뀐다(backlog 55) */}
              {online && token && canCall && (
                <div hidden={talk !== 'call'}>
                  <CallPanel caseId={paneCase} auth={{ role: 'worker', token }} lang={lang} labels={workerCallLabels(t)} locale={LOCALES[lang]} onRing={onRing} />
                </div>
              )}
              {!online || !token ? (
                <p className="chat-sys">{t('talkOffline')}</p>
              ) : talk === 'call' && canCall ? null : (
                <ChatPanel
                  caseId={paneCase}
                  auth={{ role: 'worker', token }}
                  me="worker"
                  labels={workerChatLabels(t)}
                  locale={LOCALES[lang]}
                  active={seeing}
                  scroller={body}
                  footer={foot}
                  onSeen={onSeen}
                />
              )}
            </div>
          )}
        </div>
        <div className="sheet-foot" ref={setFoot} hidden={!paneVisible} />
      </section>
    </>
  );
}

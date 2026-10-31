// 센터 채팅 시트(backlog 39). 하단 독의 채팅 아이콘이 지금 화면 위에 연다. 페이지를 옮기지 않는다.
// 보낸 요청이 없으면 요청(종류 → 보낼 내용 → 전송 동의 → 보내기)을 대화로 묻고, 보내면 같은 시트가 센터 채팅으로 이어진다.
// 이미 보낸 요청(토큰이 있고 완료가 아닌 가장 최근 것, S-13에서 고른 것이 있으면 그것)이 있으면 그 요청의 상태와 채팅만 보인다(backlog 43).
// 머리의 📞로 통화 패널과 오간다.
// 부르는 쪽(WorkerLayout)은 한 번 연 시트를 닫아도 숨기기만 한다. 채팅 연결·통화가 끊기지 않게 하려는 것이다.
// S-12 페이지(/center-request)와 전송·연락 문구를 같이 쓴다(useSendCenterRequest, workerChatLabels, workerCallLabels).

import { useEffect, useMemo, useRef, useState } from 'react';
import { isSessionEnded } from '../api/auth';
import { isCallAvailable } from '../api/call';
import { sendCase } from '../api/center';
import { isChatAvailable } from '../api/chat';
import { useCenterSummary } from '../api/worker';
import type { CaseStatus, NewCaseResponse } from '../domain/centerCase';
import type { CenterSummaryInput, RequestType } from '../domain/templates';
import { newIntake } from '../domain/triage';
import { LOCALES } from '../domain/vocab';
import type { MessageKey } from '../i18n';
import { useT } from '../i18n';
import { useApp } from '../state/AppState';
import { CallPanel, type CallLabels } from './CallPanel';
import { canResume, useCenterLink } from './centerLink';
import { ChatPanel, type ChatLabels } from './ChatPanel';
import { Chip, PolicyDisclaimer, toggleIn } from './common';

export const REQUEST_TYPES: RequestType[] = ['booking', 'interpret', 'policy', 'referral', 'other'];

/** 근로자가 보는 내 요청의 처리 상태 칩(backlog 43). 센터 화면의 StatusPill과 같은 pill 색을 쓴다 */
export function MyCaseStatus({ status }: { status: CaseStatus }) {
  const { t } = useT();
  return <span className={`pill ${status}`}>{t(`caseStatus.${status}` as MessageKey)}</span>;
}

type T = (key: MessageKey) => string;

export function workerChatLabels(t: T): ChatLabels {
  return {
    empty: t('chatEmpty'),
    placeholder: t('chatPlaceholder'),
    send: t('chatSend'),
    me: t('chatMe'),
    other: t('chatCenter'),
    connecting: t('chatConnecting'),
    reconnecting: t('chatReconnecting'),
    stopped: { denied: t('chatStopped'), missing: t('chatStopped'), reset: t('chatStopped') },
    rejected: t('chatRejected'),
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
          emergencyFlag: app.emergencySeen,
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
          emergencyFlag: app.emergencySeen,
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

  return { summary, sent, sending, failed, send };
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

export function CenterSheet({ id, open, onClose, focusCaseId }: { id: string; open: boolean; onClose: () => void; focusCaseId: string | null }) {
  const app = useApp();
  const { t, lang } = useT();
  const { feed } = useCenterLink();
  const [types, setTypes] = useState<RequestType[]>([]);
  const [agreed, setAgreed] = useState(false);
  const [talk, setTalk] = useState<'chat' | 'call'>('chat');
  // 이어 볼 요청: S-13에서 고른 것, 아니면 다시 붙을 수 있고 완료가 아닌 가장 최근 요청.
  // 상태를 아직 못 받았으면 완료가 아닌 것으로 보고, 받은 뒤 서버가 모르는 사례(데모 초기화·서버 재시작)는 건너뛴다
  const resumable = app.myCaseIds.filter((caseId) => canResume(feed, caseId, app.chatTokens[caseId]));
  const focused = focusCaseId && canResume(feed, focusCaseId, app.chatTokens[focusCaseId]) ? focusCaseId : null;
  const existing = focused ?? resumable.find((caseId) => feed.cases[caseId]?.status !== 'done') ?? null;
  // 이어 볼 요청이 없고 지난 요청이 완료되었다
  const prevDone = !existing && resumable.some((caseId) => feed.cases[caseId]?.status === 'done');
  // 시트를 연 뒤 요청을 보냈으면 그 대화를 이어 보인다. 아니면 이미 있는 요청의 채팅만
  const asking = !existing;
  const { summary, sent, sending, failed, send } = useSendCenterRequest(types, open && asking);
  const caseId = sent?.case.id ?? existing;
  const token = caseId ? app.chatTokens[caseId] : undefined;
  const online = Boolean(token) && isChatAvailable();
  const canCall = online && isCallAvailable();
  const status = caseId ? feed.cases[caseId]?.status : undefined;
  // 시트가 열려 있을 때만 읽은 것으로 센다. 닫아도 채팅 연결은 남아 있으므로(숨기기만 한다) 닫힌 동안 온 글은 새 메시지다
  const { markCenterSeen } = app;
  const onSeen = useMemo(() => (open && caseId ? (n: number) => markCenterSeen(caseId, n) : undefined), [open, caseId, markCenterSeen]);

  const sheet = useRef<HTMLElement>(null);
  const body = useRef<HTMLDivElement>(null);

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

  // 보내고 나면 이어지는 채팅이 보이게 대화 맨 아래로 옮긴다
  useEffect(() => {
    if (sent && body.current) body.current.scrollTop = body.current.scrollHeight;
  }, [sent]);

  const typeLabel = (k: RequestType) => t(`req.${k}` as MessageKey);

  return (
    <>
      {open && <div className="sheet-scrim" onClick={onClose} aria-hidden="true" />}
      <section id={id} className="sheet" role="dialog" aria-labelledby={`${id}-title`} hidden={!open} ref={sheet} tabIndex={-1}>
        <header className="sheet-head">
          <h2 id={`${id}-title`}>{talk === 'call' && canCall ? t('liveCallTitle') : t('chatTitle')}</h2>
          {canCall && (
            <button
              type="button"
              className="sheet-btn"
              aria-label={talk === 'call' ? t('chatTitle') : t('liveCallTitle')}
              onClick={() => setTalk(talk === 'call' ? 'chat' : 'call')}
            >
              <span aria-hidden="true">{talk === 'call' ? '💬' : '📞'}</span>
            </button>
          )}
          <button type="button" className="sheet-btn" aria-label={t('close')} onClick={onClose}>
            <span aria-hidden="true">✕</span>
          </button>
        </header>
        <div className="sheet-body" ref={body}>
          {asking || sent ? (
            <>
              {prevDone && !sent && <div className="notice info">{t('casePrevDone')}</div>}
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
                  <div className="chat-msg">
                    <p>
                      ✅ <strong>{t('cenSentTitle')}</strong>
                    </p>
                    <p>{t('cenSentBody')}</p>
                  </div>
                  <CenterHoursNotice sent={sent} />
                </>
              )}
            </>
          ) : (
            <div className="chat-msg">
              <p>{t('chatIntro')}</p>
            </div>
          )}
          {caseId && (
            <>
              <p className="sheet-case small muted">
                {t('cenCaseNo')}: <strong>{caseId}</strong>
                {status && <MyCaseStatus status={status} />}
              </p>
              {!online || !token ? (
                <div className="notice info">{t('talkOffline')}</div>
              ) : talk === 'call' && canCall ? (
                <CallPanel caseId={caseId} auth={{ role: 'worker', token }} lang={lang} labels={workerCallLabels(t)} locale={LOCALES[lang]} />
              ) : (
                <ChatPanel
                  caseId={caseId}
                  auth={{ role: 'worker', token }}
                  me="worker"
                  labels={workerChatLabels(t)}
                  locale={LOCALES[lang]}
                  onSeen={onSeen}
                />
              )}
            </>
          )}
        </div>
      </section>
    </>
  );
}

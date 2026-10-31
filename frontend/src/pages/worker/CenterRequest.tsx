// S-12 센터 상담 요청·전송 확인(FR-70), S-12 연락(센터와 통화·채팅), S-13 내 정보(프로필·설정·내 메모), 병원 이용 안내(정적)
// 요약 미리보기는 api/worker.ts의 useCenterSummary가 만든다. 브라우저 요약을 먼저 그리고, API 모드면 서버 결과로 바꾼다.
// 전송은 api/center.ts의 sendCase가 한다. API 모드에서 실패하면 대체하지 않고 실패 문구와 다시 시도를 보인다.
// 센터 연락 방법은 앱 안 통화(backlog 26)와 채팅(backlog 25) 둘뿐이다(backlog 29). 전송 완료 화면과 /center-chat이 고른 쪽 하나를 보인다.
// 토큰은 API 모드 전송 응답에만 있어 단독 모드에서는 통화·채팅 대신 안내 한 줄을 보인다.

import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { PolicyDisclaimer, SingleSelect, Worse119 } from '../../components/common';
import { CallPanel, type CallLabels } from '../../components/CallPanel';
import { ChatPanel, type ChatLabels } from '../../components/ChatPanel';
import { useScreenBar } from '../../components/WorkerLayout';
import type { MessageKey } from '../../i18n';
import { LANGUAGE_OPTIONS, formatIsoDate, useT } from '../../i18n';
import { useApp } from '../../state/AppState';
import { isSessionEnded, logoutWorker } from '../../api/auth';
import { sendCase } from '../../api/center';
import { isCallAvailable } from '../../api/call';
import { isChatAvailable } from '../../api/chat';
import type { NewCaseResponse } from '../../domain/centerCase';
import { useCenterSummary } from '../../api/worker';
import type { CenterSummaryInput, RequestType } from '../../domain/templates';
import { newIntake } from '../../domain/triage';
import type { Lang } from '../../domain/vocab';
import { LOCALES, SEXES } from '../../domain/vocab';

const REQUEST_TYPES: RequestType[] = ['booking', 'interpret', 'policy', 'referral', 'other'];
type Talk = 'call' | 'chat';
const TALKS: Talk[] = ['call', 'chat'];
const TALK_LABEL = { call: 'liveCallTitle', chat: 'chatTitle' } as const;
const TALK_ICON = { call: '📞', chat: '💬' } as const;

export function CenterRequestPage() {
  const app = useApp();
  const { t, lang } = useT();
  const [params, setParams] = useSearchParams();
  const preset = params.get('type') as RequestType | null;
  const [type, setType] = useState<RequestType | null>(preset && REQUEST_TYPES.includes(preset) ? preset : null);
  const [talk, setTalk] = useState<Talk | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [sent, setSent] = useState<NewCaseResponse | null>(null);
  const [sending, setSending] = useState(false);
  const [sendFailed, setSendFailed] = useState(false);

  const intake = app.intake ?? newIntake(lang);
  const insurance = app.coverage?.input.insurance ?? null;
  // 미리보기는 요청 종류를 고른 뒤에만 만든다.
  // 통화·채팅은 domain의 ContactMethod에 없으므로 연락 희망은 보내지 않는다(backlog 29 메모).
  const summaryInput: CenterSummaryInput | null =
    !sent && type
      ? {
          intake: { ...intake, language: lang },
          emergencyFlag: app.emergencySeen,
          requestType: type,
          coverage: app.coverage?.result ?? null,
          insurance,
          contactMethod: null,
        }
      : null;
  const summary = useCenterSummary(summaryInput);
  useScreenBar({ title: t('cenTitle') });
  // 센터 전송은 로그인한 사람만 한다(FR-03). 로그인·프로필은 진입 가드(WorkerLayout)가 지킨다

  if (sent) {
    // 다음 운영일은 센터 날짜(YYYY-MM-DD)다. 그날 정오(한국 시각)로 읽어 요일이 시간대에 따라 밀리지 않게 한다.
    const next = new Date(`${sent.nextOpenDate}T12:00:00+09:00`);
    return (
      <div>
        <section className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2.6rem' }} aria-hidden>
            ✅
          </div>
          <h1>{t('cenSentTitle')}</h1>
          <p>{t('cenSentBody')}</p>
          <p className="small muted">
            {t('cenCaseNo')}: <strong>{sent.case.id}</strong>
          </p>
        </section>
        {sent.case.afterHours ? (
          <div className="notice warn">
            🌙 {t('cenAfterHours')}{' '}
            <strong>{next.toLocaleDateString(LOCALES[lang], { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'Asia/Seoul' })}</strong>
          </div>
        ) : (
          <div className="notice ok">{t('cenInHours')}</div>
        )}
        <p className="footer-note">{t('cenHoursNote')}</p>
        <CenterTalk caseId={sent.case.id} initial={talk ?? 'chat'} />
        <Worse119 />
        <Link className="btn secondary block" to="/home">
          {t('home')}
        </Link>
      </div>
    );
  }

  const send = async () => {
    if (!type) return;
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
    setSendFailed(false);
    try {
      // 요약·긴급도·운영 시간 외 여부·접수 번호는 받는 쪽이 같은 입력으로 계산한다(미리보기 값을 보내지 않는다).
      const r = await sendCase(
        {
          intake: { ...intake, language: lang },
          emergencyFlag: app.emergencySeen,
          requestType: type,
          coverage: app.coverage?.result ?? null,
          insurance,
          contactMethod: null,
          contact: null,
          consentedItems: consented,
        },
        app.meta.centerHours,
      );
      app.addMyCase(r.case.id, r.chatToken);
      setSent(r);
    } catch (e) {
      if (isSessionEnded(e)) {
        // 서버 근로자 세션이 끝났다(backend 21). 계정을 비우면 진입 가드가 이 주소를 next에 담아 로그인으로 보낸다.
        // 증상 입력은 세션에 남고 요청 종류는 주소(?type=)에 있다. 연락처는 브라우저에 남기지 않으므로(README "상태의 경계") 다시 적는다
        app.endSession();
        return;
      }
      // 입력값은 그대로 둔다. 다시 시도는 같은 입력으로 보낸다.
      setSendFailed(true);
    } finally {
      setSending(false);
    }
  };

  // 입력 화면 골격(backlog 08·17): 고르는 것은 카드 밖, 보내기 버튼 하나가 바닥에 붙는다.
  // 전송이 실패하면 동의 줄 아래에 실패 문구 + 다시 시도(README "비동기 UX 규칙")를 두고, 바닥 버튼도 그대로 남는다.
  return (
    <div className="w-screen">
      <h1>{t('cenTitle')}</h1>
      <p className="muted">{t('cenIntro')}</p>
      {!app.intake && <div className="notice info">{t('cenNoIntake')}</div>}
      <div className="field">
        <span className="label">{t('cenType')}</span>
        <SingleSelect
          options={REQUEST_TYPES}
          value={type}
          onChange={(v) => {
            setType(v);
            // 세션이 끝나 로그인하고 돌아올 때 고른 종류가 남도록 주소에도 둔다
            setParams({ type: v }, { replace: true });
          }}
          label={(k) => t(`req.${k}` as MessageKey)}
        />
      </div>
      <div className="field">
        <span className="label">{t('cenContactMethod')}</span>
        <SingleSelect options={TALKS} value={talk} onChange={setTalk} label={(k) => `${TALK_ICON[k]} ${t(TALK_LABEL[k])}`} />
      </div>

      {summary && (
        <section className="card band">
          <h2>{t('cenPreview')}</h2>
          <div className="native-box">{summary.native}</div>
          <p className="footer-note">{t('cenPreviewKo')}</p>
          {app.coverage && <PolicyDisclaimer infoDate={app.meta.infoDate} />}
        </section>
      )}

      <hr className="divider" />
      <div className="stack">
        <label className="check">
          <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
          <span>{t('cenConsent')}</span>
        </label>
        {sendFailed && (
          <div className="notice danger with-retry" role="alert">
            <span>{t('sendFailed')}</span>
            <button type="button" className="btn secondary" disabled={sending || !type || !agreed} onClick={() => void send()}>
              {t('retry')}
            </button>
          </div>
        )}
      </div>
      <p className="footer-note">{t('cenHoursNote')}</p>
      <Worse119 />
      <footer className="w-footer">
        <button type="button" className="btn block" disabled={!type || !agreed || sending} onClick={() => void send()}>
          📨 {t('cenSend')}
        </button>
      </footer>
    </div>
  );
}

/** 보낸 요청 하나의 센터 연락. 통화·채팅 중 고른 쪽 하나만 보인다. 단독 모드(토큰 없음)면 안내 한 줄 */
function CenterTalk({ caseId, initial }: { caseId: string; initial: Talk }) {
  const app = useApp();
  const { t, lang } = useT();
  const [talk, setTalk] = useState<Talk>(initial);
  const token = app.chatTokens[caseId];
  if (!token || !isChatAvailable()) return <div className="notice info">{t('talkOffline')}</div>;

  const chatLabels: ChatLabels = {
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
  const callLabels: CallLabels = {
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
  return (
    <>
      <div className="field">
        <SingleSelect options={TALKS} value={talk} onChange={setTalk} label={(k) => `${TALK_ICON[k]} ${t(TALK_LABEL[k])}`} />
      </div>
      {talk === 'call' && isCallAvailable() ? (
        <section className="card">
          <h2>{t('liveCallTitle')}</h2>
          <p className="small muted">{t('liveCallIntro')}</p>
          <CallPanel caseId={caseId} auth={{ role: 'worker', token }} lang={lang} labels={callLabels} locale={LOCALES[lang]} />
        </section>
      ) : (
        <section className="card">
          <h2>{t('chatTitle')}</h2>
          <p className="small muted">{t('chatIntro')}</p>
          <ChatPanel caseId={caseId} auth={{ role: 'worker', token }} me="worker" labels={chatLabels} locale={LOCALES[lang]} />
        </section>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// S-12 연락: 하단 채팅 아이콘이 여는 화면. 이 기기에서 보낸 가장 최근 요청(토큰이 있는 것)의 통화·채팅(backlog 29).
// ?via=call이면 통화가 먼저 열린다. 보낸 요청이 없으면 S-12로 보낸다. 로그인·프로필은 진입 가드(WorkerLayout)가 지킨다.
// ---------------------------------------------------------------------------
export function CenterChatPage() {
  const app = useApp();
  const { t } = useT();
  const [params] = useSearchParams();
  useScreenBar({ title: t('chatTitle') });
  const caseId = app.myCaseIds.find((id) => app.chatTokens[id]);
  return (
    <div>
      <h1>{t('cenTitle')}</h1>
      {caseId ? (
        <>
          <p className="small muted">
            {t('cenCaseNo')}: <strong>{caseId}</strong>
          </p>
          <CenterTalk caseId={caseId} initial={params.get('via') === 'call' ? 'call' : 'chat'} />
        </>
      ) : (
        <>
          <div className="notice info">{isChatAvailable() ? t('talkNoCase') : t('talkOffline')}</div>
          <Worse119 />
          <Link className="btn block" to="/center-request">
            🤝 {t('cenTitle')}
          </Link>
        </>
      )}
      {caseId && <Worse119 />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-13 내 정보: 프로필 → 설정(언어) → 내 메모 → 센터로 보낸 요청 → 로그아웃 → 전체 지우기.
// 배치는 backlog/12-home-my.md. 프로필·메모는 이 기기의 계정별 저장소(AppState)에 있고 서버에는 없다(backlog 28).
// ---------------------------------------------------------------------------
const DRINK_KEY = { none: 'drinkNone', sometimes: 'drinkSometimes', often: 'drinkOften' } as const;
const SMOKE_KEY = { no: 'smokeNo', yes: 'smokeYes', quit: 'smokeQuit' } as const;

export function MyPage() {
  const app = useApp();
  const navigate = useNavigate();
  // 로그인 화면으로 먼저 옮긴 뒤(동기) 계정을 비운다. 순서가 바뀌면 진입 가드가 이 화면을 next로 달고 보낸다
  const leave = (clear: () => void) => {
    navigate('/signup', { replace: true, flushSync: true });
    clear();
    void logoutWorker();
  };
  const { t, term, lang } = useT();
  useScreenBar({ title: t('myTitle') });
  const profile = app.profile;
  // 같은 계정의 다른 프로필(backlog 34). 이름을 받지 않으므로 성별·생년월일로 구별한다
  const others = app.profiles.filter((e) => e.id !== app.activeProfileId);
  // 값이 있는 줄만 만든다. null은 줄을 만들지 않는다
  const profileRows: [string, string][] = profile
    ? [
        [t('birthDate'), formatIsoDate(profile.birthDate, lang)],
        [t('sex'), term(SEXES[profile.sex])],
        ...(profile.height != null ? [[t('heightCm'), String(profile.height)] as [string, string]] : []),
        ...(profile.weight != null ? [[t('weightKg'), String(profile.weight)] as [string, string]] : []),
        ...(profile.drinking ? [[t('drinking'), t(DRINK_KEY[profile.drinking])] as [string, string]] : []),
        ...(profile.smoking ? [[t('smoking'), t(SMOKE_KEY[profile.smoking])] as [string, string]] : []),
      ]
    : [];
  return (
    <div>
      <h1>{t('myTitle')}</h1>
      <section className="card">
        <h2>{t('myProfile')}</h2>
        {profileRows.map(([label, value]) => (
          <div className="report-row" key={label}>
            <div className="lbl">{label}</div>
            <div className="val">{value}</div>
          </div>
        ))}
        <div className="stack">
          <Link to="/signup?next=/my" className="btn secondary block">
            {t('myProfileEdit')}
          </Link>
          {others.length > 0 && (
            <>
              <p className="small muted">{t('profileOthers')}</p>
              {others.map((e) => (
                <button key={e.id} type="button" className="btn secondary block" onClick={() => app.selectProfile(e.id)}>
                  👤 {term(SEXES[e.profile.sex])} · {formatIsoDate(e.profile.birthDate, lang)}
                </button>
              ))}
            </>
          )}
          <Link to="/signup?next=/my&new=1" className="btn secondary block">
            ＋ {t('profileAdd')}
          </Link>
          {app.profiles.length > 1 && app.activeProfileId && (
            <button
              type="button"
              className="btn ghost block"
              onClick={() => {
                if (app.activeProfileId && window.confirm(t('profileDeleteConfirm'))) app.deleteProfile(app.activeProfileId);
              }}
            >
              {t('profileDelete')}
            </button>
          )}
        </div>
      </section>
      <section className="card">
        <h2>{t('mySettings')}</h2>
        <div className="field">
          <label htmlFor="my-lang">{t('changeLang')}</label>
          <select id="my-lang" className="input" value={app.lang ?? 'en'} onChange={(e) => app.setLang(e.target.value as Lang)}>
            {LANGUAGE_OPTIONS.map((o) => (
              <option key={o.lang} value={o.lang}>
                {o.native}
              </option>
            ))}
          </select>
        </div>
      </section>
      <section className="card">
        <h2>{t('myReports')}</h2>
        {app.reports.length === 0 ? (
          <p className="muted">{t('myEmpty')}</p>
        ) : (
          <div className="stack" style={{ gap: 8 }}>
            {app.reports.map((r) => (
              <Link key={r.id} to={`/report/${r.id}`} className="row link">
                <span>
                  🩺 {new Date(r.createdAt).toLocaleString(LOCALES[r.language])}
                  <span className="small muted"> · {r.rows.find((row) => row.field === 'symptoms')?.valueNative ?? ''}</span>
                </span>
                <span className="small">{t('myOpen')} →</span>
              </Link>
            ))}
          </div>
        )}
      </section>
      {app.myCaseIds.length > 0 && (
        <section className="card">
          <h2>{t('myCases')}</h2>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {app.myCaseIds.map((id) => (
              <li key={id}>{id}</li>
            ))}
          </ul>
        </section>
      )}
      {/* 로그아웃·지우기는 로그인 화면으로 간다. 서버 세션은 기다리지 않고 지운다 */}
      <button type="button" className="btn secondary block" onClick={() => leave(app.signOut)}>
        {t('logout')}
      </button>
      <button
        type="button"
        className="btn ghost block"
        onClick={() => {
          if (window.confirm(t('myDeleteConfirm'))) leave(app.clearMyData);
        }}
      >
        🗑️ {t('myDelete')}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 병원 이용 방법(정적 콘텐츠, P1)
// ---------------------------------------------------------------------------
export function GuidePage() {
  const { t } = useT();
  const sections: [MessageKey, MessageKey][] = [
    ['guide1t', 'guide1b'],
    ['guide2t', 'guide2b'],
    ['guide3t', 'guide3b'],
    ['guide4t', 'guide4b'],
    ['guide5t', 'guide5b'],
  ];
  return (
    <div>
      <h1>{t('guideTitle')}</h1>
      {sections.map(([title, body]) => (
        <section className="card" key={title}>
          <h2>{t(title)}</h2>
          <p>{t(body)}</p>
        </section>
      ))}
      <p className="footer-note">ⓘ {t('guideCheck')}</p>
      <Worse119 />
      <Link className="btn block" to="/intake">
        🤕 {t('menuSick')}
      </Link>
    </div>
  );
}

// S-12 센터 상담 요청·전송 확인(FR-70), S-13 내 정보(프로필·설정·내 메모), 병원 이용 안내(정적)
// 요약 미리보기와 전송은 components/CenterSheet.tsx의 useSendCenterRequest가 한다(하단 채팅 시트와 같이 쓴다).
// 브라우저 요약을 먼저 그리고 API 모드면 서버 결과로 바꾼다. 전송이 API 모드에서 실패하면 대체하지 않고 실패 문구와 다시 시도를 보인다.
// 센터 연락 방법은 앱 안 통화(backlog 26)와 채팅(backlog 25) 둘뿐이다(backlog 29). 연락 방법은 묻지 않고, 보내면 전송 완료 화면을 보이고
// 거기서 `💬 센터와 대화`를 눌러야 하단 독의 채팅 아이콘과 같은 화면 위 시트(backlog 39)가 그 요청의 채팅으로 열린다(backlog 44·52).
// 통화는 시트 머리의 📞로 바꾼다. 토큰은 API 모드 전송 응답에만 있어 단독 모드에서는 버튼 대신 안내 한 줄을 보인다.

import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { Chip, PhotoStrip, PolicyDisclaimer, toggleIn, Worse119 } from '../../components/common';
import { canResume, useCenterLink } from '../../components/centerLink';
import { CenterHoursNotice, MyCaseRow, REQUEST_TYPES, useSendCenterRequest } from '../../components/CenterSheet';
import { useScreenBar } from '../../components/WorkerLayout';
import type { MessageKey } from '../../i18n';
import { formatIsoDate, useT } from '../../i18n';
import { useApp } from '../../state/AppState';
import { logoutWorker } from '../../api/auth';
import { isChatAvailable } from '../../api/chat';
import type { RequestType } from '../../domain/templates';
import { LOCALES, SEXES } from '../../domain/vocab';

export function CenterRequestPage() {
  const app = useApp();
  const { t } = useT();
  const [params, setParams] = useSearchParams();
  // 여러 개를 고른다(backlog 37). 주소에는 쉼표로 잇는다(?type=booking,interpret)
  const preset = (params.get('type') ?? '').split(',').filter((k): k is RequestType => REQUEST_TYPES.includes(k as RequestType));
  const [types, setTypes] = useState<RequestType[]>(preset);
  const [agreed, setAgreed] = useState(false);
  const { summary, sent, sending, failed: sendFailed, send } = useSendCenterRequest(types, true);
  useScreenBar({ title: t('cenTitle') });
  // 센터 전송은 로그인한 사람만 한다(FR-03). 로그인·프로필은 진입 가드(WorkerLayout)가 지킨다.
  // 세션이 끝나 로그인하고 돌아오면 증상 입력은 세션에, 요청 종류는 주소(?type=)에 남는다

  if (sent) {
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
        <CenterHoursNotice sent={sent} />
        <p className="footer-note">{t('cenHoursNote')}</p>
        <CenterTalk caseId={sent.case.id} />
        <Worse119 />
        <Link className="btn secondary block" to="/home">
          {t('home')}
        </Link>
      </div>
    );
  }

  // 입력 화면 골격(backlog 08·17): 고르는 것은 카드 밖, 보내기 버튼 하나가 바닥에 붙는다.
  // 전송이 실패하면 동의 줄 아래에 실패 문구 + 다시 시도(README "비동기 UX 규칙")를 두고, 바닥 버튼도 그대로 남는다.
  return (
    <div className="w-screen">
      <h1>{t('cenTitle')}</h1>
      <p className="muted">{t('cenIntro')}</p>
      {!app.intake && <div className="notice info">{t('cenNoIntake')}</div>}
      <div className="field">
        <span className="label">{t('cenType')}</span>
        <p className="small muted">{t('cenTypeHint')}</p>
        <div className="options" role="group">
          {REQUEST_TYPES.map((k) => (
            <Chip
              key={k}
              pressed={types.includes(k)}
              onClick={() => {
                const next = toggleIn(types, k);
                setTypes(next);
                // 세션이 끝나 로그인하고 돌아올 때 고른 종류가 남도록 주소에도 둔다
                setParams(next.length ? { type: next.join(',') } : {}, { replace: true });
              }}
            >
              {t(`req.${k}` as MessageKey)}
            </Chip>
          ))}
        </div>
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
            <button type="button" className="btn secondary" disabled={sending || !types.length || !agreed} onClick={() => void send()}>
              {t('retry')}
            </button>
          </div>
        )}
      </div>
      <p className="footer-note">{t('cenHoursNote')}</p>
      <Worse119 />
      <footer className="w-footer">
        <button type="button" className="btn block" disabled={!types.length || !agreed || sending} onClick={() => void send()}>
          📨 {t('cenSend')}
        </button>
      </footer>
    </div>
  );
}

/**
 * 보낸 요청 하나의 센터 연락(backlog 44). 버튼을 눌러야 하단 채팅 시트를 그 요청의 대화로 연다(보낸 직후 저절로 열지 않는다, backlog 52·53).
 * 채팅·통화는 시트가 맡아 페이지에는 패널을 두지 않는다(같은 요청의 연결이 둘 생기지 않게). 단독 모드(토큰 없음)면 안내 한 줄
 */
function CenterTalk({ caseId }: { caseId: string }) {
  const app = useApp();
  const { t } = useT();
  const { openCase } = useCenterLink();
  const online = Boolean(app.chatTokens[caseId]) && isChatAvailable();
  const openSheet = () => openCase(caseId);
  if (!online) return <div className="notice info">{t('talkOffline')}</div>;
  return (
    <button type="button" className="btn block" onClick={openSheet}>
      💬 {t('chatTitle')}
    </button>
  );
}

// ---------------------------------------------------------------------------
// S-13 내 정보: 프로필 → 내 메모 → 센터로 보낸 요청 → 로그아웃 → 전체 지우기.
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
  const { feed, openCase } = useCenterLink();
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
                  <PhotoStrip photos={r.photos} />
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
          {/* 줄마다 보낸 날·처리 상태·안 읽은 수(backlog 46·53). 다시 붙을 수 있으면 눌러 그 대화를 시트로 연다.
              토큰이 없는 요청(backlog 46 이전에 세션이 끝나 열쇠를 잃은 것, 단독 모드)과 서버가 모르는 요청은 누를 수 없다 */}
          <div className="stack my-cases">
            {app.myCaseIds.map((id) => (
              <MyCaseRow key={id} id={id} onOpen={canResume(feed, id, app.chatTokens[id]) ? () => openCase(id) : undefined} />
            ))}
          </div>
          {feed.failed && <div className="notice info">{t('caseStatusFailed')}</div>}
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
  // 1~4는 차례(번호는 문구 안), 5·6은 차례가 아니라 덧붙이는 안내라 번호 대신 아이콘을 앞에 둔다(backlog 54)
  const sections: [MessageKey, MessageKey, string?][] = [
    ['guide1t', 'guide1b'],
    ['guide2t', 'guide2b'],
    ['guide3t', 'guide3b'],
    ['guide4t', 'guide4b'],
    ['guide5t', 'guide5b', '🦺'],
    ['guide6t', 'guide6b', '🌙'],
  ];
  return (
    <div>
      <h1>{t('guideTitle')}</h1>
      {sections.map(([title, body, icon]) => (
        <section className="card" key={title}>
          <h2>
            {icon && `${icon} `}
            {t(title)}
          </h2>
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

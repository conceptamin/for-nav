// S-12 센터 상담 요청·전송 확인(FR-70), S-13 내 정보(프로필·설정·내 메모), 병원 이용 안내(정적)
// 요약 미리보기는 api/worker.ts의 useCenterSummary가 만든다. 브라우저 요약을 먼저 그리고, API 모드면 서버 결과로 바꾼다.
// 전송은 api/center.ts의 sendCase가 한다. API 모드에서 실패하면 대체하지 않고 실패 문구와 다시 시도를 보인다.

import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { PolicyDisclaimer, SingleSelect, Worse119 } from '../../components/common';
import { useScreenBar } from '../../components/WorkerLayout';
import type { MessageKey } from '../../i18n';
import { LANGUAGE_OPTIONS, useT } from '../../i18n';
import { useApp } from '../../state/AppState';
import { sendCase } from '../../api/center';
import type { NewCaseResponse } from '../../domain/centerCase';
import { useCenterSummary } from '../../api/worker';
import type { CenterSummaryInput, ContactMethod, RequestType } from '../../domain/templates';
import { newIntake } from '../../domain/triage';
import type { Lang } from '../../domain/vocab';
import { LOCALES, SEXES } from '../../domain/vocab';

const REQUEST_TYPES: RequestType[] = ['booking', 'interpret', 'policy', 'referral', 'other'];
const CONTACT_METHODS: ContactMethod[] = ['phone', 'sms', 'kakao', 'zalo', 'visit'];

export function CenterRequestPage() {
  const app = useApp();
  const { t, lang } = useT();
  const [params] = useSearchParams();
  const preset = params.get('type') as RequestType | null;
  const [type, setType] = useState<RequestType | null>(preset && REQUEST_TYPES.includes(preset) ? preset : null);
  const [method, setMethod] = useState<ContactMethod | null>(null);
  const [contact, setContact] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [sent, setSent] = useState<NewCaseResponse | null>(null);
  const [sending, setSending] = useState(false);
  const [sendFailed, setSendFailed] = useState(false);

  const intake = app.intake ?? newIntake(lang);
  const insurance = app.coverage?.input.insurance ?? null;
  // 미리보기는 회원이 요청 종류를 고른 뒤에만 만든다. 비회원은 이 화면에서 아무것도 서버로 보내지 않는다.
  // 연락처는 요약 입력에 없으므로 미리보기 요청에 들어가지 않는다.
  const summaryInput: CenterSummaryInput | null =
    app.mode === 'member' && !sent && type
      ? {
          intake: { ...intake, language: lang },
          emergencyFlag: app.emergencySeen,
          requestType: type,
          coverage: app.coverage?.result ?? null,
          insurance,
          contactMethod: method,
        }
      : null;
  const summary = useCenterSummary(summaryInput);
  useScreenBar({ title: t('cenTitle') });

  // 센터 전송은 회원만 가능(FR-03)
  if (app.mode !== 'member') {
    return (
      <div>
        <h1>{t('cenTitle')}</h1>
        <p className="muted">{t('cenIntro')}</p>
        <div className="card">
          <p>{t('cenNeedMember')}</p>
          <Link className="btn block big" to="/signup?next=/center-request">
            {t('cenMakeProfile')}
          </Link>
        </div>
        <Worse119 />
      </div>
    );
  }

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
      contact.trim() ? '연락처' : null,
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
          contactMethod: method,
          contact: contact.trim() || null,
          consentedItems: consented,
        },
        app.meta.centerHours,
      );
      app.addMyCase(r.case.id);
      setSent(r);
    } catch {
      // 입력값은 그대로 둔다. 다시 시도는 같은 입력으로 보낸다.
      setSendFailed(true);
    } finally {
      setSending(false);
    }
  };

  // 입력 화면 골격(design.md "화면 골격"): 고르는 것은 카드 밖, 보내기 버튼 하나가 바닥에 붙는다.
  // 전송이 실패해도 바닥 버튼은 그대로 있고, 누르면 같은 입력으로 다시 보낸다(바닥에 버튼을 둘 두지 않는다).
  return (
    <div className="w-screen">
      <h1>{t('cenTitle')}</h1>
      <p className="muted">{t('cenIntro')}</p>
      {!app.intake && <div className="notice info">{t('cenNoIntake')}</div>}
      <div className="field">
        <span className="label">{t('cenType')}</span>
        <SingleSelect options={REQUEST_TYPES} value={type} onChange={setType} label={(k) => t(`req.${k}` as MessageKey)} />
      </div>
      <div className="field">
        <span className="label">{t('cenContactMethod')}</span>
        <SingleSelect options={CONTACT_METHODS} value={method} onChange={setMethod} label={(k) => t(`contact.${k}` as MessageKey)} />
      </div>
      {method && method !== 'visit' && (
        <div className="field">
          <label htmlFor="contact">
            {t('cenContact')} <span className="small muted">({t('optional')})</span>
          </label>
          <input id="contact" type="text" inputMode={method === 'phone' || method === 'sms' ? 'tel' : 'text'} value={contact} onChange={(e) => setContact(e.target.value)} maxLength={40} />
          <span className="small muted">{t('cenContactHint')}</span>
        </div>
      )}

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
          <div className="notice danger" role="alert">
            {t('sendFailed')}
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

// ---------------------------------------------------------------------------
// S-13 내 정보: 프로필 → 설정(언어) → 내 메모 → 센터로 보낸 요청 → 전체 지우기.
// 배치는 design.md "홈과 내 화면". 전부 브라우저 안 상태(AppState)이고 서버 계정은 없다.
// ---------------------------------------------------------------------------
const DRINK_KEY = { none: 'drinkNone', sometimes: 'drinkSometimes', often: 'drinkOften' } as const;
const SMOKE_KEY = { no: 'smokeNo', yes: 'smokeYes', quit: 'smokeQuit' } as const;

export function MyPage() {
  const app = useApp();
  const { t, term } = useT();
  const [deleted, setDeleted] = useState(false);
  useScreenBar({ title: t('myTitle') });
  const profile = app.mode === 'member' ? app.profile : null;
  // 값이 있는 줄만 만든다. null은 줄을 만들지 않는다
  const profileRows: [string, string][] = profile
    ? [
        [t('birthDate'), profile.birthDate],
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
      {app.mode !== 'member' && <div className="notice warn">{t('repSavedGuest')}</div>}
      <section className="card">
        <h2>{t('myProfile')}</h2>
        {profile ? (
          <>
            {profileRows.map(([label, value]) => (
              <div className="report-row" key={label}>
                <div className="lbl">{label}</div>
                <div className="val">{value}</div>
              </div>
            ))}
            <Link to="/signup?next=/my" className="btn secondary block">
              {t('myProfileEdit')}
            </Link>
          </>
        ) : (
          <>
            <p className="muted">{t('myProfileGuestHint')}</p>
            <Link to="/signup?next=/my" className="btn block">
              {t('myProfileCreate')}
            </Link>
          </>
        )}
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
      {deleted && <div className="notice ok">{t('myDeleted')}</div>}
      <button
        type="button"
        className="btn secondary block"
        onClick={() => {
          if (window.confirm(t('myDeleteConfirm'))) {
            app.clearMyData();
            setDeleted(true);
          }
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

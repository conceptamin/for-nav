// S-12 센터 상담 요청·전송 확인(FR-70), S-13 내 리포트, 병원 이용 안내(정적)

import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { PolicyDisclaimer, SingleSelect, Worse119 } from '../../components/common';
import type { MessageKey } from '../../i18n';
import { useT } from '../../i18n';
import { useApp } from '../../state/AppState';
import { addLiveCase } from '../../state/centerStore';
import type { CenterCase } from '../../domain/centerCase';
import { rateUrgency } from '../../domain/centerCase';
import { INFO_DATE, isAfterHours, nextOpenDay } from '../../domain/coverage';
import type { ContactMethod, RequestType } from '../../domain/templates';
import { buildCenterSummary } from '../../domain/templates';
import { newIntake } from '../../domain/triage';

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
  const [sent, setSent] = useState<CenterCase | null>(null);

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
    const next = nextOpenDay(new Date(sent.createdAt));
    return (
      <div>
        <section className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2.6rem' }} aria-hidden>
            ✅
          </div>
          <h1>{t('cenSentTitle')}</h1>
          <p>{t('cenSentBody')}</p>
          <p className="small muted">
            {t('cenCaseNo')}: <strong>{sent.id}</strong>
          </p>
        </section>
        {sent.afterHours ? (
          <div className="notice warn">
            🌙 {t('cenAfterHours')}{' '}
            <strong>{next.toLocaleDateString(lang === 'vi' ? 'vi-VN' : 'en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}</strong>
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

  const intake = app.intake ?? newIntake(lang);
  const insurance = app.coverage?.input.insurance ?? null;
  const summary = type
    ? buildCenterSummary({
        intake: { ...intake, language: lang },
        emergencyFlag: app.emergencySeen,
        requestType: type,
        coverage: app.coverage?.result ?? null,
        insurance,
        contactMethod: method,
      })
    : null;

  const send = () => {
    if (!type || !summary) return;
    const now = new Date();
    const { urgency, reasons } = rateUrgency({ emergencyFlag: app.emergencySeen, workRelated: intake.workRelated, insurance });
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
    const c: CenterCase = {
      id: `C-${now.getTime().toString().slice(-5)}`,
      createdAt: now.toISOString(),
      language: lang,
      requestType: type,
      urgency,
      urgencyReasons: reasons,
      district: intake.district,
      industry: intake.industry,
      status: 'new',
      summaryKo: summary.ko,
      originalNative: summary.native,
      consentedItems: consented,
      coveragePath: app.coverage?.result.path ?? null,
      contactMethod: method,
      contact: contact.trim() || null,
      afterHours: isAfterHours(now),
      emergencyFlag: app.emergencySeen,
      workRelated: intake.workRelated,
      insurance,
      live: true,
    };
    addLiveCase(c);
    app.addMyCase(c.id);
    setSent(c);
  };

  return (
    <div>
      <h1>{t('cenTitle')}</h1>
      <p className="muted">{t('cenIntro')}</p>
      {!app.intake && <div className="notice info">{t('cenNoIntake')}</div>}
      <section className="card">
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
      </section>

      {summary && (
        <section className="card" style={{ borderTop: '6px solid var(--brand)' }}>
          <h2>{t('cenPreview')}</h2>
          <div className="native-box">{summary.native}</div>
          <p className="footer-note">{t('cenPreviewKo')}</p>
          {app.coverage && <PolicyDisclaimer infoDate={INFO_DATE} />}
        </section>
      )}

      <label className="check" style={{ marginBottom: 12 }}>
        <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
        <span>{t('cenConsent')}</span>
      </label>
      <button type="button" className="btn block big" disabled={!type || !agreed} onClick={send}>
        📨 {t('cenSend')}
      </button>
      <p className="footer-note">{t('cenHoursNote')}</p>
      <Worse119 />
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-13 내 리포트(P2): 기기에만 저장된 기록을 보여 주고 삭제할 수 있다.
// ---------------------------------------------------------------------------
export function MyPage() {
  const app = useApp();
  const { t } = useT();
  const [deleted, setDeleted] = useState(false);
  return (
    <div>
      <h1>{t('myTitle')}</h1>
      {app.mode !== 'member' && <div className="notice warn">{t('repSavedGuest')}</div>}
      <section className="card">
        {app.reports.length === 0 ? (
          <p className="muted">{t('myEmpty')}</p>
        ) : (
          <div className="stack" style={{ gap: 8 }}>
            {app.reports.map((r) => (
              <Link key={r.id} to={`/report/${r.id}`} className="row" style={{ justifyContent: 'space-between', textDecoration: 'none', color: 'inherit', minHeight: 44 }}>
                <span>
                  🩺 {new Date(r.createdAt).toLocaleString(r.language === 'vi' ? 'vi-VN' : 'en-GB')}
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

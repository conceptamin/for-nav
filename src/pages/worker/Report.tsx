// S-11 의료진용 리포트: 항목 선택(기본값 모두 포함) → 동의 → 리포트(/report/:id)
// 한국어·모국어 두 벌을 미리 만들어 두어 토글 전환이 즉시 된다.

import { useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router';
import { toggleIn, Worse119 } from '../../components/common';
import type { MessageKey } from '../../i18n';
import { useT } from '../../i18n';
import { useApp } from '../../state/AppState';
import type { ReportField } from '../../domain/templates';
import { buildClinicianReport, REPORT_FIELDS } from '../../domain/templates';

export function ReportBuilderPage() {
  const app = useApp();
  const { t } = useT();
  const navigate = useNavigate();
  const [included, setIncluded] = useState<ReportField[]>([...REPORT_FIELDS]);
  const [meds, setMeds] = useState('');
  const [agreed, setAgreed] = useState(false);

  if (!app.intake || !app.triage) return <Navigate to="/intake" replace />;
  const intake = app.intake;

  // 내용이 없는 항목은 목록에서 뺀다.
  const available = REPORT_FIELDS.filter((f) => {
    if (f === 'onset') return Boolean(intake.onset);
    if (f === 'circumstance') return Boolean(intake.workRelated || intake.workType || intake.industry);
    if (f === 'note') return Boolean(intake.freeText);
    if (f === 'baseline') return Boolean(app.profile);
    return true;
  });

  const make = () => {
    const report = buildClinicianReport(intake, included.filter((f) => available.includes(f)), app.profile, meds.trim());
    app.saveReport(report);
    navigate(`/report/${report.id}`);
  };

  return (
    <div>
      <h1>{t('repTitle')}</h1>
      <section className="card">
        <h2>{t('repChoose')}</h2>
        <p className="small muted">{t('repChooseHint')}</p>
        <div className="stack" style={{ gap: 8 }}>
          {available.map((f) => (
            <label key={f} className="check">
              <input type="checkbox" checked={included.includes(f)} onChange={() => setIncluded(toggleIn(included, f))} />
              <span>{t(`field.${f}` as MessageKey)}</span>
            </label>
          ))}
        </div>
        {!app.profile && <p className="footer-note">{t('repNoProfile')}</p>}
        {included.includes('meds') && (
          <div className="field" style={{ marginTop: 12 }}>
            <label htmlFor="meds">
              {t('repMeds')} <span className="small muted">({t('optional')})</span>
            </label>
            <input id="meds" type="text" value={meds} placeholder={t('repMedsPh')} onChange={(e) => setMeds(e.target.value)} />
          </div>
        )}
      </section>
      <label className="check" style={{ marginBottom: 12 }}>
        <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
        <span>{t('repConsent')}</span>
      </label>
      <button type="button" className="btn block big" disabled={!agreed || included.length === 0} onClick={make}>
        {t('repMakeBtn')}
      </button>
    </div>
  );
}

export function ReportViewPage() {
  const app = useApp();
  const { t } = useT();
  const { id } = useParams();
  const [showKo, setShowKo] = useState(true);
  const report = app.reports.find((r) => r.id === id);

  if (!report) {
    return (
      <div>
        <div className="notice warn">{t('repNotFound')}</div>
        <Link className="btn block" to="/report/new">
          {t('repMakeBtn')}
        </Link>
      </div>
    );
  }

  const nativeLabel = report.language === 'vi' ? 'Tiếng Việt' : 'English';
  return (
    <div>
      <div className="toggle" role="group" style={{ marginBottom: 12 }}>
        <button type="button" aria-pressed={showKo} onClick={() => setShowKo(true)}>
          {t('repToggleKo')}
        </button>
        <button type="button" aria-pressed={!showKo} onClick={() => setShowKo(false)}>
          {nativeLabel}
        </button>
      </div>
      <section className="card" style={{ borderTop: '6px solid var(--brand)' }} lang={showKo ? 'ko' : report.language}>
        <h1 style={{ fontSize: '1.3rem' }}>{showKo ? '외국인 근로자 증상 메모 (의료진용)' : t('repTitle')}</h1>
        <p className="small muted">
          {showKo ? '환자가 직접 입력한 내용입니다. 진단이 아닙니다.' : t('repNoDiag')}
        </p>
        {report.rows.map((row) => (
          <div className="report-row" key={row.field}>
            <div className="lbl">{showKo ? row.labelKo : row.labelNative}</div>
            <div className="val">{showKo ? row.valueKo : row.valueNative}</div>
          </div>
        ))}
        <p className="footer-note">
          {showKo ? `작성 ${new Date(report.createdAt).toLocaleString('ko-KR')} · 사용 언어: ${report.language === 'vi' ? '베트남어' : '영어'}` : new Date(report.createdAt).toLocaleString(report.language === 'vi' ? 'vi-VN' : 'en-GB')}
        </p>
      </section>
      <p className="small muted">👩‍⚕️ {t('repShowDoctor')}</p>
      <div className={app.mode === 'member' ? 'notice ok' : 'notice warn'}>
        {app.mode === 'member' ? `✓ ${t('repSaved')}` : t('repSavedGuest')}
      </div>
      <Worse119 />
      <Link className="btn secondary block" to="/result">
        {t('back')}
      </Link>
    </div>
  );
}

// S-11 의료진용 리포트: 항목 선택(기본값 모두 포함) → 동의 → 리포트(/report/:id)
// 한국어·모국어 두 벌을 미리 만들어 두어 토글 전환이 즉시 된다.
// 리포트는 버튼을 누를 때 api/worker.ts가 만든다. 기다리는 동안 버튼만 막는다 (README.md "비동기 UX 규칙").

import { useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router';
import { toggleIn, Worse119 } from '../../components/common';
import { useScreenBar } from '../../components/WorkerLayout';
import type { MessageKey } from '../../i18n';
import { LANGUAGE_OPTIONS, useT } from '../../i18n';
import { useApp } from '../../state/AppState';
import { buildClinicianReport } from '../../api/worker';
import type { ReportField } from '../../domain/templates';
import { REPORT_FIELDS } from '../../domain/templates';
import { LANGUAGE_NAMES_KO, LOCALES } from '../../domain/vocab';

export function ReportBuilderPage() {
  const app = useApp();
  const { t } = useT();
  const navigate = useNavigate();
  const [included, setIncluded] = useState<ReportField[]>([...REPORT_FIELDS]);
  const [meds, setMeds] = useState('');
  const [agreed, setAgreed] = useState(false);
  /** 서버 응답을 기다리는 중. 만들기 버튼을 막아 리포트가 두 번 만들어지지 않게 한다 */
  const [busy, setBusy] = useState(false);
  // ← 는 리포트 보기의 되돌아가기와 같이 결과로 간다
  useScreenBar({ title: t('repTitle'), onBack: () => navigate('/result') });

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

  const make = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const report = await buildClinicianReport(intake, included.filter((f) => available.includes(f)), app.profile, meds.trim());
      app.saveReport(report);
      navigate(`/report/${report.id}`);
    } finally {
      setBusy(false);
    }
  };

  // 입력 화면 골격(backlog 08·17): h1 → 항목 고르기 → 동의 → 바닥에 붙은 만들기 버튼 하나
  return (
    <div className="w-screen">
      <h1>{t('repTitle')}</h1>
      <h2>{t('repChoose')}</h2>
      <p className="small muted">{t('repChooseHint')}</p>
      <div className="stack">
        {available.map((f) => (
          <label key={f} className="check">
            <input type="checkbox" checked={included.includes(f)} onChange={() => setIncluded(toggleIn(included, f))} />
            <span>{t(`field.${f}` as MessageKey)}</span>
          </label>
        ))}
        {included.includes('meds') && (
          <div className="field">
            <label htmlFor="meds">
              {t('repMeds')} <span className="small muted">({t('optional')})</span>
            </label>
            <input id="meds" type="text" value={meds} placeholder={t('repMedsPh')} onChange={(e) => setMeds(e.target.value)} />
          </div>
        )}
      </div>
      {!app.profile && <p className="footer-note">{t('repNoProfile')}</p>}
      <hr className="divider" />
      <div className="stack">
        <label className="check">
          <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
          <span>{t('repConsent')}</span>
        </label>
        <Worse119 />
      </div>
      <footer className="w-footer">
        <button type="button" className="btn block" disabled={busy || !agreed || included.length === 0} onClick={make}>
          {t('repMakeBtn')}
        </button>
      </footer>
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

  const nativeLabel = LANGUAGE_OPTIONS.find((o) => o.lang === report.language)?.native ?? report.language;
  // 한국어로 작성한 리포트는 두 벌이 같으므로 토글을 보이지 않는다.
  const bilingual = report.language !== 'ko';
  return (
    <div>
      {bilingual && (
        <div className="toggle" role="group" style={{ marginBottom: 12 }}>
          <button type="button" aria-pressed={showKo} onClick={() => setShowKo(true)}>
            {t('repToggleKo')}
          </button>
          <button type="button" aria-pressed={!showKo} onClick={() => setShowKo(false)}>
            {nativeLabel}
          </button>
        </div>
      )}
      <section className="card band" lang={showKo ? 'ko' : report.language}>
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
          {showKo ? `작성 ${new Date(report.createdAt).toLocaleString('ko-KR')} · 사용 언어: ${LANGUAGE_NAMES_KO[report.language]}` : new Date(report.createdAt).toLocaleString(LOCALES[report.language])}
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

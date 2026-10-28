// S-05 증상 입력 → S-06 응급 안내 / S-07 진료 안내
// 단계마다 응급 감지를 돌려, 응급이면 남은 질문 없이 바로 119 화면으로 보낸다.
// 추출과 최종 판정은 src/api/worker.ts를 거친다(단독/API 모드와 대체는 그 안에만 있다).
// 서버를 기다리는 동안은 버튼만 비활성으로 둔다(design.md "로딩과 실패를 그리는 법").

import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router';
import { Chip, kakaoSearchUrl, SingleSelect, toggleIn, Worse119, YesNoSeg } from '../../components/common';
import { useT } from '../../i18n';
import { useApp } from '../../state/AppState';
import { checkTriage, extract, screenEmergency } from '../../api/worker';
import type { ExtractResult, Intake, TriageResult } from '../../domain/triage';
import { newIntake, REASON_KO } from '../../domain/triage';
import type { AgeGroup, BodyPart, Industry, Onset, Sex, Symptom, WorkType } from '../../domain/vocab';
import { AGE_GROUPS, BODY_PARTS, DEPARTMENTS, DISTRICTS, INDUSTRIES, LANGUAGE_NAMES_KO, ONSETS, pron, SEXES, SYMPTOMS, WORK_TYPES } from '../../domain/vocab';
import type { District } from '../../domain/vocab';

const STEP_COUNT = 4;
const PAIN_SCORES = Array.from({ length: 11 }, (_, i) => i);

export function IntakePage() {
  const app = useApp();
  const { t, term, lang } = useT();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [intake, setIntake] = useState<Intake>(() => newIntake(lang));
  const [missingMsg, setMissingMsg] = useState(false);
  const [extracted, setExtracted] = useState(false);
  /** 서버 응답을 기다리는 중. 다음·이전 버튼을 막아 두 번 눌리지 않게 한다 */
  const [busy, setBusy] = useState(false);

  /** 응급이면 저장 후 119 화면으로 이동하고 true를 돌려준다. 브라우저 규칙만 쓰므로 기다리지 않는다. */
  const checkEmergency = (draft: Intake): boolean => {
    const r = screenEmergency(draft);
    if (r.emergency) {
      app.setIntake(draft);
      app.setTriage(r);
      navigate('/emergency', { replace: true });
      return true;
    }
    return false;
  };

  const goNext = async () => {
    if (busy) return;
    setMissingMsg(false);
    if (step === 1 && checkEmergency(intake)) return;
    if (step === 2) {
      let out: ExtractResult;
      setBusy(true);
      try {
        out = await extract({ ...intake, language: lang });
      } finally {
        setBusy(false);
      }
      const merged = out.intake;
      setExtracted(out.filled);
      setIntake(merged);
      if (checkEmergency(merged)) return;
      // 필수 항목(부위·증상)이 비면 해당 버튼 질문으로 되돌아간다.
      if (!merged.bodyParts.length || !merged.symptoms.length) {
        setMissingMsg(true);
        setStep(merged.bodyParts.length ? 1 : 0);
        return;
      }
    }
    if (step === 3) {
      const final = { ...intake, language: lang };
      let r: TriageResult;
      setBusy(true);
      try {
        r = await checkTriage(final);
      } finally {
        setBusy(false);
      }
      app.setIntake(final);
      app.setTriage(r);
      navigate(r.emergency ? '/emergency' : '/result');
      return;
    }
    setStep(step + 1);
  };

  const set = (p: Partial<Intake>) => setIntake((i) => ({ ...i, ...p }));

  return (
    <div>
      <h1>{t('intakeTitle')}</h1>
      <div className="steps" aria-hidden>
        {Array.from({ length: STEP_COUNT }, (_, i) => (
          <span key={i} className={i <= step ? 'on' : undefined} />
        ))}
      </div>
      {missingMsg && <div className="notice warn">{t('missingAsk')}</div>}

      {step === 0 && (
        <section className="card">
          <h2>{t('stepBody')}</h2>
          <p className="small muted">{t('stepBodyHint')}</p>
          <div className="chips">
            {(Object.keys(BODY_PARTS) as BodyPart[]).map((k) => (
              <Chip key={k} pressed={intake.bodyParts.includes(k)} onClick={() => set({ bodyParts: toggleIn(intake.bodyParts, k) })}>
                {term(BODY_PARTS[k])}
              </Chip>
            ))}
          </div>
        </section>
      )}

      {step === 1 && (
        <section className="card">
          <h2>{t('stepSymptom')}</h2>
          <p className="small muted">{t('stepBodyHint')}</p>
          <div className="chips">
            {(Object.keys(SYMPTOMS) as Symptom[]).map((k) => (
              <Chip key={k} pressed={intake.symptoms.includes(k)} onClick={() => set({ symptoms: toggleIn(intake.symptoms, k) })}>
                {term(SYMPTOMS[k])}
              </Chip>
            ))}
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="card">
          <h2>{t('stepText')}</h2>
          <p className="small muted">{t('stepTextHint')}</p>
          <textarea
            aria-label={t('stepText')}
            placeholder={t('stepTextPlaceholder')}
            value={intake.freeText}
            maxLength={500}
            onChange={(e) => set({ freeText: e.target.value })}
          />
        </section>
      )}

      {step === 3 && (
        <section className="card">
          <h2>{t('stepMore')}</h2>
          {extracted && <div className="notice info">✨ {t('extractedNote')}</div>}
          <div className="field">
            <span className="label">{t('onsetQ')}</span>
            <SingleSelect options={Object.keys(ONSETS) as Onset[]} value={intake.onset} onChange={(v) => set({ onset: v })} label={(k) => term(ONSETS[k])} />
          </div>
          {/* 통증 점수·손상 여부·나이대·성별은 응급도 모델 입력이다. 답하지 않으면 키가 없다. */}
          <div className="field">
            <label htmlFor="pain">{t('painQ')}</label>
            <select
              id="pain"
              className="input"
              value={intake.painScore ?? ''}
              onChange={(e) => set({ painScore: Number(e.target.value) })}
            >
              <option value="" disabled>
                —
              </option>
              {PAIN_SCORES.map((n) => (
                <option key={n} value={n}>
                  {n === 0 ? `0 · ${t('painNone')}` : n === 10 ? `10 · ${t('painWorst')}` : n}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <span className="label">{t('injuryQ')}</span>
            <YesNoSeg
              withUnknown={false}
              value={intake.injury === undefined ? null : intake.injury ? 'yes' : 'no'}
              onChange={(v) => set({ injury: v === 'yes' })}
            />
          </div>
          <div className="field">
            <span className="label">{t('workQ')}</span>
            <YesNoSeg value={intake.workRelated} onChange={(v) => set({ workRelated: v })} />
          </div>
          {intake.workRelated === 'yes' && (
            <div className="field">
              <span className="label">
                {t('workTypeQ')} <span className="small muted">({t('optional')})</span>
              </span>
              <SingleSelect options={Object.keys(WORK_TYPES) as WorkType[]} value={intake.workType} onChange={(v) => set({ workType: v })} label={(k) => term(WORK_TYPES[k])} />
            </div>
          )}
          <div className="field">
            <span className="label">{t('ageGroupQ')}</span>
            <SingleSelect options={Object.keys(AGE_GROUPS) as AgeGroup[]} value={intake.ageGroup ?? null} onChange={(v) => set({ ageGroup: v })} label={(k) => term(AGE_GROUPS[k])} />
          </div>
          <div className="field">
            <span className="label">{t('sex')}</span>
            <SingleSelect options={Object.keys(SEXES) as Sex[]} value={intake.sex ?? null} onChange={(v) => set({ sex: v })} label={(k) => term(SEXES[k])} />
          </div>
          <div className="field">
            <span className="label">{t('industryQ')}</span>
            <SingleSelect options={Object.keys(INDUSTRIES) as Industry[]} value={intake.industry} onChange={(v) => set({ industry: v })} label={(k) => term(INDUSTRIES[k])} />
          </div>
          <div className="field">
            <span className="label">{t('districtQ')}</span>
            <SingleSelect
              options={Object.keys(DISTRICTS) as District[]}
              value={intake.district}
              onChange={(v) => set({ district: v })}
              label={(k) => `${DISTRICTS[k].ko} · ${term(DISTRICTS[k])}`}
            />
          </div>
        </section>
      )}

      <div className="row" style={{ flexWrap: 'nowrap' }}>
        <button
          type="button"
          className="btn secondary"
          disabled={busy}
          onClick={() => (step === 0 ? navigate('/home') : setStep(step - 1))}
        >
          {t('back')}
        </button>
        <button type="button" className="btn block" disabled={busy} onClick={() => void goNext()}>
          {step === 3 ? t('seeResult') : step === 2 && !intake.freeText ? t('skip') : t('next')}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-06 응급 안내: 지도 없이 119 전화와 한국어 위치·상황 문장만 보인다.
// ---------------------------------------------------------------------------
export function EmergencyPage() {
  const app = useApp();
  const { t, lang } = useT();
  const navigate = useNavigate();
  const intake = app.intake;
  const reasons = app.triage?.reasons ?? [];

  const where = intake?.district ? `울산 ${DISTRICTS[intake.district].ko}` : '울산';
  const what = reasons.length ? reasons.map((r) => REASON_KO[r]).join(', ') : '응급 상황';
  // 한국어 사용자는 통역 요청 문장을 붙이지 않는다.
  const interpret = lang === 'ko' ? '' : ` 저는 한국어를 잘 못합니다. ${LANGUAGE_NAMES_KO[lang]} 통역을 부탁합니다.`;
  const koSentence = `응급 환자가 있습니다. 위치는 ${where}입니다. 증상은 ${what}입니다.${interpret}`;

  return (
    <div>
      <section className="em-hero" role="alert">
        <h1>🚨 {t('emTitle')}</h1>
        <p>{t('emBody')}</p>
        <a className="em-call" href="tel:119">
          📞 {t('call119')}
        </a>
      </section>
      <section className="card">
        <h2>{t('emShowKo')}</h2>
        <p className="ko-big" lang="ko">
          {koSentence}
        </p>
        <p className="small muted">{t('emLocationHint')}</p>
      </section>
      <div className="notice info">🗣️ {t('emInterpret')}</div>
      {reasons.length > 0 && (
        <section className="card">
          <h3>{t('emReasons')}</h3>
          <ul style={{ margin: 0, paddingLeft: 20 }} lang="ko">
            {reasons.map((r) => (
              <li key={r}>{REASON_KO[r]}</li>
            ))}
          </ul>
          <p className="footer-note">{t('emRuleNote')}</p>
        </section>
      )}
      <button type="button" className="btn ghost block" onClick={() => navigate('/home')}>
        {t('home')}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-07 진료 안내
// ---------------------------------------------------------------------------
export function ResultPage() {
  const app = useApp();
  const { t, term, lang } = useT();
  const navigate = useNavigate();
  const tri = app.triage;
  if (!app.intake || !tri) return <Navigate to="/intake" replace />;
  // 응급 판정이면 지도 화면을 띄우지 않는다.
  if (tri.emergency) return <Navigate to="/emergency" replace />;
  if (!tri.department) return <Navigate to="/intake" replace />;

  const primary = DEPARTMENTS[tri.department.primary];
  const alt = DEPARTMENTS[tri.department.alt];

  return (
    <div>
      <Worse119 />
      <h1>{t('resultTitle')}</h1>
      <div className="stack" style={{ marginBottom: 12 }}>
        <div className="dept">
          <div className="small muted">{t('resultFirst')}</div>
          <div className="ko" lang="ko">
            {primary.ko}
          </div>
          {lang !== 'ko' && (
            <div>
              <strong>{term(primary)}</strong> <span className="muted small">· {pron(primary, lang)}</span>
            </div>
          )}
          <a className="btn block" style={{ marginTop: 10 }} href={kakaoSearchUrl(primary.ko)} target="_blank" rel="noreferrer">
            🗺️ {t('mapDept')} — {primary.ko}
          </a>
        </div>
        <div className="dept alt">
          <div className="small muted">{t('resultAlt')}</div>
          <div className="ko" lang="ko">
            {alt.ko} {lang !== 'ko' && <span className="small muted">· {term(alt)}</span>}
          </div>
          <a className="btn secondary block" style={{ marginTop: 8 }} href={kakaoSearchUrl(alt.ko)} target="_blank" rel="noreferrer">
            🗺️ {t('mapDept')} — {alt.ko}
          </a>
        </div>
      </div>
      <div className="row" style={{ flexWrap: 'nowrap', marginBottom: 8 }}>
        <a className="btn secondary block" href={kakaoSearchUrl('약국')} target="_blank" rel="noreferrer">
          💊 {t('mapPharmacy')}
        </a>
        <a className="btn secondary block" href={kakaoSearchUrl('응급실')} target="_blank" rel="noreferrer">
          🚑 {t('mapEr')}
        </a>
      </div>
      <div className="notice warn">
        ☎️ {t('mapNotice')}
        <div className="small">{t('mapOpens')}</div>
      </div>
      <div className="stack">
        <Link className="btn block" to="/visit/call">
          📞 {t('toCall')}
        </Link>
        <Link className="btn block" to="/visit/desk">
          🪪 {t('toDesk')}
        </Link>
        <Link className="btn block" to="/report/new">
          🩺 {t('toReport')}
        </Link>
        <Link className="btn secondary block" to="/coverage">
          💳 {t('toCoverage')}
        </Link>
        <Link className="btn secondary block" to="/center-request">
          🤝 {t('toCenter')}
        </Link>
      </div>
      <p className="footer-note">ⓘ {t('resultNoDiag')}</p>
      <button
        type="button"
        className="btn ghost block"
        onClick={() => {
          app.setIntake(null);
          app.setTriage(null);
          navigate('/intake');
        }}
      >
        ↺ {t('newIntake')}
      </button>
    </div>
  );
}

// S-05 증상 입력 → S-06 응급 안내 / S-07 진료 안내
// 묶음(부위·증상·자유 입력·추가 질문) 네 개 중 추가 질문 묶음은 화면 하나에 질문 하나다. 진행 표시는 묶음이 아니라
// 실제로 지나갈 화면 수로 센다(backlog 35). 하나만 고르는 질문은 고르면 바로 다음 화면으로 가고, 프로필로 채운 질문은 묻지 않는다.
// 단계마다 응급 감지를 돌려, 응급이면 남은 질문 없이 바로 119 화면으로 보낸다.
// 추출과 최종 판정은 src/api/worker.ts를 거친다(단독/API 모드와 대체는 그 안에만 있다).
// 서버를 기다리는 동안 추출은 버튼만 비활성이고, 최종 판정은 분석 중 화면을 보인다 (README.md "비동기 UX 규칙").

import { useEffect, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router';
import {
  Chip,
  kakaoSearchUrl,
  PainRange,
  PhotoPicker,
  Progress,
  SingleSelect,
  toggleIn,
  usePhotoCleanup,
  Worse119,
  YesNoSeg,
  type PhotoItem,
} from '../../components/common';
import { useScreenBar } from '../../components/WorkerLayout';
import { useT, type MessageKey } from '../../i18n';
import { useApp } from '../../state/AppState';
import { checkTriage, extract, screenEmergency, usedKeywordFallback } from '../../api/worker';
import type { ExtractResult, Intake, TriageResult } from '../../domain/triage';
import { newIntake, profileAnswers, REASON_KO } from '../../domain/triage';
import type { AgeGroup, BodyPart, Industry, Onset, Sex, Symptom, WorkType } from '../../domain/vocab';
import { AGE_GROUPS, BODY_PARTS, DEPARTMENTS, DISTRICTS, INDUSTRIES, LANGUAGE_NAMES_KO, ONSETS, pron, SEXES, SYMPTOMS, WORK_TYPES } from '../../domain/vocab';
import type { District } from '../../domain/vocab';

/** 묶음: 0 부위 · 1 증상 · 2 자유 입력(사진) · 3 추가 질문. 추가 질문 앞의 화면 수 */
const SCREENS_BEFORE_QUESTIONS = 3;

/** 추가 질문 순서. 업무 종류는 업무 관련이 "예"일 때만, 나이대·성별은 프로필로 채우지 못했을 때만 묻는다 */
type MoreQuestion = 'onset' | 'pain' | 'injury' | 'work' | 'workType' | 'ageGroup' | 'sex' | 'industry' | 'district';
const MORE_QUESTIONS: MoreQuestion[] = ['onset', 'pain', 'injury', 'work', 'workType', 'ageGroup', 'sex', 'industry', 'district'];

/** 칩 묶음. 화면의 표시 순서일 뿐이고 vocab의 열거값·순서는 그대로다 */
const BODY_GROUPS: { title: MessageKey; keys: BodyPart[] }[] = [
  { title: 'groupHead', keys: ['head', 'eye', 'ent', 'teeth'] },
  { title: 'groupTrunk', keys: ['chest', 'abdomen', 'back'] },
  { title: 'groupLimbs', keys: ['arm', 'hand', 'leg', 'foot'] },
  { title: 'groupOther', keys: ['skin', 'whole'] },
];
const SYMPTOM_GROUPS: { title: MessageKey; keys: Symptom[] }[] = [
  { title: 'groupInjury', keys: ['pain', 'swelling', 'cut', 'bleeding', 'burn', 'numb', 'cantmove'] },
  { title: 'groupIllness', keys: ['fever', 'cough', 'dizzy', 'rash', 'nausea', 'breath'] },
  { title: 'groupExposure', keys: ['chemical', 'foreign'] },
];

export function IntakePage() {
  const app = useApp();
  const { t, term, lang } = useT();
  const navigate = useNavigate();
  const [group, setGroup] = useState(0);
  /** 추가 질문 묶음 안의 질문 번호 */
  const [q, setQ] = useState(0);
  const [intake, setIntake] = useState<Intake>(() => newIntake(lang));
  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  usePhotoCleanup(photos);
  const [missingMsg, setMissingMsg] = useState(false);
  const [extracted, setExtracted] = useState(false);
  /** API 모드에서 LLM 대신 키워드 사전으로 채웠는지(README "경로별 대체 정책") */
  const [keywordFallback, setKeywordFallback] = useState(false);
  /** 서버 응답을 기다리는 중. 다음 버튼을 막아 두 번 눌리지 않게 한다 */
  const [busy, setBusy] = useState(false);
  /** 최종 판정을 기다리는 중. 분석 중 화면을 보인다 */
  const [analyzing, setAnalyzing] = useState(false);
  /** 지금 프로필로 채운 나이대·성별. 최종 판정에만 붙이고(추출에는 보내지 않는다), 채운 질문은 묻지 않는다 */
  const [fromProfile] = useState(() => profileAnswers(app.profile, new Date()));

  const questionsFor = (i: Intake) =>
    MORE_QUESTIONS.filter((k) => (k !== 'workType' || i.workRelated === 'yes') && !(k in fromProfile));
  const questions = questionsFor(intake);
  const current: MoreQuestion | null = group === 3 ? questions[Math.min(q, questions.length - 1)] : null;
  const lastQuestion = group === 3 && q >= questions.length - 1;
  const screen = group < 3 ? group + 1 : SCREENS_BEFORE_QUESTIONS + Math.min(q, questions.length - 1) + 1;
  const screens = SCREENS_BEFORE_QUESTIONS + questions.length;

  // 질문이 바뀌면 맨 위부터 보이게 한다(경로는 그대로라 WorkerLayout이 올리지 않는다).
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [group, q]);

  useScreenBar({
    title: t('intakeTitle'),
    hidden: analyzing,
    onBack: () => {
      if (busy) return;
      setMissingMsg(false);
      if (group === 3 && q > 0) setQ(q - 1);
      else if (group === 0) navigate('/home');
      else {
        setGroup(group - 1);
        setQ(0);
      }
    },
  });

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

  /** 다음 화면. `answer`는 하나만 고르는 질문에서 방금 고른 값이다(상태가 바뀌기 전에 넘어가므로 함께 받는다) */
  const goNext = async (answer?: Partial<Intake>) => {
    if (busy) return;
    const cur = answer ? { ...intake, ...answer } : intake;
    if (answer) setIntake(cur);
    setMissingMsg(false);
    if (group === 1 && checkEmergency(cur)) return;
    if (group === 2) {
      let out: ExtractResult;
      setBusy(true);
      try {
        out = await extract({ ...cur, language: lang });
      } finally {
        setBusy(false);
      }
      const merged = out.intake;
      setExtracted(out.filled);
      setKeywordFallback(usedKeywordFallback(out, cur.freeText));
      setIntake(merged);
      if (checkEmergency(merged)) return;
      // 필수 항목(부위·증상)이 비면 해당 버튼 질문으로 되돌아간다.
      if (!merged.bodyParts.length || !merged.symptoms.length) {
        setMissingMsg(true);
        setGroup(merged.bodyParts.length ? 1 : 0);
        return;
      }
    }
    if (group === 3) {
      if (q < questionsFor(cur).length - 1) {
        setQ(q + 1);
        return;
      }
      const final = { ...cur, ...fromProfile, language: lang };
      // 응급은 브라우저에서 즉시 판정한다. 분석 중 화면을 거치지 않는다.
      if (checkEmergency(final)) return;
      let r: TriageResult;
      setBusy(true);
      setAnalyzing(true);
      try {
        r = await checkTriage(final);
      } catch (e) {
        setAnalyzing(false);
        throw e;
      } finally {
        setBusy(false);
      }
      app.setIntake(final);
      app.setTriage(r);
      navigate(r.emergency ? '/emergency' : '/result');
      return;
    }
    setGroup(group + 1);
    setQ(0);
  };

  const set = (p: Partial<Intake>) => setIntake((i) => ({ ...i, ...p }));
  /** 하나만 고르는 질문: 고르면 바로 다음 화면. 잘못 골랐으면 ←로 돌아와 다시 고른다 */
  const pick = (p: Partial<Intake>) => void goNext(p);

  if (analyzing) {
    return (
      <div className="w-wait" role="status">
        <div className="pic" aria-hidden>
          🔎
        </div>
        <h1>{t('analyzingTitle')}</h1>
        <p className="muted">{t('analyzingSub')}</p>
      </div>
    );
  }

  // 아직 답하지 않은 추가 질문은 바닥 버튼이 "건너뛰기"다(답하지 않으면 키가 없다)
  const unanswered: Record<MoreQuestion, boolean> = {
    onset: intake.onset === null,
    pain: intake.painScore === undefined,
    injury: intake.injury === undefined,
    work: intake.workRelated === null,
    workType: intake.workType === null,
    ageGroup: intake.ageGroup === undefined,
    sex: intake.sex === undefined,
    industry: intake.industry === null,
    district: intake.district === null,
  };
  const skippable = (group === 2 && !intake.freeText) || (current !== null && unanswered[current]);
  const primaryLabel = lastQuestion ? t('seeResult') : skippable ? t('skip') : t('next');

  return (
    <div className="w-screen">
      <Progress current={screen} total={screens} label={t('intakeTitle')} />
      {missingMsg && <div className="notice warn">{t('missingAsk')}</div>}

      {group === 0 && (
        <>
          <h1>{t('stepBody')}</h1>
          <p className="small muted">{t('stepBodyHint')}</p>
          {BODY_GROUPS.map((g) => (
            <section className="chip-group" key={g.title}>
              <h2>{t(g.title)}</h2>
              <div className="chips">
                {g.keys.map((k) => (
                  <Chip key={k} pressed={intake.bodyParts.includes(k)} onClick={() => set({ bodyParts: toggleIn(intake.bodyParts, k) })}>
                    {term(BODY_PARTS[k])}
                  </Chip>
                ))}
              </div>
            </section>
          ))}
        </>
      )}

      {group === 1 && (
        <>
          <h1>{t('stepSymptom')}</h1>
          <p className="small muted">{t('stepSymptomHint')}</p>
          {SYMPTOM_GROUPS.map((g) => (
            <section className="chip-group" key={g.title}>
              <h2>{t(g.title)}</h2>
              <div className="chips">
                {g.keys.map((k) => (
                  <Chip key={k} pressed={intake.symptoms.includes(k)} onClick={() => set({ symptoms: toggleIn(intake.symptoms, k) })}>
                    {term(SYMPTOMS[k])}
                  </Chip>
                ))}
              </div>
            </section>
          ))}
        </>
      )}

      {group === 2 && (
        <>
          <h1>{t('stepText')}</h1>
          <p className="small muted">{t('stepTextHint')}</p>
          <PhotoPicker photos={photos} onChange={setPhotos} />
          <div className="field">
            <textarea
              aria-label={t('stepText')}
              placeholder={t('stepTextPlaceholder')}
              value={intake.freeText}
              maxLength={500}
              onChange={(e) => set({ freeText: e.target.value })}
            />
          </div>
        </>
      )}

      {group === 3 && (
        <>
          {/* 대체 알림은 같은 안내 상자 안의 한 줄로 둔다(안내 상자를 두 개 연달아 쌓지 않는다) */}
          {extracted && q === 0 && (
            <div className="notice info">
              ✨ {t('extractedNote')}
              {keywordFallback && <div className="small">{t('extractFallback')}</div>}
            </div>
          )}
          {current === 'onset' && (
            <>
              <h1>{t('onsetQ')}</h1>
              <SingleSelect options={Object.keys(ONSETS) as Onset[]} value={intake.onset} onChange={(v) => pick({ onset: v })} label={(k) => term(ONSETS[k])} />
            </>
          )}
          {/* 통증 점수·손상 여부·나이대·성별은 응급도 모델 입력이다. 답하지 않으면 키가 없다. 슬라이더는 움직이는 중이라 자동으로 넘기지 않는다 */}
          {current === 'pain' && (
            <>
              <h1>{t('painQ')}</h1>
              <PainRange value={intake.painScore} onChange={(n) => set({ painScore: n })} />
            </>
          )}
          {current === 'injury' && (
            <>
              <h1>{t('injuryQ')}</h1>
              <YesNoSeg
                withUnknown={false}
                value={intake.injury === undefined ? null : intake.injury ? 'yes' : 'no'}
                onChange={(v) => pick({ injury: v === 'yes' })}
              />
            </>
          )}
          {current === 'work' && (
            <>
              <h1>{t('workQ')}</h1>
              <YesNoSeg value={intake.workRelated} onChange={(v) => pick({ workRelated: v })} />
            </>
          )}
          {current === 'workType' && (
            <>
              <h1>
                {t('workTypeQ')} <span className="small muted">({t('optional')})</span>
              </h1>
              <SingleSelect options={Object.keys(WORK_TYPES) as WorkType[]} value={intake.workType} onChange={(v) => pick({ workType: v })} label={(k) => term(WORK_TYPES[k])} />
            </>
          )}
          {current === 'ageGroup' && (
            <>
              <h1>{t('ageGroupQ')}</h1>
              <SingleSelect options={Object.keys(AGE_GROUPS) as AgeGroup[]} value={intake.ageGroup ?? null} onChange={(v) => pick({ ageGroup: v })} label={(k) => term(AGE_GROUPS[k])} />
            </>
          )}
          {current === 'sex' && (
            <>
              <h1>{t('sex')}</h1>
              <SingleSelect options={Object.keys(SEXES) as Sex[]} value={intake.sex ?? null} onChange={(v) => pick({ sex: v })} label={(k) => term(SEXES[k])} />
            </>
          )}
          {current === 'industry' && (
            <>
              <h1>{t('industryQ')}</h1>
              <SingleSelect options={Object.keys(INDUSTRIES) as Industry[]} value={intake.industry} onChange={(v) => pick({ industry: v })} label={(k) => term(INDUSTRIES[k])} />
            </>
          )}
          {current === 'district' && (
            <>
              <h1>{t('districtQ')}</h1>
              <SingleSelect
                options={Object.keys(DISTRICTS) as District[]}
                value={intake.district}
                onChange={(v) => pick({ district: v })}
                label={(k) => (lang === 'ko' ? DISTRICTS[k].ko : `${DISTRICTS[k].ko} · ${term(DISTRICTS[k])}`)}
              />
            </>
          )}
        </>
      )}

      <footer className="w-footer">
        <button type="button" className="btn block" disabled={busy} onClick={() => void goNext()}>
          {primaryLabel}
        </button>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-06 응급 안내: 지도 없이 119 전화와 한국어 위치·상황 문장만 보인다.
// ---------------------------------------------------------------------------
export function EmergencyPage() {
  const app = useApp();
  const { t, lang } = useT();
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
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-07 진료 안내
// ---------------------------------------------------------------------------
export function ResultPage() {
  const app = useApp();
  const { t, term, lang } = useT();
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
    </div>
  );
}

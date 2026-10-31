// S-05 증상 입력 → S-07 진료 안내
// 묶음(부위·증상·자유 입력·추가 질문) 네 개 중 추가 질문 묶음은 화면 하나에 질문 하나다. 진행 표시는 묶음이 아니라
// 실제로 지나갈 화면 수로 센다(backlog 35). 하나만 고르는 질문은 고르면 바로 다음 화면으로 간다.
// 응급 여부는 판정하지 않는다(backlog 43). 119는 하단 독과 "심해지면 119" 안내로 늘 보인다.
// 추출과 진료과 추천은 src/api/worker.ts를 거친다(단독/API 모드와 대체는 그 안에만 있다).
// 서버를 기다리는 동안 추출은 버튼만 비활성이고, 진료과 추천은 분석 중 화면을 보인다 (README.md "비동기 UX 규칙").

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router';
import {
  Chip,
  kakaoSearchUrl,
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
import { checkTriage, extract, usedKeywordFallback } from '../../api/worker';
import type { ExtractResult, Intake, TriageResult } from '../../domain/triage';
import { newIntake } from '../../domain/triage';
import type { BodyPart, Industry, Onset, Symptom, WorkType } from '../../domain/vocab';
import { BODY_PARTS, DEPARTMENTS, DISTRICTS, INDUSTRIES, ONSETS, pron, SYMPTOMS, WORK_TYPES } from '../../domain/vocab';
import type { District } from '../../domain/vocab';

/** 묶음: 0 부위 · 1 증상 · 2 자유 입력(사진) · 3 추가 질문. 추가 질문 앞의 화면 수 */
const SCREENS_BEFORE_QUESTIONS = 3;

/** 추가 질문 순서. 업무 종류는 업무 관련이 "예"일 때만 묻는다 */
type MoreQuestion = 'onset' | 'injury' | 'work' | 'workType' | 'industry' | 'district';
const MORE_QUESTIONS: MoreQuestion[] = ['onset', 'injury', 'work', 'workType', 'industry', 'district'];

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
  /** 진료과 추천을 기다리는 중. 분석 중 화면을 보인다 */
  const [analyzing, setAnalyzing] = useState(false);

  const questionsFor = (i: Intake) => MORE_QUESTIONS.filter((k) => k !== 'workType' || i.workRelated === 'yes');
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

  /** 다음 화면. `answer`는 하나만 고르는 질문에서 방금 고른 값이다(상태가 바뀌기 전에 넘어가므로 함께 받는다) */
  const goNext = async (answer?: Partial<Intake>) => {
    if (busy) return;
    const cur = answer ? { ...intake, ...answer } : intake;
    if (answer) setIntake(cur);
    setMissingMsg(false);
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
      const final = { ...cur, language: lang };
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
      navigate('/result');
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
    injury: intake.injury === undefined,
    work: intake.workRelated === null,
    workType: intake.workType === null,
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
          {/* 손상 여부는 진료과 모델 B 입력이다. 답하지 않으면 키가 없다 */}
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
// S-07 진료 안내
// ---------------------------------------------------------------------------
export function ResultPage() {
  const app = useApp();
  const { t, term, lang } = useT();
  const tri = app.triage;
  const [afterHoursOpen, setAfterHoursOpen] = useState(false);
  const closeAfterHours = useCallback(() => setAfterHoursOpen(false), []);
  if (!app.intake || !tri) return <Navigate to="/intake" replace />;
  if (!tri.department) return <Navigate to="/intake" replace />;

  const primary = DEPARTMENTS[tri.department.primary];
  const alt = DEPARTMENTS[tri.department.alt];

  // 주 동작은 첫 진료과 지도 하나(브랜드색). 나머지는 홈 기능 목록과 같은 줄로 두 묶음에 담는다(backlog 36).
  // 아이콘은 오래된 기기도 그리는 Unicode 6.0 이모지만 쓴다
  const goItems: ResultItem[] = [
    { ico: '📞', label: t('toCall'), to: '/visit/call' },
    { ico: '📋', label: t('toDesk'), to: '/visit/desk' },
    { ico: '📝', label: t('toReport'), to: '/report/new' },
  ];
  // 보험과 지원·센터 요청은 홈 기능 목록과 하단 채팅에 있어 여기서는 뺀다(2026-10-31 사용자 결정)
  const moreItems: ResultItem[] = [
    { ico: '💊', label: t('mapPharmacy'), href: kakaoSearchUrl('약국') },
    { ico: '🚑', label: t('mapEr'), href: kakaoSearchUrl('응급실') },
    // 밤·휴일 안내는 페이지를 옮기지 않고 화면 위 시트로 연다(backlog 44 after-hours-guide, 2026-10-31 사용자 결정)
    { ico: '🌙', label: t('ahTitle'), sheet: 'after-hours', open: afterHoursOpen, onOpen: () => setAfterHoursOpen(true) },
  ];

  return (
    <div className="stack wide">
      <Worse119 />
      {/* 진단이 아니라는 안내는 맨 아래에서 제목 옆으로 올려 빨간 글씨로 보인다(2026-10-31 사용자 결정) */}
      <div className="result-head">
        <h1>{t('resultTitle')}</h1>
        <p className="result-nodiag">
          <span aria-hidden="true">ⓘ</span>
          <span>{t('resultNoDiag')}</span>
        </p>
      </div>
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
        <p className="dept-note">
          {t('mapNotice')} {t('mapOpens')}
        </p>
      </div>
      <div className="dept alt">
        <div className="small muted">{t('resultAlt')}</div>
        <div className="ko" lang="ko">
          {alt.ko} {lang !== 'ko' && <span className="small muted">· {term(alt)}</span>}
        </div>
        <a className="btn ghost dept-alt-map" href={kakaoSearchUrl(alt.ko)} target="_blank" rel="noreferrer">
          {t('mapDept')} — {alt.ko} ›
        </a>
      </div>
      <ResultGroup title={t('resultGoGroup')} items={goItems} />
      <ResultGroup title={t('resultMoreGroup')} items={moreItems} />
      {afterHoursOpen && <AfterHoursSheet id="after-hours" onClose={closeAfterHours} />}
    </div>
  );
}

type ResultItem = { ico: string; label: string } & (
  | { to: string }
  | { href: string }
  | { sheet: string; open: boolean; onOpen: () => void }
);

/** S-07 묶음 하나: 홈 기능 목록(.home-list)과 같은 줄. 지도는 카카오맵을 새 탭으로, 시트 줄은 화면 위 시트로 연다 */
function ResultGroup({ title, items }: { title: string; items: ResultItem[] }) {
  const row = (it: ResultItem) => (
    <>
      <span className="ico" aria-hidden>
        {it.ico}
      </span>
      <span className="txt">
        <strong>{it.label}</strong>
      </span>
      <span className="chev" aria-hidden>
        ›
      </span>
    </>
  );
  return (
    <section>
      <h2>{title}</h2>
      <nav className="home-list">
        {items.map((it) =>
          'to' in it ? (
            <Link key={it.to} to={it.to}>
              {row(it)}
            </Link>
          ) : 'href' in it ? (
            <a key={it.href} href={it.href} target="_blank" rel="noreferrer">
              {row(it)}
            </a>
          ) : (
            <button
              key={it.sheet}
              type="button"
              aria-haspopup="dialog"
              aria-expanded={it.open}
              aria-controls={it.sheet}
              onClick={it.onOpen}
            >
              {row(it)}
            </button>
          ),
        )}
      </nav>
    </section>
  );
}

/**
 * 밤·휴일 안내 시트. 센터 채팅 시트와 같은 틀(막·머리·✕)이고 높이는 내용만큼이다(.sheet.fit).
 * 열면 시트로 초점을 옮기고 Esc·막·✕로 닫는다. 뒤 화면은 스크롤되지 않게 묶는다. 갈 곳을 고르는 판단은 119에 맡긴다
 */
function AfterHoursSheet({ id, onClose }: { id: string; onClose: () => void }) {
  const { t } = useT();
  const sheet = useRef<HTMLElement>(null);
  useEffect(() => {
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
  }, [onClose]);
  return (
    <>
      <div className="sheet-scrim" onClick={onClose} aria-hidden="true" />
      <section id={id} className="sheet fit" role="dialog" aria-labelledby={`${id}-title`} ref={sheet} tabIndex={-1}>
        <header className="sheet-head">
          <div className="sheet-title">
            <h2 id={`${id}-title`}>🌙 {t('ahTitle')}</h2>
          </div>
          <button type="button" className="sheet-btn" aria-label={t('close')} onClick={onClose}>
            <svg className="sheet-icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </header>
        <div className="sheet-body">
          <p>📞 {t('ah119')}</p>
          <p>🏪 {t('ahStore')}</p>
        </div>
      </section>
    </>
  );
}

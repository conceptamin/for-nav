// S-09 접수 창구용 화면, S-10 전화 스크립트 (예약·접수 도우미)

import { useState } from 'react';
import { Link, Navigate } from 'react-router';
import { Chip, Worse119 } from '../../components/common';
import { useT } from '../../i18n';
import { useApp } from '../../state/AppState';
import type { Line } from '../../domain/templates';
import { buildCallScript, buildDeskSheet } from '../../domain/templates';
import type { Intake } from '../../domain/triage';
import type { Department } from '../../domain/vocab';
import { DEPARTMENTS } from '../../domain/vocab';

function LineView({ line, big = false }: { line: Line; big?: boolean }) {
  const { t } = useT();
  return (
    <div className="line">
      <div className={big ? 'ko-big' : 'ko'} lang="ko">
        {line.ko}
      </div>
      <div className="pron">
        🔊 <span className="small muted">{t('pronunciation')}:</span> {line.pron}
      </div>
      <div className="native">↳ {line.native}</div>
    </div>
  );
}

/** 접수·전화 화면은 비응급 판정과 진료과가 있어야 연다. */
type VisitContext = { redirect: string } | { intake: Intake; dept: Department };

function useVisitContext(): VisitContext {
  const app = useApp();
  const tri = app.triage;
  if (!app.intake || !tri) return { redirect: '/intake' };
  if (tri.emergency) return { redirect: '/emergency' };
  if (!tri.department) return { redirect: '/intake' };
  return { intake: app.intake, dept: tri.department.primary };
}

export function DeskPage() {
  const ctx = useVisitContext();
  const { t, lang } = useT();
  const [firstVisit, setFirstVisit] = useState(true);
  if ('redirect' in ctx) return <Navigate to={ctx.redirect} replace />;
  const sheet = buildDeskSheet(ctx.intake, ctx.dept, firstVisit, lang);

  return (
    <div>
      <h1>{t('deskTitle')}</h1>
      <p className="small muted">{t('deskHint')}</p>
      <div className="field">
        <span className="label">{t('deskFirstQ')}</span>
        <div className="seg">
          <Chip pressed={firstVisit} onClick={() => setFirstVisit(true)}>
            {t('deskFirst')}
          </Chip>
          <Chip pressed={!firstVisit} onClick={() => setFirstVisit(false)}>
            {t('deskRevisit')}
          </Chip>
        </div>
      </div>
      <section className="card" style={{ borderTop: '6px solid var(--brand)' }}>
        <p className="small muted" lang="ko">
          접수 담당자님께 · 외국인 환자 접수 안내
        </p>
        {sheet.lines.map((l) => (
          <LineView key={l.ko} line={l} big />
        ))}
      </section>
      <section className="card">
        <h2 lang="ko">접수 요약 · {t('deskInfo')}</h2>
        <dl className="kv" lang="ko">
          <dt>초진 여부</dt>
          <dd>{sheet.firstVisit ? '초진' : '재진'}</dd>
          <dt>희망 진료과</dt>
          <dd>{DEPARTMENTS[ctx.dept].ko}</dd>
          <dt>업무 중 발생</dt>
          <dd>{sheet.workRelatedKo}</dd>
          <dt>사용 언어</dt>
          <dd>{lang === 'vi' ? '베트남어' : '영어'}</dd>
        </dl>
      </section>
      <section className="card">
        <h2>
          <span lang="ko">필요 서류</span> · {t('deskDocs')}
        </h2>
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          {sheet.docsKo.map((d) => (
            <li key={d.ko}>
              <strong lang="ko">{d.ko}</strong> <span className="muted small">— {d.native}</span>
            </li>
          ))}
        </ul>
      </section>
      <Worse119 />
      <Link className="btn secondary block" to="/report/new">
        🩺 {t('toReport')}
      </Link>
    </div>
  );
}

export function CallPage() {
  const ctx = useVisitContext();
  const { t, lang } = useT();
  const [picked, setPicked] = useState<Record<string, number>>({});
  if ('redirect' in ctx) return <Navigate to={ctx.redirect} replace />;
  const script = buildCallScript(ctx.intake, ctx.dept, lang);

  return (
    <div>
      <h1>{t('callTitle')}</h1>
      <p className="small muted">{t('callHint')}</p>
      <section className="card">
        <h2>🗣️ {t('callSay')}</h2>
        {script.lines.map((l) => (
          <LineView key={l.ko} line={l} />
        ))}
      </section>
      <section className="card">
        <h2>❓ {t('callFaq')}</h2>
        <p className="small muted">{t('callFaqHint')}</p>
        {script.faq
          .filter((f) => f.answers.length > 0)
          .map((f) => {
            const chosen = picked[f.id];
            const answer = chosen !== undefined ? f.answers[chosen] : undefined;
            return (
              <div key={f.id} style={{ padding: '12px 0', borderTop: '1px solid var(--line)' }}>
                <div style={{ fontWeight: 800, fontSize: '1.1rem' }} lang="ko">
                  {f.q.ko}
                </div>
                <div className="small muted">{lang === 'vi' ? f.q.vi : f.q.en}</div>
                <div className="stack" style={{ marginTop: 8, gap: 6 }}>
                  {f.answers.map((a, i) => (
                    <Chip key={a.ko} pressed={chosen === i} onClick={() => setPicked({ ...picked, [f.id]: i })}>
                      {a.native}
                    </Chip>
                  ))}
                </div>
                {answer && (
                  <div className="notice ok" style={{ marginTop: 8, marginBottom: 0 }} aria-live="polite">
                    <div className="small">{t('callAnswer')}</div>
                    <div className="ko-big" lang="ko">
                      {answer.ko}
                    </div>
                    <div className="small">🔊 {answer.pron}</div>
                  </div>
                )}
              </div>
            );
          })}
      </section>
      <div className="notice warn">🏥 {t('callReferral')}</div>
      <Link className="btn block" to="/center-request?type=booking">
        🤝 {t('callNeedHelp')}
      </Link>
      <div style={{ height: 12 }} />
      <Worse119 />
    </div>
  );
}

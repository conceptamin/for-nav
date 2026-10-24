// 센터 영역(PC 우선, 한국어): C-01 사례 접수함, C-02 사례 상세, C-03 통계
// 데모에서는 로그인을 생략한다(PRD 5-2).

import { useMemo, useState } from 'react';
import { Link, NavLink, Outlet, useNavigate, useParams } from 'react-router';
import { buildStatRecords } from '../../data/mock';
import type { CaseStatus, CenterCase, Urgency } from '../../domain/centerCase';
import { STATUS_KO, URGENCY_KO } from '../../domain/centerCase';
import { PATH_KO } from '../../domain/coverage';
import { CONTACT_METHOD_KO, REQUEST_TYPE_KO } from '../../domain/templates';
import type { District, Industry, Lang, YesNoUnknown } from '../../domain/vocab';
import { DISTRICTS, INDUSTRIES, LANGUAGE_NAMES_KO } from '../../domain/vocab';
import { resetCenterDemo, setCaseStatus, useCenterCases } from '../../state/centerStore';

export function CenterLayout() {
  return (
    <div className="c-shell">
      <header className="c-header">
        <span className="brand">울산 외국인주민·근로자 통합지원센터 · 의료지원</span>
        <nav>
          <NavLink to="/center" end>
            사례 접수함
          </NavLink>
          <NavLink to="/center/stats">통계</NavLink>
        </nav>
        <span className="pill low">데모 · 로그인 생략</span>
        <a href="/" target="_blank" rel="noreferrer" className="small">
          근로자 화면 열기 ↗
        </a>
      </header>
      <main className="c-main">
        <Outlet />
      </main>
    </div>
  );
}

const fmt = (iso: string) =>
  new Date(iso).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });

const URGENCY_ORDER: Record<Urgency, number> = { high: 0, medium: 1, low: 2 };

function UrgencyPill({ u }: { u: Urgency }) {
  const mark = { high: '▲▲', medium: '▲', low: '–' }[u];
  return (
    <span className={`pill ${u}`}>
      {mark} {URGENCY_KO[u]}
    </span>
  );
}

function StatusPill({ s }: { s: CaseStatus }) {
  return <span className={`pill ${s}`}>{STATUS_KO[s]}</span>;
}

// ---------------------------------------------------------------------------
// C-01 사례 접수함
// ---------------------------------------------------------------------------
export function InboxPage() {
  const cases = useCenterCases();
  const navigate = useNavigate();
  const [status, setStatus] = useState<CaseStatus | 'all'>('all');
  const [sort, setSort] = useState<'time' | 'urgency'>('time');

  const counts = useMemo(() => {
    const c = { new: 0, progress: 0, done: 0, high: 0 };
    for (const x of cases) {
      c[x.status] += 1;
      if (x.urgency === 'high' && x.status !== 'done') c.high += 1;
    }
    return c;
  }, [cases]);

  const rows = cases
    .filter((c) => status === 'all' || c.status === status)
    .sort((a, b) => {
      // 신규 사례는 항상 맨 위(FR-80 수용 기준)
      if ((a.status === 'new') !== (b.status === 'new')) return a.status === 'new' ? -1 : 1;
      if (sort === 'urgency' && a.urgency !== b.urgency) return URGENCY_ORDER[a.urgency] - URGENCY_ORDER[b.urgency];
      return b.createdAt.localeCompare(a.createdAt);
    });

  return (
    <div>
      <div className="c-grid">
        <div className="kpi">
          <div className="n">{counts.new}</div>
          <div className="l">신규</div>
        </div>
        <div className="kpi">
          <div className="n">{counts.progress}</div>
          <div className="l">진행 중</div>
        </div>
        <div className="kpi">
          <div className="n">{counts.done}</div>
          <div className="l">완료</div>
        </div>
        <div className="kpi">
          <div className="n" style={{ color: 'var(--danger)' }}>
            {counts.high}
          </div>
          <div className="l">긴급도 높음(미완료)</div>
        </div>
      </div>

      <div className="filters">
        {(['all', 'new', 'progress', 'done'] as const).map((s) => (
          <button key={s} type="button" aria-pressed={status === s} onClick={() => setStatus(s)}>
            {s === 'all' ? '전체' : STATUS_KO[s]}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        <label className="small">
          정렬{' '}
          <select value={sort} onChange={(e) => setSort(e.target.value as 'time' | 'urgency')}>
            <option value="time">접수 시각</option>
            <option value="urgency">긴급도</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => {
            if (window.confirm('데모로 전송한 사례와 상태 변경을 모두 지울까요?')) resetCenterDemo();
          }}
        >
          데모 초기화
        </button>
      </div>

      <div className="table-wrap">
        <table className="cases">
          <thead>
            <tr>
              <th>접수 번호</th>
              <th>접수 시각</th>
              <th>언어</th>
              <th>요청 유형</th>
              <th>긴급도</th>
              <th>긴급도 근거</th>
              <th>구·군</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr
                key={c.id}
                className={c.status === 'new' && c.live ? 'fresh' : undefined}
                tabIndex={0}
                onClick={() => navigate(`/center/cases/${c.id}`)}
                onKeyDown={(e) => e.key === 'Enter' && navigate(`/center/cases/${c.id}`)}
              >
                <td>
                  <strong>{c.id}</strong> {c.live && <span className="pill live">실제 전송</span>}
                </td>
                <td>
                  {fmt(c.createdAt)} {c.afterHours && <span title="운영 시간 외 접수">🌙</span>}
                </td>
                <td>{LANGUAGE_NAMES_KO[c.language]}</td>
                <td>{REQUEST_TYPE_KO[c.requestType]}</td>
                <td>
                  <UrgencyPill u={c.urgency} />
                </td>
                <td className="small muted">{c.urgencyReasons.join(', ') || '—'}</td>
                <td>{c.district ? DISTRICTS[c.district].ko : '—'}</td>
                <td>
                  <StatusPill s={c.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="footer-note">
        mock 사례 24건 + 근로자 화면에서 실제 전송한 사례. 같은 브라우저의 다른 탭에서 전송하면 2초 안에 이 목록에 나타납니다. 🌙 = 운영 시간 외 접수
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// C-02 사례 상세
// ---------------------------------------------------------------------------
export function CaseDetailPage() {
  const { id } = useParams();
  const cases = useCenterCases();
  const c = cases.find((x) => x.id === id);
  if (!c) {
    return (
      <div className="panel">
        <p>사례를 찾을 수 없습니다.</p>
        <Link to="/center">← 접수함</Link>
      </div>
    );
  }
  return <CaseDetail c={c} />;
}

function CaseDetail({ c }: { c: CenterCase }) {
  const flow: CaseStatus[] = ['new', 'progress', 'done'];
  const yn = (v: YesNoUnknown | null, map: Record<YesNoUnknown, string>) => (v ? map[v] : '—');
  return (
    <div>
      <div className="row" style={{ marginBottom: 12 }}>
        <Link to="/center">← 접수함</Link>
        <h1 style={{ margin: '0 0 0 8px', fontSize: '1.3rem' }}>사례 {c.id}</h1>
        <UrgencyPill u={c.urgency} />
        <StatusPill s={c.status} />
        {c.live && <span className="pill live">실제 전송</span>}
      </div>
      <div className="detail">
        <div>
          <section className="panel">
            <h2>한국어 사례 요약</h2>
            <p style={{ fontSize: '1.05rem', lineHeight: 1.7 }}>{c.summaryKo}</p>
            <p className="footer-note">근로자 입력과 버튼 응답을 사실 그대로 요약했습니다. 판단·추측은 포함하지 않습니다.</p>
          </section>
          <section className="panel">
            <h2>모국어 원문 ({LANGUAGE_NAMES_KO[c.language]})</h2>
            <div className="native-box" lang={c.language}>
              {c.originalNative}
            </div>
          </section>
          <section className="panel">
            <h2>근로자가 전송에 동의한 항목</h2>
            <div className="row">
              {c.consentedItems.map((i) => (
                <span key={i} className="pill low">
                  {i}
                </span>
              ))}
            </div>
          </section>
        </div>
        <div>
          <section className="panel">
            <h2>상태 변경</h2>
            <div className="row">
              {flow.map((s) => (
                <button
                  key={s}
                  type="button"
                  className={`btn ${c.status === s ? '' : 'secondary'}`}
                  style={{ minHeight: 40, flex: 1 }}
                  aria-pressed={c.status === s}
                  onClick={() => setCaseStatus(c.id, s)}
                >
                  {STATUS_KO[s]}
                </button>
              ))}
            </div>
          </section>
          <section className="panel">
            <h2>사례 정보</h2>
            <dl className="kv">
              <dt>접수 시각</dt>
              <dd>
                {new Date(c.createdAt).toLocaleString('ko-KR')} {c.afterHours && '(운영 시간 외)'}
              </dd>
              <dt>요청 유형</dt>
              <dd>{REQUEST_TYPE_KO[c.requestType]}</dd>
              <dt>긴급도 근거</dt>
              <dd>{c.urgencyReasons.join(', ') || '해당 없음'}</dd>
              <dt>구·군</dt>
              <dd>{c.district ? DISTRICTS[c.district].ko : '—'}</dd>
              <dt>업종</dt>
              <dd>{c.industry ? INDUSTRIES[c.industry].ko : '—'}</dd>
              <dt>업무 중 발생</dt>
              <dd>{yn(c.workRelated, { yes: '예', no: '아니요', unknown: '모름' })}</dd>
              <dt>건강보험증</dt>
              <dd>{yn(c.insurance, { yes: '있음', no: '없음', unknown: '모름' })}</dd>
              <dt>응급 판정 이력</dt>
              <dd>{c.emergencyFlag ? '있음' : '없음'}</dd>
            </dl>
          </section>
          <section className="panel">
            <h2>제도 경로 결과</h2>
            <p style={{ fontWeight: 700 }}>{c.coveragePath ? PATH_KO[c.coveragePath] : '근로자가 확인하지 않음'}</p>
            <p className="footer-note">규칙 기반 "먼저 상담할 곳" 안내이며 지원 여부 판정이 아닙니다.</p>
          </section>
          <section className="panel">
            <h2>연락 희망 방법</h2>
            <dl className="kv">
              <dt>방법</dt>
              <dd>{c.contactMethod ? CONTACT_METHOD_KO[c.contactMethod] : '선택 안 함'}</dd>
              <dt>연락처</dt>
              <dd>{c.contact ?? '미입력'}</dd>
            </dl>
          </section>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// C-03 통계: 익명 집계만 보이고 5건 미만 칸은 숨긴다.
// ---------------------------------------------------------------------------
const MIN_CELL = 5;

function Bars({ data }: { data: { label: string; n: number }[] }) {
  const max = Math.max(...data.map((d) => d.n), 1);
  return (
    <div className="bars">
      {data.map((d) => {
        const hidden = d.n < MIN_CELL;
        return (
          <div className="bar-row" key={d.label}>
            <span>{d.label}</span>
            <div className="bar-track" aria-hidden>
              {!hidden && <div className="bar-fill" style={{ width: `${(d.n / max) * 100}%` }} />}
            </div>
            <span className="num">{hidden ? '<5' : d.n}</span>
          </div>
        );
      })}
    </div>
  );
}

const PIE_COLORS = ['#0f5b78', '#e08a00', '#9aa8b2'];

function Donut({ parts }: { parts: { label: string; n: number }[] }) {
  const total = parts.reduce((s, p) => s + p.n, 0) || 1;
  const r = 52;
  const circ = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="donut-wrap">
      <svg width="140" height="140" viewBox="0 0 140 140" role="img" aria-label="보험 상태 분포">
        <g transform="rotate(-90 70 70)">
          {parts.map((p, i) => {
            const len = (p.n / total) * circ;
            const el = (
              <circle
                key={p.label}
                cx="70"
                cy="70"
                r={r}
                fill="none"
                stroke={PIE_COLORS[i % PIE_COLORS.length]}
                strokeWidth="22"
                strokeDasharray={`${p.n < MIN_CELL ? 0 : len} ${circ}`}
                strokeDashoffset={-offset}
              />
            );
            offset += len;
            return el;
          })}
        </g>
      </svg>
      <div className="legend">
        {parts.map((p, i) => (
          <span key={p.label}>
            <i style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
            {p.label} <strong>{p.n < MIN_CELL ? '<5' : `${p.n}건 (${Math.round((p.n / total) * 100)}%)`}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}

export function StatsPage() {
  const all = useMemo(() => buildStatRecords(), []);
  const [days, setDays] = useState<30 | 90 | 180>(90);
  const [district, setDistrict] = useState<District | 'all'>('all');

  const recs = useMemo(() => {
    const since = Date.now() - days * 86400000;
    return all.filter((r) => r.date.getTime() >= since && (district === 'all' || r.district === district));
  }, [all, days, district]);

  const countBy = <K extends string>(keys: K[], get: (r: (typeof recs)[number]) => K) =>
    keys.map((k) => ({ key: k, n: recs.filter((r) => get(r) === k).length }));

  const byIndustry = countBy(Object.keys(INDUSTRIES) as Industry[], (r) => r.industry).map((x) => ({ label: INDUSTRIES[x.key].ko, n: x.n }));
  const byLang = countBy(['vi', 'en'] as Lang[], (r) => r.language).map((x) => ({ label: LANGUAGE_NAMES_KO[x.key], n: x.n }));
  const byIns = countBy(['yes', 'no', 'unknown'] as YesNoUnknown[], (r) => r.insurance).map((x) => ({
    label: { yes: '있음', no: '없음', unknown: '모름' }[x.key],
    n: x.n,
  }));
  const after = recs.filter((r) => r.afterHours).length;
  const total = recs.length;

  return (
    <div>
      <div className="filters">
        <strong>기간</strong>
        {([30, 90, 180] as const).map((d) => (
          <button key={d} type="button" aria-pressed={days === d} onClick={() => setDays(d)}>
            최근 {d}일
          </button>
        ))}
        <strong style={{ marginLeft: 12 }}>구·군</strong>
        <select value={district} onChange={(e) => setDistrict(e.target.value as District | 'all')}>
          <option value="all">전체</option>
          {(Object.keys(DISTRICTS) as District[]).map((d) => (
            <option key={d} value={d}>
              {DISTRICTS[d].ko}
            </option>
          ))}
        </select>
      </div>

      <div className="c-grid">
        <div className="kpi">
          <div className="n">{total < MIN_CELL ? '<5' : total}</div>
          <div className="l">요청 수</div>
        </div>
        <div className="kpi">
          <div className="n">{total < MIN_CELL ? '—' : `${Math.round((after / total) * 100)}%`}</div>
          <div className="l">운영 시간 외 요청 비율</div>
        </div>
        <div className="kpi">
          <div className="n">{total < MIN_CELL ? '—' : `${Math.round((recs.filter((r) => r.workRelated === 'yes').length / total) * 100)}%`}</div>
          <div className="l">업무 중 발생 비율</div>
        </div>
        <div className="kpi">
          <div className="n">{total < MIN_CELL ? '—' : `${Math.round((recs.filter((r) => r.insurance !== 'yes').length / total) * 100)}%`}</div>
          <div className="l">보험 없음·모름 비율</div>
        </div>
      </div>

      <div className="charts">
        <section className="panel">
          <h2>업종별 요청 수</h2>
          <Bars data={byIndustry} />
        </section>
        <section className="panel">
          <h2>언어별 요청 수</h2>
          <Bars data={byLang} />
        </section>
        <section className="panel">
          <h2>건강보험증 보유 분포</h2>
          <Donut parts={byIns} />
        </section>
        <section className="panel">
          <h2>운영 시간 외 요청 비율</h2>
          <Donut
            parts={[
              { label: '운영 시간 외', n: after },
              { label: '운영 시간 내', n: total - after },
            ]}
          />
          <p className="footer-note">운영 시간 가정: 평일 09:00~18:00 (센터 확인 후 설정값으로 변경)</p>
        </section>
      </div>
      <p className="footer-note">
        데모 mock 익명 집계입니다. 개인 단위 기록은 제공하지 않으며 5건 미만인 칸은 "&lt;5"로 숨깁니다. 울산시 담당자는 같은 화면을 읽기 전용으로 사용합니다(실서비스).
      </p>
    </div>
  );
}

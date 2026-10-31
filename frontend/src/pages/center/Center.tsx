// 센터 영역(PC 우선, 한국어): C-01 사례 접수함, C-02 사례 상세, C-03 통계
// 서버가 센터 로그인을 쓰면(backend 17) 들어올 때 세션을 확인하고, 없거나 중간에 끝나면 C-00 로그인으로 보낸다(backlog 27).
// 서버가 로그인을 쓰지 않거나 단독 모드면 지금처럼 바로 열린다(PRD 5-2 데모).
// 읽기·쓰기는 src/api/center.ts를 거친다. 실패하면 대체하지 않고 연결 띠·실패 문구로 보인다.
// C-02 상담 채팅은 src/api/chat.ts(WebSocket)를 거친다. 단독 모드에는 없다(backlog 25).
// C-02 통화와 번역 자막은 src/api/call.ts(WebSocket + WebRTC)를 거친다. 단독 모드에는 없다(backlog 26).

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate, useParams } from 'react-router';
import { getMe, loginPath, logout, onSessionEnded } from '../../api/auth';
import { clearCases, getStats, resetDemo, setCaseStatus, useCenterCases } from '../../api/center';
import { isCallAvailable } from '../../api/call';
import { isChatAvailable } from '../../api/chat';
import { CallPanel, type CallLabels } from '../../components/CallPanel';
import { ChatPanel, type ChatLabels } from '../../components/ChatPanel';
import { useReveal } from '../../components/reveal';
import type { CaseStatus, CenterCase, CenterStats, StatCell, Urgency } from '../../domain/centerCase';
import { STATUS_KO, URGENCY_KO } from '../../domain/centerCase';
import { PATH_KO } from '../../domain/coverage';
import { CONTACT_METHOD_KO, requestTypesKo } from '../../domain/templates';
import type { District, Industry, Lang, YesNoUnknown } from '../../domain/vocab';
import { DISTRICTS, INDUSTRIES, LANGUAGE_NAMES_KO } from '../../domain/vocab';

// 센터 화면은 한국어 고정이다.
const TEXT = {
  offline: '서버 연결 안 됨',
  lastUpdated: '마지막 갱신',
  never: '없음',
  retry: '다시 시도',
  loading: '목록을 불러오는 중입니다.',
  notLoaded: '목록을 아직 받지 못했습니다.',
  statusFailed: '상태를 바꾸지 못했습니다. 서버 연결을 확인해 주세요.',
  resetFailed: '접수함을 초기화하지 못했습니다. 서버 연결을 확인해 주세요.',
  statsFailed: '통계를 불러오지 못했습니다. 서버 연결을 확인해 주세요.',
  statsLoading: '통계를 불러오는 중입니다.',
  talkTitle: '상담',
  talkMode: '보기',
  modeChat: '채팅',
  modeChatNew: '새 메시지',
  modeScript: '스크립트',
  chatMock: '예시 사례라 근로자 채팅 토큰이 없습니다. 근로자는 이 채팅에 들어올 수 없습니다.',
  chatNote: '근로자가 쓴 글은 번역 없이 원문 그대로 보입니다.',
  callNote: '근로자와 인터넷으로 통화합니다. 두 사람의 말이 자막으로 남고 기계 번역이 붙습니다. 자막은 이 화면을 떠나면 사라집니다(서버에 저장하지 않음).',
  callMock: '예시 사례라 근로자가 이 통화에 들어올 수 없습니다.',
  checking: '로그인을 확인하는 중입니다.',
  meFailed: '서버에 연결하지 못했습니다. 서버 연결을 확인해 주세요.',
  logout: '로그아웃',
  logoutFailed: '로그아웃하지 못했습니다. 서버 연결을 확인해 주세요.',
  relogin: '다시 로그인',
} as const;

const CHAT_LABELS: ChatLabels = {
  empty: '아직 메시지가 없습니다.',
  placeholder: '근로자에게 보낼 메시지',
  send: '보내기',
  me: '센터',
  other: '근로자',
  read: '읽음',
  unread: '안 읽음',
  connecting: '채팅 연결 중…',
  reconnecting: '채팅 연결이 끊겼습니다. 다시 연결하는 중…',
  stopped: {
    denied: '채팅에 연결할 권한이 없습니다.',
    missing: '서버에 이 사례가 없어 채팅을 열 수 없습니다.',
    reset: '데모 초기화로 채팅이 끝났습니다.',
    unauthorized: '로그인이 끝났습니다. 다시 로그인해 주세요.',
  },
  rejected: '메시지를 보내지 못했습니다. 1~1000자로 써 주세요.',
};

const CALL_LABELS: CallLabels = {
  start: '전화 걸기',
  accept: '받기',
  decline: '거절',
  hangup: '끊기',
  mute: '음소거',
  unmute: '음소거 해제',
  calling: '거는 중… (30초 동안 받지 않으면 끊습니다)',
  ringing: '근로자가 전화를 걸었습니다.',
  connecting: '통화 연결 중…',
  inCall: '통화 중',
  ended: {
    self: '통화를 끊었습니다.',
    peer: '근로자가 통화를 끊었습니다.',
    'peer-left': '근로자 화면이 닫혀 통화가 끝났습니다.',
    declined: '근로자가 전화를 거절했습니다.',
    'no-answer': '전화를 받지 않았습니다.',
    failed: '통화를 연결하지 못했습니다. 네트워크를 확인해 주세요.',
  },
  peerAway: '근로자가 화면에 없어 걸 수 없습니다. 채팅으로 먼저 알려 주세요.',
  micDenied: '마이크를 허용해야 통화할 수 있습니다. 브라우저 주소창의 권한 설정을 확인해 주세요.',
  noCaption: '이 브라우저에서는 내 말의 자막을 만들 수 없습니다(Chrome 권장). 통화와 근로자 자막은 그대로 됩니다.',
  unsupported: '이 브라우저나 주소에서는 통화를 쓸 수 없습니다(HTTPS 또는 localhost 필요).',
  me: '센터',
  other: '근로자',
  translating: '번역 중…',
  machineTranslated: '기계 번역',
  socketConnecting: '통화 연결 준비 중…',
  socketReconnecting: '통화 신호 연결이 끊겼습니다. 다시 연결하는 중…',
  stopped: {
    denied: '통화에 연결할 권한이 없습니다.',
    missing: '서버에 이 사례가 없어 통화를 열 수 없습니다.',
    reset: '데모 초기화로 통화가 끝났습니다.',
    unauthorized: '로그인이 끝났습니다. 다시 로그인해 주세요.',
    busy: '다른 창에서 이 사례 통화를 이미 열어 두었습니다. 그 창을 닫으면 여기서 이어집니다.',
  },
};

const hhmm = (iso: string) => new Date(iso).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false });

/** 실패 문구 + 바로 옆 다시 시도. 입력값은 그대로 둔다 (README.md "비동기 UX 규칙") */
function Failure({ text, onRetry, busy }: { text: string; onRetry: () => void; busy: boolean }) {
  return (
    <div className="notice danger with-retry" role="alert">
      <span>{text}</span>
      <button type="button" className="btn secondary" disabled={busy} onClick={onRetry}>
        {TEXT.retry}
      </button>
    </div>
  );
}

/** 센터 머리글. 로그인 화면(C-00)도 같은 머리글에 로고·이름만 쓴다 */
export function CenterHeader({ children }: { children?: ReactNode }) {
  return (
    <header className="c-header">
      <img className="logo" src="/mark.png" width="24" height="24" alt="" />
      <span className="brand">울산외국인주민·근로자통합지원센터 · 의료지원</span>
      {children}
    </header>
  );
}

type Gate = { kind: 'checking' } | { kind: 'open'; email: string | null } | { kind: 'error' };

/**
 * C-01~C-03 공통 틀. 들어올 때 `/api/auth/me`를 한 번 묻고, 열리기 전에는 접수함을 읽지 않는다.
 * 로그인이 필요하면(또는 쓰는 중에 세션이 끝나면) 지금 주소를 `from`에 담아 로그인 화면으로 바꿔 간다.
 */
export function CenterLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  // 로그인 뒤 돌아올 주소. 세션 끝 알림은 나중에 오므로 그때의 주소를 읽도록 ref에 둔다
  const here = useRef('');
  here.current = location.pathname + location.search;
  const [gate, setGate] = useState<Gate>({ kind: 'checking' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let alive = true;
    setGate({ kind: 'checking' });
    getMe().then(
      (me) => {
        if (!alive) return;
        if (me.required && me.email === null) navigate(loginPath(here.current), { replace: true });
        else setGate({ kind: 'open', email: me.email });
      },
      () => alive && setGate({ kind: 'error' }),
    );
    return () => {
      alive = false;
    };
  }, [attempt, navigate]);

  // 센터 경로가 401을 받으면(세션 만료, 직원 목록에서 빠짐) 하던 화면을 기억하고 로그인으로 간다
  useEffect(() => onSessionEnded(() => navigate(loginPath(here.current), { replace: true })), [navigate]);

  if (gate.kind === 'open') return <CenterOpen email={gate.email} />;
  return (
    <div className="c-shell">
      <CenterHeader />
      <main className="c-main">
        {gate.kind === 'checking' ? (
          <p className="muted">{TEXT.checking}</p>
        ) : (
          <Failure text={TEXT.meFailed} onRetry={() => setAttempt((n) => n + 1)} busy={false} />
        )}
      </main>
    </div>
  );
}

/** 로그인 확인이 끝난 센터 화면. 여기서부터 접수함을 읽는다(useCenterCases 구독 = 폴링 시작) */
function CenterOpen({ email }: { email: string | null }) {
  const { connected, lastUpdated } = useCenterCases();
  const navigate = useNavigate();
  const [leaving, setLeaving] = useState(false);
  const [logoutFailed, setLogoutFailed] = useState(false);
  // 스크롤 등장(backlog 25). 근로자 화면과 같은 훅
  const mainRef = useRef<HTMLElement>(null);
  useReveal(mainRef, true);

  const signOut = async () => {
    setLeaving(true);
    setLogoutFailed(false);
    try {
      await logout();
      clearCases();
      navigate('/center/login', { replace: true });
    } catch {
      setLogoutFailed(true);
      setLeaving(false);
    }
  };

  return (
    <div className="c-shell">
      <CenterHeader>
        <nav>
          <NavLink to="/center" end>
            사례 접수함
          </NavLink>
          <NavLink to="/center/stats">통계</NavLink>
        </nav>
        <a href="/" target="_blank" rel="noreferrer" className="small">
          근로자 화면 열기 ↗
        </a>
        {email && (
          <>
            <span className="who small muted">{email}</span>
            <button type="button" className="btn ghost" disabled={leaving} onClick={signOut}>
              {TEXT.logout}
            </button>
          </>
        )}
      </CenterHeader>
      {!connected && (
        <div className="c-offline" role="status">
          ⚠️ {TEXT.offline} · {TEXT.lastUpdated} {lastUpdated ? hhmm(lastUpdated) : TEXT.never}
        </div>
      )}
      <main className="c-main" ref={mainRef}>
        {logoutFailed && <Failure text={TEXT.logoutFailed} onRetry={signOut} busy={leaving} />}
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
  const { cases, connected, lastUpdated } = useCenterCases();
  const navigate = useNavigate();
  const [status, setStatus] = useState<CaseStatus | 'all'>('all');
  const [sort, setSort] = useState<'time' | 'urgency'>('time');
  const [resetting, setResetting] = useState(false);
  const [resetFailed, setResetFailed] = useState(false);

  const reset = async () => {
    setResetting(true);
    setResetFailed(false);
    try {
      await resetDemo();
    } catch {
      setResetFailed(true);
    } finally {
      setResetting(false);
    }
  };

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
          <div className="n danger">
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
          disabled={resetting}
          onClick={() => {
            if (window.confirm('전송된 사례와 상태 변경을 모두 지울까요?')) void reset();
          }}
        >
          접수함 초기화
        </button>
      </div>
      {resetFailed && <Failure text={TEXT.resetFailed} onRetry={() => void reset()} busy={resetting} />}

      {lastUpdated === null && cases.length === 0 ? (
        <p className="muted">{connected ? TEXT.loading : TEXT.notLoaded}</p>
      ) : (
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
                  <td>{requestTypesKo(c.requestTypes)}</td>
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
      )}
      <p className="footer-note">
        mock 사례 24건 + 근로자 화면에서 실제 전송한 사례. 근로자 화면에서 전송하면 2초 안에 이 목록에 나타납니다. 🌙 = 운영 시간 외 접수
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// C-02 사례 상세
// ---------------------------------------------------------------------------
export function CaseDetailPage() {
  const { id } = useParams();
  const { cases, connected, lastUpdated } = useCenterCases();
  const c = cases.find((x) => x.id === id);
  if (!c && lastUpdated === null) {
    return (
      <div className="panel">
        <p className="muted">{connected ? TEXT.loading : TEXT.notLoaded}</p>
        <Link to="/center">← 접수함</Link>
      </div>
    );
  }
  if (!c) {
    return (
      <div className="panel">
        <p>사례를 찾을 수 없습니다.</p>
        <Link to="/center">← 접수함</Link>
      </div>
    );
  }
  // 다른 사례로 옮기면 실패 문구를 지운다
  return <CaseDetail key={c.id} c={c} />;
}

function CaseDetail({ c }: { c: CenterCase }) {
  const flow: CaseStatus[] = ['new', 'progress', 'done'];
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<CaseStatus | null>(null);
  const change = async (s: CaseStatus) => {
    setBusy(true);
    setFailed(null);
    try {
      await setCaseStatus(c.id, s);
    } catch {
      setFailed(s);
    } finally {
      setBusy(false);
    }
  };
  const yn = (v: YesNoUnknown | null, map: Record<YesNoUnknown, string>) => (v ? map[v] : '—');
  // 통화·채팅이 있으면 오른쪽 열을 그 둘에 주고 읽기만 하는 정보는 왼쪽 아래로 보낸다. 없으면(단독 모드) 오른쪽 열에 둔다(backlog 48)
  const side = isCallAvailable() || isChatAvailable();
  const info = (
    <>
      <section className="panel">
        <h2>사례 정보</h2>
        <dl className="kv">
          <dt>접수 시각</dt>
          <dd>
            {new Date(c.createdAt).toLocaleString('ko-KR')} {c.afterHours && '(운영 시간 외)'}
          </dd>
          <dt>요청 유형</dt>
          <dd>{requestTypesKo(c.requestTypes)}</dd>
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
    </>
  );
  return (
    <div>
      <div className="detail-head">
        <div className="row">
          <Link to="/center">← 접수함</Link>
          <h1 style={{ margin: '0 0 0 8px', fontSize: '1.3rem' }}>사례 {c.id}</h1>
          <UrgencyPill u={c.urgency} />
          <StatusPill s={c.status} />
          {c.live && <span className="pill live">실제 전송</span>}
        </div>
        <section className="status-box" aria-labelledby="status-box-label">
          <span className="label" id="status-box-label">
            상태 변경
          </span>
          {flow.map((s) => (
            <button
              key={s}
              type="button"
              className={`btn ${c.status === s ? '' : 'secondary'}`}
              aria-pressed={c.status === s}
              disabled={busy}
              onClick={() => void change(s)}
            >
              {STATUS_KO[s]}
            </button>
          ))}
        </section>
      </div>
      {failed && <Failure text={TEXT.statusFailed} onRetry={() => void change(failed)} busy={busy} />}
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
          {side && info}
        </div>
        <div>
          {side && <CenterTalk c={c} />}
          {!side && info}
        </div>
      </div>
    </div>
  );
}

// C-02 상담 카드(backlog 49). 통화와 채팅을 한 카드에 담는다. 근로자 센터 채팅 시트와 같은 메신저 틀이다:
// 머리(근로자 표시 · 채팅/스크립트 전환) / 통화 줄(상태·버튼, 늘 보인다) / 대화 / 아래 칸(채팅 입력줄).
// 대화는 채팅 메시지나 통화 스크립트(자막) 중 하나를 보인다. 둘 다 늘 붙어 있고 숨기기만 해서 연결·입력 중인 글·자막이 남는다.
// 통화 줄은 대화 바깥이라 스크립트를 보든 채팅을 보든 전화가 오는 것을 놓치지 않는다.

type TalkMode = 'chat' | 'script';

function CenterTalk({ c }: { c: CenterCase }) {
  const chat = isChatAvailable();
  const call = isCallAvailable();
  const [mode, setMode] = useState<TalkMode>(chat ? 'chat' : 'script');
  const body = useRef<HTMLDivElement>(null);
  // 통화 상태·버튼을 그릴 통화 줄과 채팅 입력줄을 그릴 아래 칸. 각 패널이 포털로 그린다
  const [bar, setBar] = useState<HTMLDivElement | null>(null);
  const [foot, setFoot] = useState<HTMLDivElement | null>(null);
  // 스크립트를 보는 사이 근로자가 채팅을 보내면 채팅 버튼에 점을 단다
  const [peerCount, setPeerCount] = useState(0);
  const [seenPeer, setSeenPeer] = useState(0);
  useEffect(() => {
    if (mode === 'chat') setSeenPeer(peerCount);
  }, [mode, peerCount]);
  const unread = mode === 'script' && peerCount > seenPeer;

  // 모드를 바꾸면 그 대화의 맨 아래(최근)를 보인다
  useEffect(() => {
    if (body.current) body.current.scrollTop = body.current.scrollHeight;
  }, [mode]);

  const relogin = <Link to={loginPath(`/center/cases/${c.id}`)}>{TEXT.relogin}</Link>;
  return (
    <section className="panel talk" aria-labelledby="talk-title">
      <header className="sheet-head">
        <span className="sheet-avatar talk-avatar" aria-hidden="true">
          <svg className="sheet-icon" width="22" height="22" viewBox="0 0 24 24" focusable="false">
            <circle cx="12" cy="8.5" r="3.5" />
            <path d="M5 19.5c.8-3.5 3.6-5.5 7-5.5s6.2 2 7 5.5" />
          </svg>
        </span>
        <div className="sheet-title">
          <h2 id="talk-title">{TEXT.talkTitle}</h2>
          <p>근로자 · {LANGUAGE_NAMES_KO[c.language]}</p>
        </div>
        {chat && call && (
          <div className="toggle talk-mode" role="group" aria-label={TEXT.talkMode}>
            <button type="button" aria-pressed={mode === 'chat'} onClick={() => setMode('chat')}>
              {TEXT.modeChat}
              {unread && (
                <>
                  <span className="talk-dot" aria-hidden="true" />
                  <span className="sr-only"> · {TEXT.modeChatNew}</span>
                </>
              )}
            </button>
            <button type="button" aria-pressed={mode === 'script'} onClick={() => setMode('script')}>
              {TEXT.modeScript}
            </button>
          </div>
        )}
      </header>
      {call && <div className="talk-bar" ref={setBar} />}
      <div className="sheet-body" ref={body}>
        {chat && (
          <div className="talk-pane" hidden={mode !== 'chat'}>
            <p className="chat-sys">{c.live ? TEXT.chatNote : TEXT.chatMock}</p>
            <ChatPanel
              caseId={c.id}
              auth={{ role: 'center' }}
              me="center"
              labels={CHAT_LABELS}
              locale="ko-KR"
              relogin={relogin}
              active={mode === 'chat'}
              scroller={body}
              // 스크립트를 볼 때는 입력줄을 숨긴 칸 안에 그린다(입력 중인 글은 남는다)
              footer={mode === 'chat' ? foot : null}
              onPeerCount={setPeerCount}
            />
          </div>
        )}
        {call && (
          <div className="talk-pane" hidden={mode !== 'script'}>
            <p className="chat-sys">{c.live ? TEXT.callNote : TEXT.callMock}</p>
            <CallPanel caseId={c.id} auth={{ role: 'center' }} lang="ko" labels={CALL_LABELS} locale="ko-KR" relogin={relogin} scroller={body} footer={bar} />
          </div>
        )}
      </div>
      <div className="sheet-foot" ref={setFoot} />
    </section>
  );
}

// ---------------------------------------------------------------------------
// C-03 통계: 익명 집계만 보이고 5건 미만 칸은 숨긴다.
// ---------------------------------------------------------------------------
// 칸 값은 src/api/center.ts가 준 그대로 그린다. null(5건 미만)은 "<5"이고 막대·조각을 그리지 않는다.
const cellText = (n: number | null) => (n === null ? '<5' : String(n));
const pct = (rate: number | null) => (rate === null ? '—' : `${Math.round(rate * 100)}%`);

function Bars({ data }: { data: { label: string; n: number | null }[] }) {
  const max = Math.max(...data.map((d) => d.n ?? 0), 1);
  return (
    <div className="bars">
      {data.map((d) => (
        <div className="bar-row" key={d.label}>
          <span>{d.label}</span>
          <div className="bar-track" aria-hidden>
            {d.n !== null && <div className="bar-fill" style={{ width: `${(d.n / max) * 100}%` }} />}
          </div>
          <span className="num">{cellText(d.n)}</span>
        </div>
      ))}
    </div>
  );
}

/** 차트 계열 클래스. 색은 styles.css의 --chart-1~3이 정한다 */
const series = (i: number) => `series-${(i % 3) + 1}`;

/** total은 전체 건수(가린 칸 포함). 가린 칸은 조각 길이 0이고 그 자리만큼 비워 둔다 */
function Donut({ parts, total, label }: { parts: { label: string; n: number | null }[]; total: number | null; label: string }) {
  const whole = total ?? 1;
  const r = 52;
  const circ = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="donut-wrap">
      <svg width="140" height="140" viewBox="0 0 140 140" role="img" aria-label={label}>
        <g transform="rotate(-90 70 70)">
          {parts.map((p, i) => {
            const len = p.n === null || total === null ? 0 : (p.n / whole) * circ;
            const el = (
              <circle
                key={p.label}
                cx="70"
                cy="70"
                r={r}
                fill="none"
                className={series(i)}
                strokeWidth="22"
                strokeDasharray={`${len} ${circ}`}
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
            <i className={series(i)} />
            {p.label} <strong>{p.n === null || total === null ? '<5' : `${p.n}건 (${Math.round((p.n / whole) * 100)}%)`}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}

const cellsBy = <K extends string>(cells: StatCell[], label: (k: K) => string) => cells.map((c) => ({ label: label(c.key as K), n: c.n }));

type StatsState = { kind: 'loading' } | { kind: 'ok'; stats: CenterStats } | { kind: 'error' };

export function StatsPage() {
  const [days, setDays] = useState<30 | 90 | 180>(90);
  const [district, setDistrict] = useState<District | 'all'>('all');
  const [state, setState] = useState<StatsState>({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let alive = true;
    setState({ kind: 'loading' });
    getStats(days, district === 'all' ? null : district).then(
      (stats) => alive && setState({ kind: 'ok', stats }),
      () => alive && setState({ kind: 'error' }),
    );
    return () => {
      alive = false;
    };
  }, [days, district, attempt]);

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

      {state.kind === 'loading' && <p className="muted">{TEXT.statsLoading}</p>}
      {state.kind === 'error' && <Failure text={TEXT.statsFailed} onRetry={() => setAttempt((n) => n + 1)} busy={false} />}
      {state.kind === 'ok' && <StatsView s={state.stats} />}
      <p className="footer-note">
        익명 집계입니다. 개인 단위 기록은 제공하지 않으며 5건 미만인 칸은 "&lt;5"로 숨깁니다. 울산시 담당자는 같은 화면을 읽기 전용으로 사용합니다(실서비스).
      </p>
    </div>
  );
}

function StatsView({ s }: { s: CenterStats }) {
  const byIndustry = cellsBy<Industry>(s.byIndustry, (k) => INDUSTRIES[k]?.ko ?? k);
  const byLang = cellsBy<Lang>(s.byLanguage, (k) => LANGUAGE_NAMES_KO[k] ?? k);
  const byIns = cellsBy<YesNoUnknown>(s.byInsurance, (k) => ({ yes: '있음', no: '없음', unknown: '모름' })[k] ?? k);
  const byAfter = cellsBy<'after' | 'within'>(s.byAfterHours, (k) => ({ after: '운영 시간 외', within: '운영 시간 내' })[k] ?? k);
  return (
    <>
      <div className="c-grid">
        <div className="kpi">
          <div className="n">{cellText(s.total)}</div>
          <div className="l">요청 수</div>
        </div>
        <div className="kpi">
          <div className="n">{pct(s.afterHoursRate)}</div>
          <div className="l">운영 시간 외 요청 비율</div>
        </div>
        <div className="kpi">
          <div className="n">{pct(s.workRelatedRate)}</div>
          <div className="l">업무 중 발생 비율</div>
        </div>
        <div className="kpi">
          <div className="n">{pct(s.noInsuranceRate)}</div>
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
          <Donut parts={byIns} total={s.total} label="보험 상태 분포" />
        </section>
        <section className="panel">
          <h2>운영 시간 외 요청 비율</h2>
          <Donut parts={byAfter} total={s.total} label="운영 시간 외 요청 비율" />
          <p className="footer-note">센터 운영 시간: 일~목 09:00~18:00</p>
        </section>
      </div>
    </>
  );
}

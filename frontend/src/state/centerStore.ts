// 센터 접수함의 단독 모드 구현(VITE_API_BASE가 비었을 때). 화면은 이 파일을 직접 부르지 않고 src/api/center.ts를 거친다.
// localStorage를 서버 DB 대신 쓴다. 같은 브라우저의 다른 탭(센터 화면)에도 storage 이벤트로 즉시 반영되어
// "근로자 전송 → 센터 접수함 도착"을 시연할 수 있다. API 모드에서는 이 파일의 어떤 함수도 부르지 않는다.

import type { StatRecord } from '../data/mock';
import { buildMockCases, buildStatRecords } from '../data/mock';
import type { CasePatch, CaseStatus, CenterCase, CenterStats, NewCaseRequest, NewCaseResponse, StatCell } from '../domain/centerCase';
import { applyCasePatch, defaultCategory, MIN_CELL, rateUrgency, withCaseDefaults } from '../domain/centerCase';
import type { CenterHours } from '../domain/coverage';
import { isAfterHours, nextOpenDay } from '../domain/coverage';
import type { RequestType } from '../domain/templates';
import { buildCenterSummary } from '../domain/templates';
import type { District, Industry, Lang, YesNoUnknown } from '../domain/vocab';
import { INDUSTRIES, LANGS } from '../domain/vocab';
import { readJson, writeJson } from './storage';

const LIVE_KEY = 'umn.center.liveCases';
// 사례 id → 직원이 바꾼 값. 상태만 바꾸던 때(backlog 41 전)는 값이 상태 문자열이다
const STATUS_KEY = 'umn.center.statusOverrides';
const CHANGE_EVENT = 'umn-center-change';

const mockCases = buildMockCases();

type StoredCase = Omit<CenterCase, 'category' | 'actions' | 'referredTo'> & Partial<CenterCase> & { requestType?: RequestType };

/**
 * 이 브라우저에 예전에 저장된 사례를 지금 모양으로 읽는다.
 * 요청 종류가 하나였던 때(backlog 37 전)는 배열로, 분야·조치가 없던 때(backlog 41 전)는 규칙 분야와 빈 조치로 채운다
 */
const upgrade = (c: StoredCase): CenterCase => withCaseDefaults({ ...c, requestTypes: c.requestTypes ?? (c.requestType ? [c.requestType] : []) });

function loadOverrides(): Record<string, CasePatch> {
  const raw = readJson<Record<string, CaseStatus | CasePatch>>(localStorage, STATUS_KEY, {});
  return Object.fromEntries(Object.entries(raw).map(([id, v]) => [id, typeof v === 'string' ? { status: v } : v]));
}

export function loadAllLocal(): CenterCase[] {
  const live = readJson<StoredCase[]>(localStorage, LIVE_KEY, []).map(upgrade);
  const overrides = loadOverrides();
  return [...live, ...mockCases]
    .map((c) => (overrides[c.id] ? applyCasePatch(c, overrides[c.id]!) : c))
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

/** 다른 탭의 storage 이벤트, 같은 탭의 변경, 놓친 이벤트를 위한 2초 주기 갱신을 듣는다 */
export function subscribeLocal(onChange: () => void): () => void {
  window.addEventListener('storage', onChange);
  window.addEventListener(CHANGE_EVENT, onChange);
  const timer = window.setInterval(onChange, 2000);
  return () => {
    window.removeEventListener('storage', onChange);
    window.removeEventListener(CHANGE_EVENT, onChange);
    window.clearInterval(timer);
  };
}

const changed = () => window.dispatchEvent(new Event(CHANGE_EVENT));

/** 브라우저 시각 기준 YYYY-MM-DD(서버의 `nextOpenDate`와 같은 형식) */
const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/** 서버 `POST /api/center/cases`와 같은 계산을 브라우저에서 한다(요약·긴급도·운영 시간 외·id·접수 시각) */
export function sendCaseLocal(req: NewCaseRequest, hours: CenterHours): NewCaseResponse {
  const now = new Date();
  const summary = buildCenterSummary(req);
  const { urgency, reasons } = rateUrgency({ workRelated: req.intake.workRelated, insurance: req.insurance });
  const c: CenterCase = {
    id: `C-${now.getTime().toString().slice(-5)}`,
    createdAt: now.toISOString(),
    language: req.intake.language,
    requestTypes: req.requestTypes,
    urgency,
    urgencyReasons: reasons,
    district: req.intake.district,
    industry: req.intake.industry,
    status: 'new',
    category: defaultCategory({ coveragePath: req.coverage?.path ?? null, requestTypes: req.requestTypes }),
    actions: [],
    referredTo: [],
    summaryKo: summary.ko,
    originalNative: summary.native,
    consentedItems: req.consentedItems,
    coveragePath: req.coverage?.path ?? null,
    contactMethod: req.contactMethod,
    contact: req.contact?.trim() || null,
    afterHours: isAfterHours(now, hours),
    workRelated: req.intake.workRelated,
    insurance: req.insurance,
    live: true,
  };
  const live = readJson<CenterCase[]>(localStorage, LIVE_KEY, []);
  writeJson(localStorage, LIVE_KEY, [c, ...live]);
  changed();
  return { case: c, nextOpenDate: ymd(nextOpenDay(now, hours)) };
}

/** 서버 `PATCH`와 같이 보낸 필드만 바꾼다. 앞서 바꾼 필드는 남는다 */
export function updateCaseLocal(id: string, patch: CasePatch): void {
  const overrides = loadOverrides();
  writeJson(localStorage, STATUS_KEY, { ...overrides, [id]: { ...overrides[id], ...patch } });
  changed();
}

/** 데모 초기화: 실제 전송 사례와 상태 변경을 지운다. */
export function resetCenterDemoLocal(): void {
  writeJson(localStorage, LIVE_KEY, []);
  writeJson(localStorage, STATUS_KEY, {});
  changed();
}

// ---------------------------------------------------------------------------
// C-03 통계: 서버 `GET /api/center/stats`와 같은 집계·가림을 브라우저 mock 원천으로 한다.
// ---------------------------------------------------------------------------
let statRecords: StatRecord[] | null = null;

const mask = (n: number) => (n >= MIN_CELL ? n : null);

function countBy<K extends string>(recs: StatRecord[], keys: K[], get: (r: StatRecord) => K): StatCell[] {
  return keys.map((k) => ({ key: k, n: mask(recs.filter((r) => get(r) === k).length) }));
}

export function getStatsLocal(days: number, district: District | null): CenterStats {
  statRecords ??= buildStatRecords();
  const since = Date.now() - days * 86400000;
  const recs = statRecords.filter((r) => r.date.getTime() >= since && (district === null || r.district === district));
  const total = recs.length;
  const after = recs.filter((r) => r.afterHours).length;
  const shown = total >= MIN_CELL;
  const rate = (n: number) => (shown ? n / total : null);
  return {
    total: shown ? total : null,
    afterHoursRate: rate(after),
    workRelatedRate: rate(recs.filter((r) => r.workRelated === 'yes').length),
    noInsuranceRate: rate(recs.filter((r) => r.insurance !== 'yes').length),
    byIndustry: countBy(recs, Object.keys(INDUSTRIES) as Industry[], (r) => r.industry),
    byLanguage: countBy(recs, [...LANGS] as Lang[], (r) => r.language),
    byInsurance: countBy(recs, ['yes', 'no', 'unknown'] as YesNoUnknown[], (r) => r.insurance),
    byAfterHours: [
      { key: 'after', n: mask(after) },
      { key: 'within', n: mask(total - after) },
    ],
  };
}

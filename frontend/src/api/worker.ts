// 근로자 화면(S-05~S-12)이 부르는 함수. 단독/API 모드 분기와 실패 시 대체 분기는 여기에만 있다(README "경로별 대체 정책").
// 화면은 두 모드에서 같은 형태의 값을 받고, 시간 제한 숫자를 갖지 않는다.

import type { CoverageInput, CoverageResult } from '../domain/coverage';
import { routeCoverage as routeCoverageLocal } from '../domain/coverage';
import type { CenterSummary, CenterSummaryInput, ClinicianReport, Profile, ReportField, VisitHelper } from '../domain/templates';
import {
  buildCallScript,
  buildCenterSummary as buildCenterSummaryLocal,
  buildClinicianReport as buildClinicianReportLocal,
  buildDeskSheet,
} from '../domain/templates';
import type { ExtractResult, Intake, TriageResult } from '../domain/triage';
import { extractIntake, triage } from '../domain/triage';
import type { Department, Lang } from '../domain/vocab';
import { ApiError, isApiMode, logFallback, requestJson } from './http';
import { useServerResult } from './useServerResult';

/** 응급 판정 서버 호출 시간 제한. 넘기면 브라우저 결과를 쓴다 */
export const TRIAGE_TIMEOUT_MS = 3000;
/** 자유 입력 추출 서버 호출 시간 제한. 넘기면 브라우저 키워드 사전을 쓴다(backend 03 LLM이 붙으면 다시 정한다) */
export const EXTRACT_TIMEOUT_MS = 8000;

/**
 * 중간 단계의 응급 선별. 브라우저 규칙만 돌리고 서버를 부르지 않는다.
 * `/emergency`로 가는 길에는 비동기 호출을 두지 않는다(README "비동기 UX 규칙").
 */
export function screenEmergency(intake: Intake): TriageResult {
  return triage(intake);
}

/**
 * 최종 응급 판정과 진료과 추천.
 * 브라우저 `triage()`를 먼저 돌려 응급이면 서버를 기다리지 않고 바로 돌려준다.
 * 응급이 아니고 API 모드면 `POST /api/triage`를 부르고, 실패하거나 시간 제한을 넘기면 브라우저 결과를 돌려준다.
 * 서버 결과가 응급이면 응급이다. 서버가 더하는 선택 필드(`model` 등)는 그대로 실린다.
 */
export async function checkTriage(intake: Intake): Promise<TriageResult> {
  const local = triage(intake);
  if (local.emergency || !isApiMode()) return local;
  try {
    const remote = await requestJson<Partial<TriageResult>>('/triage', { body: intake, timeoutMs: TRIAGE_TIMEOUT_MS });
    if (typeof remote.emergency !== 'boolean' || remote.department === undefined) {
      throw new ApiError('BAD_RESPONSE', null, null);
    }
    return { ...local, ...remote } as TriageResult;
  } catch (e) {
    logFallback('/triage', e);
    return local;
  }
}

/**
 * 자유 입력 추출. 단독 모드는 브라우저 키워드 사전, API 모드는 `POST /api/extract`(LLM 또는 키워드).
 * 실패하거나 시간 제한을 넘기면 브라우저 함수로 조용히 대체한다(추출에서 멈추면 응급 판정이 늦어진다).
 * 자유 입력이 비어 있으면 뽑을 것이 없으므로 서버를 부르지 않는다.
 * 버튼으로 고른 값이 우선이고 빈 항목만 채워지는 것은 두 모드가 같다.
 */
export async function extract(intake: Intake): Promise<ExtractResult> {
  if (!isApiMode() || intake.freeText.trim() === '') return extractIntake(intake);
  try {
    const r = await requestJson<Partial<ExtractResult>>('/extract', { body: { intake }, timeoutMs: EXTRACT_TIMEOUT_MS });
    if (!r.extraction || !r.intake || typeof r.filled !== 'boolean') {
      throw new ApiError('BAD_RESPONSE', null, null);
    }
    return r as ExtractResult;
  } catch (e) {
    logFallback('/extract', e);
    return extractIntake(intake);
  }
}

/**
 * 추출을 키워드 사전으로 했는지. API 모드에서 자유 입력이 있었는데 LLM이 채우지 않았으면 true다
 * (서버 키워드 사전 `source: 'keywords'`, 서버 실패 후 브라우저 사전 `source` 없음 둘 다).
 * 단독 모드는 원래 키워드 사전뿐이라 알리지 않는다.
 */
export function usedKeywordFallback(result: ExtractResult, freeText: string): boolean {
  return isApiMode() && freeText.trim() !== '' && result.source !== 'llm';
}

// ---------------------------------------------------------------------------
// S-08~S-12: 서버 결과와 브라우저 결과가 같은 경로. 실패하면 조용히 브라우저 함수로 대체한다.
// ---------------------------------------------------------------------------

/** 제도 경로·접수 도우미·리포트·센터 요약 서버 호출 시간 제한. 넘기면 브라우저 템플릿을 쓴다 */
export const TEMPLATE_TIMEOUT_MS = 8000;

/** 서버를 부르고, 필수 필드 검사에 실패하거나 요청이 실패하면 `fallback()`을 돌려준다 */
async function withFallback<T>(path: string, body: unknown, valid: (r: Partial<T>) => boolean, fallback: () => T): Promise<T> {
  if (!isApiMode()) return fallback();
  try {
    const r = await requestJson<Partial<T>>(path, { body, timeoutMs: TEMPLATE_TIMEOUT_MS });
    if (!valid(r)) throw new ApiError('BAD_RESPONSE', null, null);
    return r as T;
  } catch (e) {
    logFallback(path, e);
    return fallback();
  }
}

const isLines = (x: unknown): boolean => Array.isArray(x) && x.every((l) => l && typeof l.ko === 'string' && typeof l.native === 'string');

/** POST /api/route. `infoDate`는 `/api/meta`의 기준일이다(서버 결과에는 서버가 넣는다) */
export function routeCoverage(input: CoverageInput, infoDate: string): Promise<CoverageResult> {
  return withFallback<CoverageResult>(
    '/route',
    input,
    (r) => typeof r.path === 'string' && Array.isArray(r.institutions) && Array.isArray(r.docs) && typeof r.infoDate === 'string',
    () => routeCoverageLocal(input, infoDate),
  );
}

function visitHelperLocal(intake: Intake, department: Department, firstVisit: boolean, lang: Lang): VisitHelper {
  return { desk: buildDeskSheet(intake, department, firstVisit, lang), call: buildCallScript(intake, department, lang) };
}

/** POST /api/visit-helper. 접수 창구(S-09)와 전화 스크립트(S-10)를 한 번에 받는다 */
export function buildVisitHelper(intake: Intake, department: Department, firstVisit: boolean, lang: Lang): Promise<VisitHelper> {
  return withFallback<VisitHelper>(
    '/visit-helper',
    { intake, department, firstVisit, lang },
    (r) => Boolean(r.desk && isLines(r.desk.lines) && Array.isArray(r.desk.docsKo) && r.call && isLines(r.call.lines) && Array.isArray(r.call.faq)),
    () => visitHelperLocal(intake, department, firstVisit, lang),
  );
}

/** POST /api/report/clinician. 버튼을 눌렀을 때 부른다(S-11) */
export function buildClinicianReport(intake: Intake, included: ReportField[], profile: Profile | null, meds: string): Promise<ClinicianReport> {
  return withFallback<ClinicianReport>(
    '/report/clinician',
    { intake, included, profile, meds },
    (r) => typeof r.id === 'string' && typeof r.createdAt === 'string' && Array.isArray(r.rows),
    () => buildClinicianReportLocal(intake, included, profile, meds),
  );
}

/** POST /api/report/center. S-12 미리보기 */
export function buildCenterSummary(input: CenterSummaryInput): Promise<CenterSummary> {
  return withFallback<CenterSummary>(
    '/report/center',
    input,
    (r) => typeof r.ko === 'string' && typeof r.native === 'string',
    () => buildCenterSummaryLocal(input),
  );
}

// 버튼 없이 바로 뜨는 화면용. 브라우저 결과를 먼저 그리고 서버 결과가 오면 바꾼다(useServerResult).

/** S-08. 입력이 다 갖춰지지 않았으면 null */
export function useCoverage(input: CoverageInput | null, infoDate: string): CoverageResult | null {
  return useServerResult<CoverageResult | null>(
    JSON.stringify([input, infoDate]),
    () => (input ? routeCoverageLocal(input, infoDate) : null),
    input ? () => routeCoverage(input, infoDate) : null,
  );
}

/** S-09·S-10 */
export function useVisitHelper(intake: Intake, department: Department, firstVisit: boolean, lang: Lang): VisitHelper {
  return useServerResult<VisitHelper>(
    JSON.stringify([intake, department, firstVisit, lang]),
    () => visitHelperLocal(intake, department, firstVisit, lang),
    () => buildVisitHelper(intake, department, firstVisit, lang),
  );
}

/** S-12 미리보기. 요청 종류를 고르기 전이면 null */
export function useCenterSummary(input: CenterSummaryInput | null): CenterSummary | null {
  return useServerResult<CenterSummary | null>(
    JSON.stringify(input),
    () => (input ? buildCenterSummaryLocal(input) : null),
    input ? () => buildCenterSummary(input) : null,
  );
}

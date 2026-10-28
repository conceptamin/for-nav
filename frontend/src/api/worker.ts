// 근로자 화면(S-05)이 부르는 함수. 단독/API 모드 분기와 실패 시 대체 분기는 여기에만 있다(README "경로별 대체 정책").
// 화면은 두 모드에서 같은 형태의 값을 받고, 시간 제한 숫자를 갖지 않는다.

import type { ExtractResult, Intake, TriageResult } from '../domain/triage';
import { extractIntake, triage } from '../domain/triage';
import { ApiError, isApiMode, logFallback, requestJson } from './http';

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

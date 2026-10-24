// 센터 사례(CenterCase)와 긴급도 규칙. 긴급도는 규칙 기반이며 LLM을 쓰지 않는다.

import type { CoveragePath } from './coverage';
import type { ContactMethod, RequestType } from './templates';
import type { District, Industry, Lang, YesNoUnknown } from './vocab';

export type CaseStatus = 'new' | 'progress' | 'done';
export type Urgency = 'high' | 'medium' | 'low';

export interface CenterCase {
  id: string;
  createdAt: string;
  language: Lang;
  requestType: RequestType;
  urgency: Urgency;
  urgencyReasons: string[];
  district: District | null;
  industry: Industry | null;
  status: CaseStatus;
  summaryKo: string;
  originalNative: string;
  /** 근로자가 센터 전송에 동의한 항목(한국어 표시) */
  consentedItems: string[];
  coveragePath: CoveragePath | null;
  contactMethod: ContactMethod | null;
  contact: string | null;
  afterHours: boolean;
  emergencyFlag: boolean;
  workRelated: YesNoUnknown | null;
  insurance: YesNoUnknown | null;
  /** 데모에서 실제로 전송한 사례(mock과 구분) */
  live: boolean;
}

export function rateUrgency(input: {
  emergencyFlag: boolean;
  workRelated: YesNoUnknown | null;
  insurance: YesNoUnknown | null;
}): { urgency: Urgency; reasons: string[] } {
  let score = 0;
  const reasons: string[] = [];
  if (input.emergencyFlag) {
    score += 3;
    reasons.push('응급 판정 이력');
  }
  if (input.workRelated === 'yes') {
    score += 2;
    reasons.push('업무 중 발생');
  }
  if (input.insurance === 'no') {
    score += 1;
    reasons.push('건강보험증 없음');
  }
  const urgency: Urgency = score >= 3 ? 'high' : score >= 1 ? 'medium' : 'low';
  return { urgency, reasons };
}

export const URGENCY_KO: Record<Urgency, string> = { high: '높음', medium: '보통', low: '낮음' };
export const STATUS_KO: Record<CaseStatus, string> = { new: '신규', progress: '진행', done: '완료' };

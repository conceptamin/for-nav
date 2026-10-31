// 센터 사례(CenterCase)와 긴급도 규칙. 긴급도는 규칙 기반이며 LLM을 쓰지 않는다.

import type { CoveragePath } from './coverage';
import type { CenterSummaryInput, ContactMethod, RequestType } from './templates';
import type { District, Industry, Lang, YesNoUnknown } from './vocab';

export type CaseStatus = 'new' | 'progress' | 'done';
export type Urgency = 'high' | 'medium' | 'low';

export interface CenterCase {
  id: string;
  createdAt: string;
  language: Lang;
  requestTypes: RequestType[];
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

/** S-12 전송 요청(`POST /api/center/cases`). 요약·긴급도·운영 시간 외 여부·id·접수 시각은 받는 쪽이 계산한다 */
export interface NewCaseRequest extends CenterSummaryInput {
  contact: string | null;
  /** 근로자가 전송에 동의한 항목(한국어 표시) */
  consentedItems: string[];
}

export interface NewCaseResponse {
  case: CenterCase;
  /** 다음 운영일(YYYY-MM-DD, 센터 시각) */
  nextOpenDate: string;
  /** 이 사례 상담 채팅에 근로자로 붙는 열쇠(API 모드만, backend 14). 센터 목록·상세에는 나오지 않는다 */
  chatToken?: string;
}

/** 근로자가 자기 요청을 다시 읽을 때 보내는 열쇠(`POST /api/center/my-cases`, backend 26). 단독 모드는 토큰 없이 id로 읽는다 */
export interface MyCaseRef {
  id: string;
  token: string | null;
}

/** 근로자가 보는 자기 요청의 처리 상태(backend 26). 사례 본문은 근로자 기기에 이미 있어 받지 않는다 */
export interface MyCaseView {
  id: string;
  status: CaseStatus;
  /** 센터가 보낸 채팅 메시지 수. 근로자 글은 세지 않는다. 단독 모드는 채팅이 없어 0 */
  centerMessages: number;
  /** 마지막 센터 메시지 시각(ISO). 없으면 null */
  lastCenterAt: string | null;
}

/** 서버가 센 센터 메시지가 근로자가 채팅에서 본 수보다 많으면 새 메시지가 있다 */
export function hasUnread(view: MyCaseView | undefined, seen: number | undefined): boolean {
  return (view?.centerMessages ?? 0) > (seen ?? 0);
}

/** 상담 채팅에서 보낸 쪽. 연결할 때 서버가 확인한 역할이다 */
export type ChatRole = 'worker' | 'center';

/** 상담 채팅 메시지 하나. id·from·at은 서버가 정한다(backend 14) */
export interface ChatMessage {
  /** 사례 안에서 m-1, m-2… */
  id: string;
  caseId: string;
  from: ChatRole;
  text: string;
  /** ISO(UTC) */
  at: string;
}

/** 서버가 받는 글 길이(앞뒤 공백을 지운 뒤). 넘으면 서버가 error 프레임을 보낸다 */
export const CHAT_MAX_LEN = 1000;

/** 통화 자막 번역 상태(backend 05·16). ok가 아니면 translated는 null이고 원문만 있다 */
export type CaptionTranslation = 'ok' | 'skipped' | 'rejected';

/** 통화 자막 한 줄. 받아쓴 확정 문장을 서버가 번역해 양쪽에 보낸다(backend 16). 서버는 저장하지 않는다 */
export interface Caption {
  /** 사례 안에서 c-1, c-2…(말한 순서) */
  id: string;
  from: ChatRole;
  text: string;
  /** 원문 언어. 근로자 말은 사례 언어, 센터 말은 ko */
  lang: Lang;
  translated: string | null;
  translatedLang: Lang;
  translation: CaptionTranslation;
  /** ISO(UTC) */
  at: string;
}

/** 서버가 받는 자막 한 줄 길이. 넘는 부분은 보내기 전에 자른다 */
export const CAPTION_MAX_LEN = 500;

/** 통계 칸. 이보다 적은 칸은 숫자를 내보내지 않는다(개인 단위 기록 보호) */
export const MIN_CELL = 5;

export interface StatCell {
  key: string;
  /** `MIN_CELL`건 미만이면 null */
  n: number | null;
}

/** C-03 익명 집계(`GET /api/center/stats`). 비율은 0~1이고 total이 null이면 null이다 */
export interface CenterStats {
  total: number | null;
  afterHoursRate: number | null;
  workRelatedRate: number | null;
  noInsuranceRate: number | null;
  byIndustry: StatCell[];
  byLanguage: StatCell[];
  byInsurance: StatCell[];
  /** key: `after` | `within` */
  byAfterHours: StatCell[];
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

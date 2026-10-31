// 센터 사례(CenterCase)와 긴급도 규칙. 긴급도는 규칙 기반이며 LLM을 쓰지 않는다.

import type { CoveragePath } from './coverage';
import type { CenterSummaryInput, ContactMethod, RequestType } from './templates';
import type { District, Industry, Lang, YesNoUnknown } from './vocab';

export type CaseStatus = 'new' | 'progress' | 'done';
export type Urgency = 'high' | 'medium' | 'low';
/** 센터 회신(2026-10-31)의 의료 상담 집계 분야: 의료·보건 / 건강보험·공공의료 / 의료비 지원 */
export type CaseCategory = 'medical' | 'insurance' | 'cost';
/** 센터 지원 절차에서 한 조치. 한 사례에 여럿이 겹친다 */
export type CaseAction = 'info' | 'interpret' | 'referral' | 'followUp';
/** 관계기관 연계 대상. `referral` 조치가 있을 때만 쓴다 */
export type ReferralTarget = 'nhis' | 'kcomwel' | 'hospital' | 'ulsan' | 'other';

export const CASE_CATEGORIES: CaseCategory[] = ['medical', 'insurance', 'cost'];
export const CASE_ACTIONS: CaseAction[] = ['info', 'interpret', 'referral', 'followUp'];
export const REFERRAL_TARGETS: ReferralTarget[] = ['nhis', 'kcomwel', 'hospital', 'ulsan', 'other'];

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
  /** 접수 때 `defaultCategory`로 채우고 직원이 C-02에서 바꾼다 */
  category: CaseCategory;
  /** 직원이 기록한 조치(처음 []) */
  actions: CaseAction[];
  /** 연계 기관(처음 []). `actions`에 `referral`이 없으면 비어 있다 */
  referredTo: ReferralTarget[];
  /** 국적(ISO 3166-1 alpha-2). 근로자가 프로필에서 고르고 전송에 동의했을 때만 있다(backlog 42). C-01 목록에는 보이지 않는다 */
  nationality: string | null;
  summaryKo: string;
  originalNative: string;
  /** 근로자가 센터 전송에 동의한 항목(한국어 표시) */
  consentedItems: string[];
  coveragePath: CoveragePath | null;
  contactMethod: ContactMethod | null;
  contact: string | null;
  afterHours: boolean;
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
  /** 국적(두 글자 대문자). 고르지 않았거나 전송에 동의하지 않으면 키째 없다 */
  nationality?: string;
}

export interface NewCaseResponse {
  case: CenterCase;
  /** 다음 운영일(YYYY-MM-DD, 센터 시각) */
  nextOpenDate: string;
  /** 이 사례 상담 채팅에 근로자로 붙는 열쇠(API 모드만, backend 14). 센터 목록·상세에는 나오지 않는다 */
  chatToken?: string;
}

/** 근로자가 자기 요청을 다시 읽을 때 보내는 열쇠(`POST /api/center/my-cases`, backend 27). 단독 모드는 토큰 없이 id로 읽는다 */
export interface MyCaseRef {
  id: string;
  token: string | null;
}

/** 근로자가 보는 자기 요청의 처리 상태(backend 27). 사례 본문은 근로자 기기에 이미 있어 받지 않는다 */
export interface MyCaseView {
  id: string;
  status: CaseStatus;
  /** 센터가 보낸 채팅 메시지 수. 근로자 글은 세지 않는다. 단독 모드는 채팅이 없어 0 */
  centerMessages: number;
  /** 마지막 센터 메시지 시각(ISO). 없으면 null */
  lastCenterAt: string | null;
}

/** 서버가 센 센터 메시지 중 근로자가 채팅에서 아직 보지 않은 수(backlog 53) */
export function unreadCount(view: MyCaseView | undefined, seen: number | undefined): number {
  return Math.max(0, (view?.centerMessages ?? 0) - (seen ?? 0));
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
  /** 번역(backend 30). 뜻은 Caption과 같다. 번역 전 서버·이전에 저장된 메시지는 없거나 null */
  lang?: Lang | null;
  /** translation이 ok일 때만 있다 */
  translated?: string | null;
  translatedLang?: Lang | null;
  translation?: CaptionTranslation | null;
  /** ISO(UTC) */
  at: string;
}

/** 서버가 받는 글 길이(앞뒤 공백을 지운 뒤). 넘으면 서버가 error 프레임을 보낸다 */
export const CHAT_MAX_LEN = 1000;

/** 통화 자막·채팅 메시지 번역 상태(backend 05·16·30). ok가 아니면 translated는 null이고 원문만 있다 */
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
  /** 최근 6개월(오래된 달부터, 마지막이 이번 달, 센터 시각). key: `YYYY-MM`. 기간 필터를 따르지 않고 구·군 필터만 따른다 */
  byMonth: StatCell[];
  /** key: CaseCategory(CASE_CATEGORIES 순서) */
  byCategory: StatCell[];
  /** key: 국적 코드 또는 `unknown`(국적 없음). 있는 국적만, 많은 순(같으면 코드 순), 가린 칸은 끝 */
  byNationality: StatCell[];
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
  workRelated: YesNoUnknown | null;
  insurance: YesNoUnknown | null;
}): { urgency: Urgency; reasons: string[] } {
  let score = 0;
  const reasons: string[] = [];
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

/**
 * 접수 때 분야 기본값. 제도 경로와 요청 종류만 본다(증상 내용으로 가르지 않는다).
 * 울산 지원 경로 → 의료비 지원, 건강보험 경로이거나 제도 상담만 고르면 → 건강보험·공공의료, 나머지 → 의료·보건
 */
export function defaultCategory(input: { coveragePath: CoveragePath | null; requestTypes: RequestType[] }): CaseCategory {
  if (input.coveragePath === 'ulsanSupport') return 'cost';
  if (input.coveragePath === 'nhis' || (input.requestTypes.length === 1 && input.requestTypes[0] === 'policy')) return 'insurance';
  return 'medical';
}

/** 분야·조치·국적이 없는 사례(backlog 41·42 전에 저장한 것, 아직 옛 서버)를 규칙 분야, 빈 조치, 국적 없음으로 채운다 */
export function withCaseDefaults(c: Omit<CenterCase, 'category' | 'actions' | 'referredTo' | 'nationality'> & Partial<CenterCase>): CenterCase {
  return {
    ...c,
    category: c.category ?? defaultCategory(c),
    actions: c.actions ?? [],
    referredTo: c.referredTo ?? [],
    nationality: c.nationality ?? null,
  };
}

/** C-02 분야·조치 변경(`PATCH /api/center/cases/{id}`). 있는 필드만 바꾼다 */
export type CasePatch = Partial<Pick<CenterCase, 'status' | 'category' | 'actions' | 'referredTo'>>;

/** 조치·연계 기관을 고정 순서로 맞추고, 연계 조치가 없으면 기관을 비운다 */
export function applyCasePatch(c: CenterCase, patch: CasePatch): CenterCase {
  const next = { ...c, ...patch };
  const actions = CASE_ACTIONS.filter((a) => next.actions.includes(a));
  const referredTo = actions.includes('referral') ? REFERRAL_TARGETS.filter((t) => next.referredTo.includes(t)) : [];
  return { ...next, actions, referredTo };
}

export const URGENCY_KO: Record<Urgency, string> = { high: '높음', medium: '보통', low: '낮음' };
export const STATUS_KO: Record<CaseStatus, string> = { new: '신규', progress: '진행', done: '완료' };
export const CATEGORY_KO: Record<CaseCategory, string> = { medical: '의료·보건', insurance: '건강보험·공공의료', cost: '의료비 지원' };
export const ACTION_KO: Record<CaseAction, string> = { info: '정보 제공', interpret: '통역 지원', referral: '관계기관 연계', followUp: '후속 상담 필요' };
export const REFERRAL_KO: Record<ReferralTarget, string> = {
  nhis: '국민건강보험공단',
  kcomwel: '근로복지공단',
  hospital: '의료기관',
  ulsan: '울산시',
  other: '그 밖의 기관',
};

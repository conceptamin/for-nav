// 보험·제도 경로(POST /route 대응). 판정이 아니라 "먼저 상담할 곳" 안내다.
// 같은 입력이면 같은 결과가 나오는 결정적 규칙이며 LLM을 쓰지 않는다.

import type { YesNoUnknown } from './vocab';

export type CoveragePath = 'industrial' | 'nhis' | 'ulsanSupport' | 'center';

export interface Institution {
  /** 언어 파일 키 접미사(inst.<id>) */
  id: 'kcomwel' | 'nhis' | 'center' | 'ulsan';
  /** 확인된 번호만 넣는다. 미확인이면 null이고 화면에 "센터 상담으로 확인하세요"를 보인다. */
  phone: string | null;
}

export interface CoverageInput {
  workRelated: YesNoUnknown;
  insurance: YesNoUnknown;
  /** 보험이 "아니요"일 때만 묻는다 */
  ulsan90: YesNoUnknown | null;
}

export interface CoverageResult {
  path: CoveragePath;
  /** 업무 관련 여부가 "모름"이면 산재 상담 가능성을 보조로 알린다 */
  alsoIndustrial: boolean;
  institutions: Institution[];
  /** 언어 파일 키 접미사(doc.<id>) */
  docs: ('arc' | 'insuranceCard' | 'accidentNote' | 'photos' | 'receipts' | 'meds')[];
  infoDate: string;
}

/** 제도 정보 기준일. 실제 운영 시 담당자가 확인한 날짜로 바꾼다. */
export const INFO_DATE = '2026-10-24';

// 대표번호는 공개된 기관 대표번호만 둔다. 센터·울산시 지원사업 연락처는 미확인(PRD Q1·Q6).
const KCOMWEL: Institution = { id: 'kcomwel', phone: '1588-0075' };
const NHIS: Institution = { id: 'nhis', phone: '1577-1000' };
const CENTER: Institution = { id: 'center', phone: null };
const ULSAN: Institution = { id: 'ulsan', phone: null };

/** `infoDate`는 API 모드에서 `/api/meta`가 준 기준일을 넘길 때만 쓴다. 기본값이면 지금과 같다. */
export function routeCoverage(input: CoverageInput, infoDate: string = INFO_DATE): CoverageResult {
  const base = { infoDate, alsoIndustrial: input.workRelated === 'unknown' };
  if (input.workRelated === 'yes') {
    return { ...base, path: 'industrial', institutions: [KCOMWEL, CENTER], docs: ['arc', 'accidentNote', 'photos', 'receipts'] };
  }
  if (input.insurance === 'yes') {
    return { ...base, path: 'nhis', institutions: [NHIS, CENTER], docs: ['arc', 'insuranceCard', 'meds'] };
  }
  if (input.insurance === 'no' && input.ulsan90 === 'yes') {
    return { ...base, path: 'ulsanSupport', institutions: [CENTER, ULSAN], docs: ['arc', 'receipts'] };
  }
  return { ...base, path: 'center', institutions: [CENTER], docs: ['arc'] };
}

export const PATH_KO: Record<CoveragePath, string> = {
  industrial: '산재 상담 먼저',
  nhis: '건강보험 진료',
  ulsanSupport: '울산 의료비 지원 상담',
  center: '센터 상담',
};

// ---------------------------------------------------------------------------
// 센터 운영 시간(설정값). PRD Q1 미결: 확인 전까지 평일 09:00~18:00으로 가정한다.
// ---------------------------------------------------------------------------
export interface CenterHours {
  openHour: number;
  closeHour: number;
  /** 0 = 일요일 */
  workdays: number[];
}

export const CENTER_HOURS: CenterHours = { openHour: 9, closeHour: 18, workdays: [1, 2, 3, 4, 5] };

/** 서버 설정값(GET /api/meta). 단독 모드와 서버 실패 시에는 브라우저 상수를 쓴다. */
export interface Meta {
  infoDate: string;
  centerHours: CenterHours;
}

export const DEFAULT_META: Meta = { infoDate: INFO_DATE, centerHours: CENTER_HOURS };

/** `hours`는 API 모드에서 `/api/meta`가 준 운영 시간을 넘길 때만 쓴다. 기본값이면 지금과 같다. */
export function isAfterHours(date: Date, hours: CenterHours = CENTER_HOURS): boolean {
  const h = date.getHours();
  return !hours.workdays.includes(date.getDay()) || h < hours.openHour || h >= hours.closeHour;
}

/** 다음 운영일(오늘 운영 시작 전이면 오늘) */
export function nextOpenDay(date: Date, hours: CenterHours = CENTER_HOURS): Date {
  const d = new Date(date);
  if (hours.workdays.includes(d.getDay()) && d.getHours() < hours.openHour) return d;
  do {
    d.setDate(d.getDate() + 1);
  } while (!hours.workdays.includes(d.getDay()));
  return d;
}

// 근로자 모국어 하나의 내용 묶음. 한국어를 뺀 언어마다 이 형태의 파일이 하나씩 있다(en.ts, vi.ts, ...).
// 한국어 표기·발음 표기는 vocab.ts·templates.ts에 있고, 여기에는 근로자에게 보이는 모국어만 둔다.
// 새 언어는 파일 하나를 추가하고 index.ts의 PACKS에 등록하면 된다. 빠진 키는 타입 검사가 잡는다.

import type { BodyPart, Department, District, Industry, Onset, Sex, Symptom, WorkType, YesNoUnknown } from '../vocab';

export type PhraseKey = 'firstVisit' | 'revisit' | 'workYes' | 'workNo' | 'korean' | 'hello' | 'arc';
export type FaqId = 'first' | 'when' | 'where' | 'insurance' | 'help';
export type AnswerKey =
  | 'firstYes'
  | 'firstNo'
  | 'whenToday'
  | 'whenTomorrowAm'
  | 'whenTomorrowPm'
  | 'whenEarliest'
  | 'insuranceYes'
  | 'insuranceNo'
  | 'insuranceUnsure'
  | 'helpRepeat'
  | 'helpText';
export type ReportFieldKey = 'symptoms' | 'bodyParts' | 'onset' | 'circumstance' | 'note' | 'baseline' | 'meds';
export type RequestTypeKey = 'booking' | 'interpret' | 'policy' | 'referral' | 'other';

export interface LangPack {
  /** 고정 어휘. vocab.ts의 표와 키가 같다 */
  terms: {
    bodyParts: Record<BodyPart, string>;
    symptoms: Record<Symptom, string>;
    departments: Record<Department, string>;
    onsets: Record<Onset, string>;
    industries: Record<Industry, string>;
    workTypes: Record<WorkType, string>;
    districts: Record<District, string>;
    sexes: Record<Sex, string>;
  };
  /**
   * 접수 도우미·의료진 리포트·센터 요약 문장.
   * 문장 틀의 `{이름}`은 값 그대로, `{이름:lower}`는 소문자로 바꿔 채운다(templates.ts `fill`).
   */
  templates: {
    phrases: Record<PhraseKey, string>;
    /** {syms} 증상들, {parts} 부위들 */
    symptom: string;
    /** {dept} 진료과 */
    department: string;
    /** {onset} 시작 시점 */
    onset: string;
    docs: Record<'arc' | 'insurance' | 'meds', string>;
    faq: Record<FaqId, string>;
    answers: Record<AnswerKey, string>;
    fields: Record<ReportFieldKey, string>;
    /** {age} 나이, {sex} 성별 */
    age: string;
    height: string;
    weight: string;
    alcohol: string;
    smoking: string;
    drinkingValue: Record<'none' | 'sometimes' | 'often', string>;
    smokingValue: Record<'no' | 'yes' | 'quit', string>;
    yesNo: Record<YesNoUnknown, string>;
    happenedAtWork: string;
    workType: string;
    industry: string;
    problem: string;
    area: string;
    myNote: string;
    request: string;
    requestTypes: Record<RequestTypeKey, string>;
  };
}

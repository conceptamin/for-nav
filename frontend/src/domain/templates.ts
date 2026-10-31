// 예약·접수 도우미(POST /visit-helper), 의료진용 리포트(POST /report/clinician),
// 센터 리포트(POST /report/center)의 문장 템플릿.
// 실서비스에서는 LLM이 템플릿 슬롯을 채우고, 실패하면 이 기본 템플릿을 그대로 쓴다.
// 데모는 LLM 없이 기본 템플릿만 사용한다. 진단 표현(병명·골절 등)을 쓰지 않는다.

import type { CoverageResult } from './coverage';
import { PATH_KO } from './coverage';
import type { Intake } from './triage';
import { PACKS } from './lang';
import type { AnswerKey, FaqId, LangPack, PhraseKey } from './lang/types';
import type { Department, Lang, NativeLang, Term, YesNoUnknown } from './vocab';
import { BODY_PARTS, DEPARTMENTS, DISTRICTS, INDUSTRIES, josa, LANGUAGE_NAMES_KO, ONSETS, pron, SEXES, SYMPTOMS, WORK_TYPES } from './vocab';

export interface Line {
  ko: string;
  native: string;
  pron: string;
}

export interface Profile {
  birthDate: string;
  sex: 'male' | 'female';
  height: number | null;
  weight: number | null;
  drinking: 'none' | 'sometimes' | 'often' | null;
  smoking: 'no' | 'yes' | 'quit' | null;
  /** 국적(ISO 3166-1 alpha-2, 선택, backlog 42). 센터 전송 때 따로 동의해야 보낸다. 이 칸 전에 저장한 프로필에는 없다 */
  nationality?: string | null;
}

const pick = (t: Term, lang: Lang) => t[lang];
const tpl = (lang: NativeLang): LangPack['templates'] => PACKS[lang].templates;

const joinTerms = (terms: Term[], key: Lang) => terms.map((t) => t[key]).join(', ');
const joinPron = (terms: Term[], lang: Lang) => terms.map((t) => pron(t, lang)).join(', ');

/** 문장 틀의 `{이름}`을 값으로, `{이름:lower}`를 소문자 값으로 채운다. */
export function fill(frame: string, vars: Record<string, string>): string {
  return frame.replace(/\{(\w+)(:lower)?\}/g, (_, name: string, lower?: string) => {
    const v = vars[name] ?? '';
    return lower ? v.toLowerCase() : v;
  });
}

// 한국어 사용자에게 보일 때의 "모국어" 문구. 다른 언어는 lang/<언어>.ts의 templates에 있다.
const YES_NO_KO: Record<YesNoUnknown, string> = { yes: '예', no: '아니요', unknown: '모름' };

// ---------------------------------------------------------------------------
// 공통 문장
// ---------------------------------------------------------------------------
const PHRASES: Record<PhraseKey, KoPhrase> = {
  firstVisit: { ko: '처음 왔습니다.', roman: 'cheo-eum wat-seum-ni-da', viPron: 'chơ-ưm oát-xưm-ni-đa' },
  revisit: { ko: '전에 온 적이 있습니다.', roman: 'jeo-ne on jeo-gi it-seum-ni-da', viPron: 'chơ-nê ôn chơ-ghi ít-xưm-ni-đa' },
  workYes: { ko: '일하다가 생겼습니다.', roman: 'il-ha-da-ga saeng-gyeot-seum-ni-da', viPron: 'in-ha-đa-ga xeng-ghiớt-xưm-ni-đa' },
  workNo: { ko: '일과 관계없이 생겼습니다.', roman: 'il-gwa gwan-gye-eop-si saeng-gyeot-seum-ni-da', viPron: 'in-goa coan-ghiê-ớp-xi xeng-ghiớt-xưm-ni-đa' },
  korean: { ko: '한국어가 서툽니다. 천천히 말씀해 주세요.', roman: 'han-gu-geo-ga seo-tum-ni-da. cheon-cheon-hi mal-sseum-hae ju-se-yo', viPron: 'han-cu-gơ-ga xơ-thum-ni-đa. chơn-chơn-hi man-xưm-he chu-xê-iô' },
  hello: { ko: '안녕하세요. 진료 예약을 하고 싶습니다.', roman: 'an-nyeong-ha-se-yo. jil-lyo ye-ya-geul ha-go sip-seum-ni-da', viPron: 'an-niơng-ha-xê-iô. chin-liô iê-ia-gưn ha-cô xíp-xưm-ni-đa' },
  arc: { ko: '외국인등록증이 있습니다.', roman: 'oe-gu-gin-deung-nok-jeung-i it-seum-ni-da', viPron: 'uê-cu-ghin-tưng-nốc-chưng-i ít-xưm-ni-đa' },
};

/** 한국어 문장과 발음 표기. 모국어 문장은 언어 묶음의 같은 키에 있다 */
interface KoPhrase {
  ko: string;
  roman: string;
  viPron: string;
}

const koPron = (p: KoPhrase, lang: Lang) => (lang === 'ko' ? '' : lang === 'vi' ? p.viPron : p.roman);

const phraseLine = (key: PhraseKey, lang: Lang): Line => {
  const p = PHRASES[key];
  return { ko: p.ko, native: lang === 'ko' ? p.ko : tpl(lang).phrases[key], pron: koPron(p, lang) };
};

function symptomLine(intake: Intake, lang: Lang): Line | null {
  if (!intake.bodyParts.length || !intake.symptoms.length) return null;
  const parts = intake.bodyParts.map((p) => BODY_PARTS[p]);
  const syms = intake.symptoms.map((s) => SYMPTOMS[s]);
  const symKo = joinTerms(syms, 'ko');
  const withJosa = josa(symKo, '이', '가');
  const josaPron = withJosa.endsWith('이') ? 'i' : 'ga';
  const ko = `${joinTerms(parts, 'ko')}에 ${withJosa} 있어서 진료받고 싶습니다.`;
  if (lang === 'ko') return { ko, native: ko, pron: '' };
  const native = fill(tpl(lang).symptom, { syms: joinTerms(syms, lang), parts: joinTerms(parts, lang) });
  const tail = lang === 'vi' ? 'ít-xơ-xơ chin-liô-bát-cô xíp-xưm-ni-đa' : 'it-seo-seo jil-lyo-bat-go sip-seum-ni-da';
  return { ko, native, pron: `${joinPron(parts, lang)}-e ${joinPron(syms, lang)}-${josaPron} ${tail}` };
}

function departmentLine(dept: Department, lang: Lang): Line {
  const d = DEPARTMENTS[dept];
  const ko = `${d.ko} 진료를 원합니다.`;
  return {
    ko,
    native: lang === 'ko' ? ko : fill(tpl(lang).department, { dept: d[lang] }),
    pron: lang === 'ko' ? '' : `${pron(d, lang)} ${lang === 'vi' ? 'chin-liô-rưn uôn-ham-ni-đa' : 'jil-lyo-reul won-ham-ni-da'}`,
  };
}

function onsetLine(intake: Intake, lang: Lang): Line | null {
  if (!intake.onset) return null;
  const o = ONSETS[intake.onset];
  const ko = `${o.ko} 시작됐습니다.`;
  return {
    ko,
    native: lang === 'ko' ? ko : fill(tpl(lang).onset, { onset: o[lang] }),
    pron: lang === 'ko' ? '' : `${pron(o, lang)} ${lang === 'vi' ? 'xi-chác-toét-xưm-ni-đa' : 'si-jak-dwaet-seum-ni-da'}`,
  };
}

// ---------------------------------------------------------------------------
// FR-50 접수 창구 화면
// ---------------------------------------------------------------------------
export interface DeskSheet {
  lines: Line[];
  firstVisit: boolean;
  workRelatedKo: string;
  docsKo: { ko: string; native: string }[];
}

export function buildDeskSheet(intake: Intake, dept: Department, firstVisit: boolean, lang: Lang): DeskSheet {
  const lines: Line[] = [phraseLine(firstVisit ? 'firstVisit' : 'revisit', lang)];
  const sym = symptomLine(intake, lang);
  if (sym) lines.push(sym);
  lines.push(departmentLine(dept, lang));
  const onset = onsetLine(intake, lang);
  if (onset) lines.push(onset);
  if (intake.workRelated === 'yes') lines.push(phraseLine('workYes', lang));
  if (intake.workRelated === 'no') lines.push(phraseLine('workNo', lang));
  // "한국어가 서툽니다"는 한국어 사용자에게는 넣지 않는다.
  if (lang !== 'ko') lines.push(phraseLine('korean', lang));
  const workRelatedKo = { yes: '예(업무 중 발생)', no: '아니요', unknown: '모름' }[intake.workRelated ?? 'unknown'];
  const docs = { arc: '외국인등록증', insurance: '건강보험증(있는 경우)', meds: '복용 중인 약(있는 경우)' } as const;
  const docsKo = (Object.keys(docs) as (keyof typeof docs)[]).map((k) => ({ ko: docs[k], native: lang === 'ko' ? docs[k] : tpl(lang).docs[k] }));
  return { lines, firstVisit, workRelatedKo, docsKo };
}

// ---------------------------------------------------------------------------
// FR-51 전화 스크립트
// ---------------------------------------------------------------------------
export interface Faq {
  id: FaqId;
  /** 질문. 한국어 사용자는 native가 ko와 같다 */
  q: { ko: string; native: string };
  answers: Line[];
}

export interface CallScript {
  lines: Line[];
  faq: Faq[];
}

/** POST /api/visit-helper 응답. `llmSlots`는 서버가 LLM으로 채운 슬롯 이름 목록(backend 04)이고 브라우저 결과에는 없다. */
export interface VisitHelper {
  desk: DeskSheet;
  call: CallScript;
  llmSlots?: string[];
}

/** 자유 입력 번역 결과(backend 05). 서버 전용 선택 필드다. */
export interface TranslationInfo {
  status: 'ok' | 'rejected' | 'skipped';
}

const FAQ_KO: Record<FaqId, string> = {
  first: '처음 오셨어요?',
  when: '언제 오시겠어요?',
  where: '어디가 아프세요?',
  insurance: '건강보험 있으세요?',
  help: '(못 알아들었을 때)',
};

const ANSWERS: Record<AnswerKey, KoPhrase> = {
  firstYes: { ko: '네, 처음입니다.', roman: 'ne, cheo-eum-im-ni-da', viPron: 'nê, chơ-ưm-im-ni-đa' },
  firstNo: { ko: '아니요, 전에 간 적이 있습니다.', roman: 'a-ni-yo, jeo-ne gan jeo-gi it-seum-ni-da', viPron: 'a-ni-iô, chơ-nê can chơ-ghi ít-xưm-ni-đa' },
  whenToday: { ko: '오늘 가고 싶습니다.', roman: 'o-neul ga-go sip-seum-ni-da', viPron: 'ô-nưn ca-cô xíp-xưm-ni-đa' },
  whenTomorrowAm: { ko: '내일 오전에 가고 싶습니다.', roman: 'nae-il o-jeo-ne ga-go sip-seum-ni-da', viPron: 'ne-in ô-chơ-nê ca-cô xíp-xưm-ni-đa' },
  whenTomorrowPm: { ko: '내일 오후에 가고 싶습니다.', roman: 'nae-il o-hu-e ga-go sip-seum-ni-da', viPron: 'ne-in ô-hu-ê ca-cô xíp-xưm-ni-đa' },
  whenEarliest: { ko: '가장 빠른 시간에 가고 싶습니다.', roman: 'ga-jang ppa-reun si-ga-ne ga-go sip-seum-ni-da', viPron: 'ca-chang ba-rưn xi-ca-nê ca-cô xíp-xưm-ni-đa' },
  insuranceYes: { ko: '네, 있습니다.', roman: 'ne, it-seum-ni-da', viPron: 'nê, ít-xưm-ni-đa' },
  insuranceNo: { ko: '없습니다.', roman: 'eop-seum-ni-da', viPron: 'ớp-xưm-ni-đa' },
  insuranceUnsure: { ko: '잘 모르겠습니다.', roman: 'jal mo-reu-get-seum-ni-da', viPron: 'chan mô-rư-ghết-xưm-ni-đa' },
  helpRepeat: { ko: '다시 한 번 말씀해 주세요.', roman: 'da-si han beon mal-sseum-hae ju-se-yo', viPron: 'ta-xi han bơn man-xưm-he chu-xê-iô' },
  helpText: { ko: '문자로 보내 주세요.', roman: 'mun-ja-ro bo-nae ju-se-yo', viPron: 'mun-cha-rô pô-ne chu-xê-iô' },
};

const ans = (key: AnswerKey, lang: Lang): Line => {
  const a = ANSWERS[key];
  return { ko: a.ko, native: lang === 'ko' ? a.ko : tpl(lang).answers[key], pron: koPron(a, lang) };
};

const faqQ = (id: FaqId, lang: Lang): Faq['q'] => ({ ko: FAQ_KO[id], native: lang === 'ko' ? FAQ_KO[id] : tpl(lang).faq[id] });

export function buildCallScript(intake: Intake, dept: Department, lang: Lang): CallScript {
  const lines: Line[] = [phraseLine('hello', lang), departmentLine(dept, lang)];
  const sym = symptomLine(intake, lang);
  if (sym) lines.push(sym);
  if (lang !== 'ko') lines.push(phraseLine('korean', lang));
  lines.push(phraseLine('arc', lang));

  const faq: Faq[] = [
    { id: 'first', q: faqQ('first', lang), answers: [ans('firstYes', lang), ans('firstNo', lang)] },
    {
      id: 'when',
      q: faqQ('when', lang),
      answers: [ans('whenToday', lang), ans('whenTomorrowAm', lang), ans('whenTomorrowPm', lang), ans('whenEarliest', lang)],
    },
    { id: 'where', q: faqQ('where', lang), answers: sym ? [sym] : [] },
    { id: 'insurance', q: faqQ('insurance', lang), answers: [ans('insuranceYes', lang), ans('insuranceNo', lang), ans('insuranceUnsure', lang)] },
    { id: 'help', q: faqQ('help', lang), answers: [ans('helpRepeat', lang), ans('helpText', lang)] },
  ];
  return { lines, faq };
}

// ---------------------------------------------------------------------------
// FR-60 의료진용 리포트
// ---------------------------------------------------------------------------
export const REPORT_FIELDS = ['symptoms', 'bodyParts', 'onset', 'circumstance', 'note', 'baseline', 'meds'] as const;
export type ReportField = (typeof REPORT_FIELDS)[number];

export interface ReportRow {
  field: ReportField;
  labelKo: string;
  valueKo: string;
  labelNative: string;
  valueNative: string;
}

export interface ClinicianReport {
  id: string;
  intakeId: string;
  language: Lang;
  included: ReportField[];
  rows: ReportRow[];
  createdAt: string;
  /** 서버 전용 선택 필드(backend 04·05). 브라우저 결과에는 없다 */
  llmSlots?: string[];
  translation?: TranslationInfo;
  /** 근로자가 붙인 사진(JPEG data URL). 서버로 보내지 않고 이 기기에서 리포트를 만든 뒤 붙인다 */
  photos?: string[];
}

const FIELD_LABEL_KO: Record<ReportField, string> = {
  symptoms: '증상',
  bodyParts: '부위',
  onset: '시작 시점',
  circumstance: '경위',
  note: '환자 메모(원문)',
  baseline: '기저 정보',
  meds: '복용 중인 약',
};

export function fieldLabel(field: ReportField, lang: Lang): string {
  return lang === 'ko' ? FIELD_LABEL_KO[field] : tpl(lang).fields[field];
}

function age(birthDate: string): number | null {
  const b = new Date(birthDate);
  if (Number.isNaN(b.getTime())) return null;
  const now = new Date();
  let a = now.getFullYear() - b.getFullYear();
  if (now < new Date(now.getFullYear(), b.getMonth(), b.getDate())) a -= 1;
  return a;
}

function baselineText(p: Profile, key: Lang): string {
  const parts: string[] = [];
  const a = age(p.birthDate);
  if (key === 'ko') {
    const drink = { none: '안 함', sometimes: '가끔', often: '자주' };
    const smoke = { no: '안 함', yes: '함', quit: '끊음' };
    if (a !== null) parts.push(`${a}세 ${{ male: '남', female: '여' }[p.sex]}`);
    if (p.height) parts.push(`키 ${p.height}cm`);
    if (p.weight) parts.push(`체중 ${p.weight}kg`);
    if (p.drinking) parts.push(`음주: ${drink[p.drinking]}`);
    if (p.smoking) parts.push(`흡연: ${smoke[p.smoking]}`);
    return parts.join(' · ');
  }
  const t = tpl(key);
  if (a !== null) parts.push(fill(t.age, { age: String(a), sex: SEXES[p.sex][key] }));
  if (p.height) parts.push(`${t.height} ${p.height}cm`);
  if (p.weight) parts.push(`${t.weight} ${p.weight}kg`);
  if (p.drinking) parts.push(`${t.alcohol}: ${t.drinkingValue[p.drinking]}`);
  if (p.smoking) parts.push(`${t.smoking}: ${t.smokingValue[p.smoking]}`);
  return parts.join(' · ');
}

/** 근로자가 제외한 항목은 아예 계산하지 않는다(LLM에도 보내지 않는 원칙과 동일). */
export function buildClinicianReport(
  intake: Intake,
  included: ReportField[],
  profile: Profile | null,
  meds: string,
): ClinicianReport {
  const lang = intake.language;
  const rows: ReportRow[] = [];
  const add = (field: ReportField, valueKo: string, valueNative: string) => {
    if (!included.includes(field) || !valueKo.trim()) return;
    rows.push({ field, labelKo: FIELD_LABEL_KO[field], valueKo, labelNative: fieldLabel(field, lang), valueNative });
  };
  const syms = intake.symptoms.map((s) => SYMPTOMS[s]);
  const parts = intake.bodyParts.map((p) => BODY_PARTS[p]);
  add('symptoms', joinTerms(syms, 'ko'), joinTerms(syms, lang));
  add('bodyParts', joinTerms(parts, 'ko'), joinTerms(parts, lang));
  if (intake.onset) add('onset', ONSETS[intake.onset].ko, pick(ONSETS[intake.onset], lang));

  const circKo: string[] = [];
  const circNative: string[] = [];
  if (intake.workRelated) {
    circKo.push(`업무 중 발생: ${YES_NO_KO[intake.workRelated]}`);
    if (lang !== 'ko') circNative.push(`${tpl(lang).happenedAtWork}: ${tpl(lang).yesNo[intake.workRelated]}`);
  }
  if (intake.workType) {
    circKo.push(`작업 유형: ${WORK_TYPES[intake.workType].ko}`);
    if (lang !== 'ko') circNative.push(`${tpl(lang).workType}: ${pick(WORK_TYPES[intake.workType], lang)}`);
  }
  if (intake.industry) {
    circKo.push(`업종: ${INDUSTRIES[intake.industry].ko}`);
    if (lang !== 'ko') circNative.push(`${tpl(lang).industry}: ${pick(INDUSTRIES[intake.industry], lang)}`);
  }
  add('circumstance', circKo.join(' / '), lang === 'ko' ? circKo.join(' / ') : circNative.join(' / '));
  // 자유 입력은 번역 LLM이 연결되기 전까지 원문 그대로 둔다. 한국어 입력은 번역이 필요 없다.
  const noteKo = lang === 'ko' ? intake.freeText : `${intake.freeText} (원문, 번역 미연결)`;
  add('note', intake.freeText ? noteKo : '', intake.freeText);
  if (profile) add('baseline', baselineText(profile, 'ko'), baselineText(profile, lang));
  add('meds', meds, meds);

  return {
    id: `rp-${Date.now().toString(36)}`,
    intakeId: intake.id,
    language: lang,
    included,
    rows,
    createdAt: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// FR-70 센터 리포트
// ---------------------------------------------------------------------------
export type RequestType = 'booking' | 'interpret' | 'policy' | 'referral' | 'other';
export type ContactMethod = 'phone' | 'sms' | 'kakao' | 'zalo' | 'visit';

export const REQUEST_TYPE_KO: Record<RequestType, string> = {
  booking: '예약 지원',
  interpret: '통번역',
  policy: '제도 상담',
  referral: '기관 연계',
  other: '기타',
};
export const CONTACT_METHOD_KO: Record<ContactMethod, string> = {
  phone: '전화',
  sms: '문자',
  kakao: '카카오톡',
  zalo: 'Zalo',
  visit: '센터 방문',
};

type SummaryText = Pick<LangPack['templates'], 'problem' | 'happenedAtWork' | 'area' | 'industry' | 'myNote' | 'request' | 'yesNo'>;
const SUMMARY_KO: SummaryText = { problem: '불편한 점', happenedAtWork: '업무 중 발생', area: '지역', industry: '업종', myNote: '내 메모', request: '요청', yesNo: YES_NO_KO };
const summaryText = (lang: Lang): SummaryText => (lang === 'ko' ? SUMMARY_KO : tpl(lang));

export interface CenterSummaryInput {
  intake: Intake;
  /** 근로자가 고른 순서. 하나 이상 */
  requestTypes: RequestType[];
  coverage: CoverageResult | null;
  insurance: 'yes' | 'no' | 'unknown' | null;
  contactMethod: ContactMethod | null;
}

export interface CenterSummary {
  ko: string;
  native: string;
  /** 서버 전용 선택 필드(backend 05). 브라우저 결과에는 없다 */
  translation?: TranslationInfo;
}

/** 사실 요약만 한다. 판단·추측 문장을 넣지 않는다. */
export function buildCenterSummary(i: CenterSummaryInput): CenterSummary {
  const { intake } = i;
  const lang = intake.language;
  const parts = intake.bodyParts.map((p) => BODY_PARTS[p]);
  const syms = intake.symptoms.map((s) => SYMPTOMS[s]);
  const ko: string[] = [];
  const nv: string[] = [];
  const where = [intake.district ? DISTRICTS[intake.district].ko : null, intake.industry ? `${INDUSTRIES[intake.industry].ko} 업종` : null].filter(Boolean);
  ko.push(`${LANGUAGE_NAMES_KO[lang]} 사용 근로자${where.length ? `(${where.join(', ')})` : ''}.`);
  if (parts.length || syms.length) ko.push(`${joinTerms(parts, 'ko') || '부위 미입력'} ${joinTerms(syms, 'ko') || ''}${intake.onset ? `, ${ONSETS[intake.onset].ko} 시작` : ''}.`);
  if (intake.workRelated) ko.push(`업무 중 발생: ${YES_NO_KO[intake.workRelated]}${intake.workType ? `(${WORK_TYPES[intake.workType].ko})` : ''}.`);
  if (i.insurance) ko.push(`건강보험증: ${{ yes: '있음', no: '없음', unknown: '모름' }[i.insurance]}.`);
  if (i.coverage) ko.push(`제도 경로 결과: ${PATH_KO[i.coverage.path]}.`);
  ko.push(`요청 유형: ${requestTypesKo(i.requestTypes)}.`);
  if (i.contactMethod) ko.push(`연락 희망: ${CONTACT_METHOD_KO[i.contactMethod]}.`);

  const t = summaryText(lang);
  if (parts.length || syms.length) nv.push(`${t.problem}: ${joinTerms(syms, lang)} — ${joinTerms(parts, lang)}${intake.onset ? ` (${pick(ONSETS[intake.onset], lang)})` : ''}.`);
  if (intake.workRelated) nv.push(`${t.happenedAtWork}: ${t.yesNo[intake.workRelated]}.`);
  if (intake.district) nv.push(`${t.area}: ${pick(DISTRICTS[intake.district], lang)}.`);
  if (intake.industry) nv.push(`${t.industry}: ${pick(INDUSTRIES[intake.industry], lang)}.`);
  if (intake.freeText) nv.push(`${t.myNote}: "${intake.freeText}"`);
  nv.push(`${t.request}: ${i.requestTypes.map((r) => requestTypeNative(r, lang)).join(', ')}.`);
  return { ko: ko.join(' '), native: nv.join('\n') };
}

/** 센터 화면·요약의 요청 유형 한 줄(한국어) */
export function requestTypesKo(types: RequestType[]): string {
  return types.map((r) => REQUEST_TYPE_KO[r]).join(', ');
}

export function requestTypeNative(t: RequestType, lang: Lang): string {
  return lang === 'ko' ? REQUEST_TYPE_KO[t] : tpl(lang).requestTypes[t];
}

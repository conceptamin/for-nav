// 예약·접수 도우미(POST /visit-helper), 의료진용 리포트(POST /report/clinician),
// 센터 리포트(POST /report/center)의 문장 템플릿.
// 실서비스에서는 LLM이 템플릿 슬롯을 채우고, 실패하면 이 기본 템플릿을 그대로 쓴다.
// 데모는 LLM 없이 기본 템플릿만 사용한다. 진단 표현(병명·골절 등)을 쓰지 않는다.

import type { CoverageResult } from './coverage';
import { PATH_KO } from './coverage';
import type { Intake } from './triage';
import type { Department, Lang, Term } from './vocab';
import { BODY_PARTS, DEPARTMENTS, DISTRICTS, INDUSTRIES, josa, ONSETS, pron, SYMPTOMS, WORK_TYPES } from './vocab';

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
}

type Tri = { ko: string; en: string; vi: string };
const pick = (t: Tri | Term, lang: Lang) => (lang === 'vi' ? t.vi : t.en);

const joinTerms = (terms: Term[], key: 'ko' | 'en' | 'vi') => terms.map((t) => t[key]).join(', ');
const joinPron = (terms: Term[], lang: Lang) => terms.map((t) => pron(t, lang)).join(', ');

// ---------------------------------------------------------------------------
// 공통 문장
// ---------------------------------------------------------------------------
const PHRASES = {
  firstVisit: { ko: '처음 왔습니다.', en: 'This is my first visit.', vi: 'Tôi đến lần đầu.', roman: 'cheo-eum wat-seum-ni-da', viPron: 'chơ-ưm oát-xưm-ni-đa' },
  revisit: { ko: '전에 온 적이 있습니다.', en: 'I have been here before.', vi: 'Tôi đã từng đến đây.', roman: 'jeo-ne on jeo-gi it-seum-ni-da', viPron: 'chơ-nê ôn chơ-ghi ít-xưm-ni-đa' },
  workYes: { ko: '일하다가 생겼습니다.', en: 'It happened while I was working.', vi: 'Bị trong lúc đang làm việc.', roman: 'il-ha-da-ga saeng-gyeot-seum-ni-da', viPron: 'in-ha-đa-ga xeng-ghiớt-xưm-ni-đa' },
  workNo: { ko: '일과 관계없이 생겼습니다.', en: 'It is not related to work.', vi: 'Không liên quan đến công việc.', roman: 'il-gwa gwan-gye-eop-si saeng-gyeot-seum-ni-da', viPron: 'in-goa coan-ghiê-ớp-xi xeng-ghiớt-xưm-ni-đa' },
  korean: { ko: '한국어가 서툽니다. 천천히 말씀해 주세요.', en: 'My Korean is limited. Please speak slowly.', vi: 'Tôi nói tiếng Hàn chưa giỏi. Xin hãy nói chậm.', roman: 'han-gu-geo-ga seo-tum-ni-da. cheon-cheon-hi mal-sseum-hae ju-se-yo', viPron: 'han-cu-gơ-ga xơ-thum-ni-đa. chơn-chơn-hi man-xưm-he chu-xê-iô' },
  hello: { ko: '안녕하세요. 진료 예약을 하고 싶습니다.', en: 'Hello. I would like to make an appointment.', vi: 'Xin chào. Tôi muốn đặt lịch khám.', roman: 'an-nyeong-ha-se-yo. jil-lyo ye-ya-geul ha-go sip-seum-ni-da', viPron: 'an-niơng-ha-xê-iô. chin-liô iê-ia-gưn ha-cô xíp-xưm-ni-đa' },
  arc: { ko: '외국인등록증이 있습니다.', en: 'I have an alien registration card (ARC).', vi: 'Tôi có thẻ đăng ký người nước ngoài (ARC).', roman: 'oe-gu-gin-deung-nok-jeung-i it-seum-ni-da', viPron: 'uê-cu-ghin-tưng-nốc-chưng-i ít-xưm-ni-đa' },
} satisfies Record<string, Term>;

const phraseLine = (t: Term, lang: Lang): Line => ({ ko: t.ko, native: pick(t, lang), pron: pron(t, lang) });

function symptomLine(intake: Intake, lang: Lang): Line | null {
  if (!intake.bodyParts.length || !intake.symptoms.length) return null;
  const parts = intake.bodyParts.map((p) => BODY_PARTS[p]);
  const syms = intake.symptoms.map((s) => SYMPTOMS[s]);
  const symKo = joinTerms(syms, 'ko');
  const withJosa = josa(symKo, '이', '가');
  const josaPron = withJosa.endsWith('이') ? 'i' : 'ga';
  const ko = `${joinTerms(parts, 'ko')}에 ${withJosa} 있어서 진료받고 싶습니다.`;
  const native =
    lang === 'vi'
      ? `Tôi bị ${joinTerms(syms, 'vi').toLowerCase()} ở ${joinTerms(parts, 'vi').toLowerCase()}, muốn được khám.`
      : `I have ${joinTerms(syms, 'en').toLowerCase()} in my ${joinTerms(parts, 'en').toLowerCase()} and would like to see a doctor.`;
  const tail = lang === 'vi' ? 'ít-xơ-xơ chin-liô-bát-cô xíp-xưm-ni-đa' : 'it-seo-seo jil-lyo-bat-go sip-seum-ni-da';
  return { ko, native, pron: `${joinPron(parts, lang)}-e ${joinPron(syms, lang)}-${josaPron} ${tail}` };
}

function departmentLine(dept: Department, lang: Lang): Line {
  const d = DEPARTMENTS[dept];
  return {
    ko: `${d.ko} 진료를 원합니다.`,
    native: lang === 'vi' ? `Tôi muốn khám ${d.vi.toLowerCase()}.` : `I would like to see ${d.en}.`,
    pron: `${pron(d, lang)} ${lang === 'vi' ? 'chin-liô-rưn uôn-ham-ni-đa' : 'jil-lyo-reul won-ham-ni-da'}`,
  };
}

function onsetLine(intake: Intake, lang: Lang): Line | null {
  if (!intake.onset) return null;
  const o = ONSETS[intake.onset];
  return {
    ko: `${o.ko} 시작됐습니다.`,
    native: lang === 'vi' ? `Bắt đầu từ ${o.vi.toLowerCase()}.` : `It started ${o.en.toLowerCase()}.`,
    pron: `${pron(o, lang)} ${lang === 'vi' ? 'xi-chác-toét-xưm-ni-đa' : 'si-jak-dwaet-seum-ni-da'}`,
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
  const lines: Line[] = [phraseLine(firstVisit ? PHRASES.firstVisit : PHRASES.revisit, lang)];
  const sym = symptomLine(intake, lang);
  if (sym) lines.push(sym);
  lines.push(departmentLine(dept, lang));
  const onset = onsetLine(intake, lang);
  if (onset) lines.push(onset);
  if (intake.workRelated === 'yes') lines.push(phraseLine(PHRASES.workYes, lang));
  if (intake.workRelated === 'no') lines.push(phraseLine(PHRASES.workNo, lang));
  lines.push(phraseLine(PHRASES.korean, lang));
  const workRelatedKo = { yes: '예(업무 중 발생)', no: '아니요', unknown: '모름' }[intake.workRelated ?? 'unknown'];
  const docs: Tri[] = [
    { ko: '외국인등록증', en: 'Alien registration card (ARC)', vi: 'Thẻ đăng ký người nước ngoài (ARC)' },
    { ko: '건강보험증(있는 경우)', en: 'Health insurance card (if you have one)', vi: 'Thẻ bảo hiểm y tế (nếu có)' },
    { ko: '복용 중인 약(있는 경우)', en: 'Medicines you are taking (if any)', vi: 'Thuốc đang dùng (nếu có)' },
  ];
  return { lines, firstVisit, workRelatedKo, docsKo: docs.map((d) => ({ ko: d.ko, native: pick(d, lang) })) };
}

// ---------------------------------------------------------------------------
// FR-51 전화 스크립트
// ---------------------------------------------------------------------------
export interface Faq {
  id: string;
  q: Tri;
  answers: Line[];
}

const ans = (ko: string, en: string, vi: string, roman: string, viPron: string, lang: Lang): Line => ({
  ko,
  native: lang === 'vi' ? vi : en,
  pron: lang === 'vi' ? viPron : roman,
});

export function buildCallScript(intake: Intake, dept: Department, lang: Lang): { lines: Line[]; faq: Faq[] } {
  const lines: Line[] = [phraseLine(PHRASES.hello, lang), departmentLine(dept, lang)];
  const sym = symptomLine(intake, lang);
  if (sym) lines.push(sym);
  lines.push(phraseLine(PHRASES.korean, lang), phraseLine(PHRASES.arc, lang));

  const faq: Faq[] = [
    {
      id: 'first',
      q: { ko: '처음 오셨어요?', en: 'Is this your first visit?', vi: 'Đây là lần đầu bạn đến phải không?' },
      answers: [
        ans('네, 처음입니다.', 'Yes, it is my first time.', 'Vâng, lần đầu.', 'ne, cheo-eum-im-ni-da', 'nê, chơ-ưm-im-ni-đa', lang),
        ans('아니요, 전에 간 적이 있습니다.', 'No, I have been before.', 'Không, tôi đã từng đến.', 'a-ni-yo, jeo-ne gan jeo-gi it-seum-ni-da', 'a-ni-iô, chơ-nê can chơ-ghi ít-xưm-ni-đa', lang),
      ],
    },
    {
      id: 'when',
      q: { ko: '언제 오시겠어요?', en: 'When would you like to come?', vi: 'Bạn muốn đến khi nào?' },
      answers: [
        ans('오늘 가고 싶습니다.', 'Today, please.', 'Tôi muốn đến hôm nay.', 'o-neul ga-go sip-seum-ni-da', 'ô-nưn ca-cô xíp-xưm-ni-đa', lang),
        ans('내일 오전에 가고 싶습니다.', 'Tomorrow morning, please.', 'Tôi muốn đến sáng mai.', 'nae-il o-jeo-ne ga-go sip-seum-ni-da', 'ne-in ô-chơ-nê ca-cô xíp-xưm-ni-đa', lang),
        ans('내일 오후에 가고 싶습니다.', 'Tomorrow afternoon, please.', 'Tôi muốn đến chiều mai.', 'nae-il o-hu-e ga-go sip-seum-ni-da', 'ne-in ô-hu-ê ca-cô xíp-xưm-ni-đa', lang),
        ans('가장 빠른 시간에 가고 싶습니다.', 'The earliest time available.', 'Thời gian sớm nhất có thể.', 'ga-jang ppa-reun si-ga-ne ga-go sip-seum-ni-da', 'ca-chang ba-rưn xi-ca-nê ca-cô xíp-xưm-ni-đa', lang),
      ],
    },
    {
      id: 'where',
      q: { ko: '어디가 아프세요?', en: 'Where does it hurt?', vi: 'Bạn bị đau ở đâu?' },
      answers: sym ? [sym] : [],
    },
    {
      id: 'insurance',
      q: { ko: '건강보험 있으세요?', en: 'Do you have health insurance?', vi: 'Bạn có bảo hiểm y tế không?' },
      answers: [
        ans('네, 있습니다.', 'Yes, I do.', 'Vâng, tôi có.', 'ne, it-seum-ni-da', 'nê, ít-xưm-ni-đa', lang),
        ans('없습니다.', 'No, I do not.', 'Tôi không có.', 'eop-seum-ni-da', 'ớp-xưm-ni-đa', lang),
        ans('잘 모르겠습니다.', 'I am not sure.', 'Tôi không rõ.', 'jal mo-reu-get-seum-ni-da', 'chan mô-rư-ghết-xưm-ni-đa', lang),
      ],
    },
    {
      id: 'help',
      q: { ko: '(못 알아들었을 때)', en: '(When you did not understand)', vi: '(Khi bạn không hiểu)' },
      answers: [
        ans('다시 한 번 말씀해 주세요.', 'Please say that again.', 'Xin nhắc lại một lần nữa.', 'da-si han beon mal-sseum-hae ju-se-yo', 'ta-xi han bơn man-xưm-he chu-xê-iô', lang),
        ans('문자로 보내 주세요.', 'Please send it by text message.', 'Xin gửi tin nhắn cho tôi.', 'mun-ja-ro bo-nae ju-se-yo', 'mun-cha-rô pô-ne chu-xê-iô', lang),
      ],
    },
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
}

const FIELD_LABEL: Record<ReportField, Tri> = {
  symptoms: { ko: '증상', en: 'Symptoms', vi: 'Triệu chứng' },
  bodyParts: { ko: '부위', en: 'Body part', vi: 'Vị trí' },
  onset: { ko: '시작 시점', en: 'Started', vi: 'Bắt đầu' },
  circumstance: { ko: '경위', en: 'How it happened', vi: 'Hoàn cảnh' },
  note: { ko: '환자 메모(원문)', en: 'My note (original)', vi: 'Ghi chú (nguyên văn)' },
  baseline: { ko: '기저 정보', en: 'Basic health info', vi: 'Thông tin sức khỏe cơ bản' },
  meds: { ko: '복용 중인 약', en: 'Medicines I take', vi: 'Thuốc đang dùng' },
};

export function fieldLabel(field: ReportField, lang: Lang | 'ko'): string {
  return lang === 'ko' ? FIELD_LABEL[field].ko : pick(FIELD_LABEL[field], lang);
}

function age(birthDate: string): number | null {
  const b = new Date(birthDate);
  if (Number.isNaN(b.getTime())) return null;
  const now = new Date();
  let a = now.getFullYear() - b.getFullYear();
  if (now < new Date(now.getFullYear(), b.getMonth(), b.getDate())) a -= 1;
  return a;
}

function baselineText(p: Profile, key: 'ko' | 'en' | 'vi'): string {
  const parts: string[] = [];
  const a = age(p.birthDate);
  const sex = { male: { ko: '남', en: 'Male', vi: 'Nam' }, female: { ko: '여', en: 'Female', vi: 'Nữ' } }[p.sex];
  if (a !== null) parts.push(key === 'ko' ? `${a}세 ${sex.ko}` : key === 'vi' ? `${a} tuổi, ${sex.vi}` : `${a} y/o, ${sex.en}`);
  if (p.height) parts.push(`${key === 'ko' ? '키' : key === 'vi' ? 'Chiều cao' : 'Height'} ${p.height}cm`);
  if (p.weight) parts.push(`${key === 'ko' ? '체중' : key === 'vi' ? 'Cân nặng' : 'Weight'} ${p.weight}kg`);
  const drink = { none: { ko: '안 함', en: 'none', vi: 'không' }, sometimes: { ko: '가끔', en: 'sometimes', vi: 'thỉnh thoảng' }, often: { ko: '자주', en: 'often', vi: 'thường xuyên' } };
  const smoke = { no: { ko: '안 함', en: 'no', vi: 'không' }, yes: { ko: '함', en: 'yes', vi: 'có' }, quit: { ko: '끊음', en: 'quit', vi: 'đã bỏ' } };
  if (p.drinking) parts.push(`${key === 'ko' ? '음주' : key === 'vi' ? 'Rượu bia' : 'Alcohol'}: ${drink[p.drinking][key]}`);
  if (p.smoking) parts.push(`${key === 'ko' ? '흡연' : key === 'vi' ? 'Hút thuốc' : 'Smoking'}: ${smoke[p.smoking][key]}`);
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
    rows.push({ field, labelKo: FIELD_LABEL[field].ko, valueKo, labelNative: pick(FIELD_LABEL[field], lang), valueNative });
  };
  const syms = intake.symptoms.map((s) => SYMPTOMS[s]);
  const parts = intake.bodyParts.map((p) => BODY_PARTS[p]);
  add('symptoms', joinTerms(syms, 'ko'), joinTerms(syms, lang));
  add('bodyParts', joinTerms(parts, 'ko'), joinTerms(parts, lang));
  if (intake.onset) add('onset', ONSETS[intake.onset].ko, pick(ONSETS[intake.onset], lang));

  const circKo: string[] = [];
  const circNative: string[] = [];
  if (intake.workRelated) {
    circKo.push(`업무 중 발생: ${{ yes: '예', no: '아니요', unknown: '모름' }[intake.workRelated]}`);
    circNative.push(
      lang === 'vi'
        ? `Xảy ra khi làm việc: ${{ yes: 'có', no: 'không', unknown: 'không rõ' }[intake.workRelated]}`
        : `Happened at work: ${{ yes: 'yes', no: 'no', unknown: 'not sure' }[intake.workRelated]}`,
    );
  }
  if (intake.workType) {
    circKo.push(`작업 유형: ${WORK_TYPES[intake.workType].ko}`);
    circNative.push(`${lang === 'vi' ? 'Loại công việc' : 'Type of work'}: ${pick(WORK_TYPES[intake.workType], lang)}`);
  }
  if (intake.industry) {
    circKo.push(`업종: ${INDUSTRIES[intake.industry].ko}`);
    circNative.push(`${lang === 'vi' ? 'Ngành' : 'Industry'}: ${pick(INDUSTRIES[intake.industry], lang)}`);
  }
  add('circumstance', circKo.join(' / '), circNative.join(' / '));
  // 자유 입력은 번역 LLM이 연결되기 전까지 원문 그대로 둔다.
  add('note', intake.freeText ? `${intake.freeText} (원문, 번역 미연결)` : '', intake.freeText);
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
const REQUEST_TYPE_NATIVE: Record<RequestType, Tri> = {
  booking: { ko: '예약 지원', en: 'Booking support', vi: 'Hỗ trợ đặt lịch' },
  interpret: { ko: '통번역', en: 'Interpretation', vi: 'Phiên dịch' },
  policy: { ko: '제도 상담', en: 'Insurance & support advice', vi: 'Tư vấn bảo hiểm, chế độ' },
  referral: { ko: '기관 연계', en: 'Referral to an agency', vi: 'Kết nối cơ quan' },
  other: { ko: '기타', en: 'Other', vi: 'Khác' },
};

export interface CenterSummaryInput {
  intake: Intake;
  emergencyFlag: boolean;
  requestType: RequestType;
  coverage: CoverageResult | null;
  insurance: 'yes' | 'no' | 'unknown' | null;
  contactMethod: ContactMethod | null;
}

/** 사실 요약만 한다. 판단·추측 문장을 넣지 않는다. */
export function buildCenterSummary(i: CenterSummaryInput): { ko: string; native: string } {
  const { intake } = i;
  const lang = intake.language;
  const parts = intake.bodyParts.map((p) => BODY_PARTS[p]);
  const syms = intake.symptoms.map((s) => SYMPTOMS[s]);
  const ko: string[] = [];
  const nv: string[] = [];
  const where = [intake.district ? DISTRICTS[intake.district].ko : null, intake.industry ? `${INDUSTRIES[intake.industry].ko} 업종` : null].filter(Boolean);
  ko.push(`${lang === 'vi' ? '베트남어' : '영어'} 사용 근로자${where.length ? `(${where.join(', ')})` : ''}.`);
  if (parts.length || syms.length) ko.push(`${joinTerms(parts, 'ko') || '부위 미입력'} ${joinTerms(syms, 'ko') || ''}${intake.onset ? `, ${ONSETS[intake.onset].ko} 시작` : ''}.`);
  if (intake.workRelated) ko.push(`업무 중 발생: ${{ yes: '예', no: '아니요', unknown: '모름' }[intake.workRelated]}${intake.workType ? `(${WORK_TYPES[intake.workType].ko})` : ''}.`);
  ko.push(`응급 판정 이력: ${i.emergencyFlag ? '있음' : '없음'}.`);
  if (i.insurance) ko.push(`건강보험증: ${{ yes: '있음', no: '없음', unknown: '모름' }[i.insurance]}.`);
  if (i.coverage) ko.push(`제도 경로 결과: ${PATH_KO[i.coverage.path]}.`);
  ko.push(`요청 유형: ${REQUEST_TYPE_KO[i.requestType]}.`);
  if (i.contactMethod) ko.push(`연락 희망: ${CONTACT_METHOD_KO[i.contactMethod]}.`);

  const L = (en: string, vi: string) => (lang === 'vi' ? vi : en);
  if (parts.length || syms.length) nv.push(`${L('Problem', 'Vấn đề')}: ${joinTerms(syms, lang)} — ${joinTerms(parts, lang)}${intake.onset ? ` (${pick(ONSETS[intake.onset], lang)})` : ''}.`);
  if (intake.workRelated) nv.push(`${L('Happened at work', 'Xảy ra khi làm việc')}: ${pick({ ko: '', en: { yes: 'yes', no: 'no', unknown: 'not sure' }[intake.workRelated], vi: { yes: 'có', no: 'không', unknown: 'không rõ' }[intake.workRelated] }, lang)}.`);
  if (intake.district) nv.push(`${L('Area', 'Khu vực')}: ${pick(DISTRICTS[intake.district], lang)}.`);
  if (intake.industry) nv.push(`${L('Industry', 'Ngành')}: ${pick(INDUSTRIES[intake.industry], lang)}.`);
  if (intake.freeText) nv.push(`${L('My note', 'Ghi chú')}: "${intake.freeText}"`);
  nv.push(`${L('Request', 'Yêu cầu')}: ${pick(REQUEST_TYPE_NATIVE[i.requestType], lang)}.`);
  return { ko: ko.join(' '), native: nv.join('\n') };
}

export function requestTypeNative(t: RequestType, lang: Lang): string {
  return pick(REQUEST_TYPE_NATIVE[t], lang);
}

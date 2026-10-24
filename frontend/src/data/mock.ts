// 데모용 합성 데이터. 실제 개인 정보가 아니다.
// - 센터 접수함 mock 사례 24건
// - 통계 탭용 익명 집계 원천(개인 식별값 없음)

import type { CaseStatus, CenterCase } from '../domain/centerCase';
import { rateUrgency } from '../domain/centerCase';
import { isAfterHours, routeCoverage } from '../domain/coverage';
import type { ContactMethod, RequestType } from '../domain/templates';
import { buildCenterSummary } from '../domain/templates';
import type { Intake } from '../domain/triage';
import type { BodyPart, District, Industry, Lang, Onset, Symptom, WorkType, YesNoUnknown } from '../domain/vocab';

/** 시드 고정 난수(mulberry32): 새로 고쳐도 같은 mock이 나온다. */
function rng(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function weighted<T>(r: () => number, items: [T, number][]): T {
  const total = items.reduce((s, [, w]) => s + w, 0);
  let x = r() * total;
  for (const [v, w] of items) {
    x -= w;
    if (x <= 0) return v;
  }
  return items[items.length - 1]![0];
}

// mock 사례는 실제 이용 비중이 큰 베트남어·영어로만 만든다(한국어 사례는 실제 전송으로만 들어온다).
type MockLang = Exclude<Lang, 'ko'>;

const SCENARIOS: { parts: BodyPart[]; syms: Symptom[]; work: YesNoUnknown; type: WorkType | null; text: Record<MockLang, string> }[] = [
  { parts: ['hand'], syms: ['pain', 'swelling'], work: 'yes', type: 'machine', text: { en: 'My finger got caught in the press machine, it is swollen.', vi: 'Ngón tay bị kẹp vào máy dập, bị sưng.' } },
  { parts: ['back'], syms: ['pain'], work: 'yes', type: 'lifting', text: { en: 'Back pain after lifting heavy parts.', vi: 'Đau lưng sau khi nâng hàng nặng.' } },
  { parts: ['eye'], syms: ['foreign', 'pain'], work: 'yes', type: 'grinding', text: { en: 'Something went into my eye while grinding.', vi: 'Bụi vào mắt khi đang mài.' } },
  { parts: ['arm'], syms: ['burn'], work: 'yes', type: 'welding', text: { en: 'Small burn on my arm from welding.', vi: 'Bị bỏng nhẹ ở tay khi hàn điện.' } },
  { parts: ['whole'], syms: ['fever', 'cough'], work: 'no', type: null, text: { en: 'Fever and cough for three days.', vi: 'Sốt và ho 3 ngày.' } },
  { parts: ['skin'], syms: ['rash'], work: 'unknown', type: 'painting', text: { en: 'Itchy rash on my hands, maybe from paint.', vi: 'Ngứa, mẩn đỏ ở tay, có thể do sơn.' } },
  { parts: ['teeth'], syms: ['pain'], work: 'no', type: null, text: { en: 'Toothache for a week.', vi: 'Đau răng một tuần.' } },
  { parts: ['leg'], syms: ['pain', 'cantmove'], work: 'yes', type: 'assembly', text: { en: 'Knee hurts, hard to walk.', vi: 'Đau đầu gối, khó đi lại.' } },
  { parts: ['abdomen'], syms: ['pain', 'nausea'], work: 'no', type: null, text: { en: 'Stomach pain and vomiting since yesterday.', vi: 'Đau bụng và nôn từ hôm qua.' } },
  { parts: ['hand'], syms: ['cut', 'bleeding'], work: 'yes', type: 'grinding', text: { en: 'Cut my hand on a steel plate.', vi: 'Bị cắt tay vào tấm thép.' } },
  { parts: ['head'], syms: ['dizzy'], work: 'unknown', type: null, text: { en: 'Dizzy often after night shift.', vi: 'Hay chóng mặt sau ca đêm.' } },
  { parts: ['ent'], syms: ['cough', 'pain'], work: 'yes', type: 'painting', text: { en: 'Sore throat and cough, smell of chemicals at work.', vi: 'Đau họng, ho, chỗ làm có mùi hóa chất.' } },
];

const ONSET_POOL: Onset[] = ['today', 'yesterday', 'days', 'week'];
const DISTRICT_W: [District, number][] = [['buk', 30], ['dong', 22], ['ulju', 20], ['nam', 18], ['jung', 10]];
const INDUSTRY_W: [Industry, number][] = [['autoparts', 32], ['shipbuilding', 30], ['chemical', 14], ['construction', 14], ['other', 10]];
const LANG_W: [MockLang, number][] = [['vi', 62], ['en', 38]];
const INS_W: [YesNoUnknown, number][] = [['yes', 55], ['no', 25], ['unknown', 20]];
const REQ_W: [RequestType, number][] = [['booking', 34], ['interpret', 24], ['policy', 24], ['referral', 10], ['other', 8]];
const CONTACT_W: [ContactMethod, number][] = [['phone', 35], ['zalo', 25], ['kakao', 20], ['sms', 15], ['visit', 5]];

export function buildMockCases(now: Date = new Date()): CenterCase[] {
  const r = rng(20261024);
  const cases: CenterCase[] = [];
  for (let n = 0; n < 24; n += 1) {
    const sc = SCENARIOS[n % SCENARIOS.length]!;
    const language = weighted(r, LANG_W);
    // 최근 14일 안, 일부는 운영 시간 외(야간·주말)
    const created = new Date(now.getTime() - (n * 13 + Math.floor(r() * 10) + 2) * 60 * 60 * 1000);
    const intake: Intake = {
      id: `mock-in-${n}`,
      language,
      bodyParts: sc.parts,
      symptoms: sc.syms,
      freeText: sc.text[language],
      onset: ONSET_POOL[Math.floor(r() * ONSET_POOL.length)]!,
      workRelated: sc.work,
      workType: sc.type,
      industry: weighted(r, INDUSTRY_W),
      district: weighted(r, DISTRICT_W),
      createdAt: created.toISOString(),
    };
    const insurance = weighted(r, INS_W);
    const emergencyFlag = r() < 0.08;
    const requestType = weighted(r, REQ_W);
    const contactMethod = weighted(r, CONTACT_W);
    const coverage = routeCoverage({ workRelated: sc.work, insurance, ulsan90: insurance === 'no' ? weighted(r, [['yes', 1], ['no', 1]] as [YesNoUnknown, number][]) : null });
    const summary = buildCenterSummary({ intake, emergencyFlag, requestType, coverage, insurance, contactMethod });
    const { urgency, reasons } = rateUrgency({ emergencyFlag, workRelated: sc.work, insurance });
    const status: CaseStatus = n < 5 ? 'new' : n < 12 ? weighted(r, [['progress', 2], ['new', 1]] as [CaseStatus, number][]) : weighted(r, [['done', 3], ['progress', 1]] as [CaseStatus, number][]);
    cases.push({
      id: `C-${String(1000 + 24 - n)}`,
      createdAt: created.toISOString(),
      language,
      requestType,
      urgency,
      urgencyReasons: reasons,
      district: intake.district,
      industry: intake.industry,
      status,
      summaryKo: summary.ko,
      originalNative: summary.native,
      consentedItems: ['증상', '부위', '시작 시점', '경위', '자유 입력 메모'],
      coveragePath: coverage.path,
      contactMethod,
      contact: contactMethod === 'visit' ? null : '010-0000-00' + String(10 + n),
      afterHours: isAfterHours(created),
      emergencyFlag,
      workRelated: sc.work,
      insurance,
      live: false,
    });
  }
  return cases;
}

// ---------------------------------------------------------------------------
// 통계 원천: 익명 레코드(날짜·구군·업종·언어·보험·시간외)만 둔다.
// ---------------------------------------------------------------------------
export interface StatRecord {
  date: Date;
  district: District;
  industry: Industry;
  language: Lang;
  insurance: YesNoUnknown;
  afterHours: boolean;
  requestType: RequestType;
  workRelated: YesNoUnknown;
}

export function buildStatRecords(now: Date = new Date()): StatRecord[] {
  const r = rng(77);
  const out: StatRecord[] = [];
  for (let n = 0; n < 420; n += 1) {
    out.push({
      date: new Date(now.getTime() - Math.floor(r() * 180) * 86400000),
      district: weighted(r, DISTRICT_W),
      industry: weighted(r, INDUSTRY_W),
      language: weighted(r, LANG_W),
      insurance: weighted(r, INS_W),
      afterHours: r() < 0.41,
      requestType: weighted(r, REQ_W),
      workRelated: weighted(r, [['yes', 48], ['no', 34], ['unknown', 18]] as [YesNoUnknown, number][]),
    });
  }
  return out;
}

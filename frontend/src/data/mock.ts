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
export function rng(seed: number) {
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

// mock 사례 언어는 센터 회신(2026-10-31) 국적 비중을 따른다(한국어 사례는 실제 전송으로만 들어온다).
// 장면은 회신에 많던 상담(치과·소화기·산부인과 통역, 건강보험증 문의)과 업무 중 부상을 섞은 합성 문장이다. vi·en 밖은 기계 번역 초안.
type MockLang = Extract<Lang, 'ru' | 'id' | 'si' | 'en' | 'tl' | 'vi'>;

const SCENARIOS: { parts: BodyPart[]; syms: Symptom[]; work: YesNoUnknown; type: WorkType | null; text: Record<MockLang, string> }[] = [
  { parts: ['teeth'], syms: ['pain'], work: 'no', type: null, text: { en: 'My tooth has hurt for a week. I need an interpreter at the dentist.', ru: 'Уже неделю болит зуб. Нужен переводчик у стоматолога.', id: 'Gigi saya sakit sudah seminggu. Saya butuh penerjemah di dokter gigi.', si: 'සතියක් තිස්සේ දතේ කැක්කුමක් තියෙනවා. දන්ත වෛද්‍යවරයා ළඟ භාෂා පරිවර්තකයෙක් ඕනේ.', tl: 'Isang linggo nang masakit ang ngipin ko. Kailangan ko ng interpreter sa dentista.', vi: 'Đau răng một tuần. Tôi cần phiên dịch khi đi nha sĩ.' } },
  { parts: ['abdomen'], syms: ['pain', 'nausea'], work: 'no', type: null, text: { en: 'Stomach pain and vomiting since yesterday. Which hospital should I go to?', ru: 'Со вчерашнего дня болит живот и рвота. В какую больницу идти?', id: 'Sakit perut dan muntah sejak kemarin. Harus ke rumah sakit mana?', si: 'ඊයේ ඉඳන් බඩේ කැක්කුමයි වමනයයි. කොයි රෝහලට යන්නද?', tl: 'Masakit ang tiyan at nagsusuka mula kahapon. Saang ospital ako pupunta?', vi: 'Đau bụng và nôn từ hôm qua. Tôi nên đến bệnh viện nào?' } },
  { parts: ['hand'], syms: ['cut', 'bleeding'], work: 'yes', type: 'grinding', text: { en: 'Cut my hand on a steel plate at the shipyard.', ru: 'Порезал руку стальным листом на верфи.', id: 'Tangan saya teriris pelat baja di galangan kapal.', si: 'නැව් හදන තැනදී වානේ තහඩුවකින් අත කැපුණා.', tl: 'Nahiwa ang kamay ko sa bakal na plato sa shipyard.', vi: 'Bị cắt tay vào tấm thép ở xưởng đóng tàu.' } },
  { parts: ['abdomen'], syms: ['pain'], work: 'no', type: null, text: { en: 'Lower belly pain. I want to see a women\'s doctor with an interpreter.', ru: 'Болит низ живота. Хочу к гинекологу с переводчиком.', id: 'Perut bagian bawah sakit. Saya ingin ke dokter kandungan dengan penerjemah.', si: 'යටි බඩේ කැක්කුමක් තියෙනවා. පරිවර්තකයෙක් එක්ක නාරිවේද වෛද්‍යවරයෙක් හමුවෙන්න ඕනේ.', tl: 'Masakit ang puson ko. Gusto kong magpatingin sa OB-GYN na may interpreter.', vi: 'Đau bụng dưới. Tôi muốn khám phụ khoa có phiên dịch.' } },
  { parts: ['back'], syms: ['pain'], work: 'yes', type: 'lifting', text: { en: 'Back pain after lifting heavy parts.', ru: 'Болит спина после подъёма тяжёлых деталей.', id: 'Sakit punggung setelah mengangkat barang berat.', si: 'බර කොටස් ඉසිලුවාට පස්සේ කොන්දේ කැක්කුමක්.', tl: 'Masakit ang likod pagkatapos magbuhat ng mabibigat na piyesa.', vi: 'Đau lưng sau khi nâng hàng nặng.' } },
  { parts: ['eye'], syms: ['foreign', 'pain'], work: 'yes', type: 'grinding', text: { en: 'Something went into my eye while grinding.', ru: 'Во время шлифовки что-то попало в глаз.', id: 'Ada sesuatu masuk ke mata saat menggerinda.', si: 'ග්‍රයින්ඩ් කරද්දී ඇහැට මොකක්හරි ගියා.', tl: 'May pumasok sa mata ko habang naggi-grinding.', vi: 'Bụi vào mắt khi đang mài.' } },
  { parts: ['whole'], syms: ['fever', 'cough'], work: 'no', type: null, text: { en: 'Fever and cough for three days. My health insurance card has not come yet.', ru: 'Температура и кашель три дня. Карту медстраховки ещё не получил.', id: 'Demam dan batuk tiga hari. Kartu asuransi kesehatan saya belum datang.', si: 'දවස් තුනක් තිස්සේ උණයි කැස්සයි. සෞඛ්‍ය රක්ෂණ කාඩ්පත තවම ලැබුණේ නෑ.', tl: 'Lagnat at ubo nang tatlong araw. Wala pa ang health insurance card ko.', vi: 'Sốt và ho 3 ngày. Tôi chưa nhận được thẻ bảo hiểm y tế.' } },
  { parts: ['arm'], syms: ['burn'], work: 'yes', type: 'welding', text: { en: 'Small burn on my arm from welding.', ru: 'Небольшой ожог руки от сварки.', id: 'Luka bakar kecil di lengan karena mengelas.', si: 'වෙල්ඩින් කරද්දී අතේ පොඩි පිළිස්සීමක්.', tl: 'Maliit na paso sa braso dahil sa welding.', vi: 'Bị bỏng nhẹ ở tay khi hàn điện.' } },
  { parts: ['leg'], syms: ['pain', 'cantmove'], work: 'yes', type: 'assembly', text: { en: 'Knee hurts, hard to walk.', ru: 'Болит колено, трудно ходить.', id: 'Lutut sakit, susah berjalan.', si: 'දණහිස රිදෙනවා, ඇවිදින්න අමාරුයි.', tl: 'Masakit ang tuhod, hirap maglakad.', vi: 'Đau đầu gối, khó đi lại.' } },
  { parts: ['skin'], syms: ['rash'], work: 'unknown', type: 'painting', text: { en: 'Itchy rash on my hands, maybe from paint.', ru: 'Зудящая сыпь на руках, возможно от краски.', id: 'Ruam gatal di tangan, mungkin karena cat.', si: 'අත්වල කසන බිබිලි, සමහරවිට තීන්ත නිසා වෙන්න ඇති.', tl: 'Makating pantal sa kamay, baka dahil sa pintura.', vi: 'Ngứa, mẩn đỏ ở tay, có thể do sơn.' } },
  { parts: ['head'], syms: ['dizzy'], work: 'unknown', type: null, text: { en: 'Dizzy often after night shift.', ru: 'Часто кружится голова после ночной смены.', id: 'Sering pusing setelah shift malam.', si: 'රාත්‍රී මුරයෙන් පස්සේ නිතර ඔලුව කැරකෙනවා.', tl: 'Madalas nahihilo pagkatapos ng night shift.', vi: 'Hay chóng mặt sau ca đêm.' } },
  { parts: ['ent'], syms: ['cough', 'pain'], work: 'yes', type: 'painting', text: { en: 'Sore throat and cough, smell of chemicals at work.', ru: 'Болит горло и кашель, на работе пахнет химией.', id: 'Sakit tenggorokan dan batuk, di tempat kerja ada bau bahan kimia.', si: 'උගුරේ අමාරුවයි කැස්සයි, වැඩපොළේ රසායන ගඳක් තියෙනවා.', tl: 'Masakit ang lalamunan at may ubo, amoy kemikal sa trabaho.', vi: 'Đau họng, ho, chỗ làm có mùi hóa chất.' } },
];

const ONSET_POOL: Onset[] = ['today', 'yesterday', 'days', 'week'];
// 구군: 회신 주소 중 구까지 적힌 건만(동구 센터 회신이라 동구가 많다, 중구는 0건)
const DISTRICT_W: [District, number][] = [['dong', 196], ['buk', 20], ['ulju', 17], ['nam', 8]];
const INDUSTRY_W: [Industry, number][] = [['autoparts', 32], ['shipbuilding', 30], ['chemical', 14], ['construction', 14], ['other', 10]];
const LANG_W: [MockLang, number][] = [['ru', 44], ['id', 25], ['si', 15], ['en', 8], ['tl', 4], ['vi', 2]];
const INS_W: [YesNoUnknown, number][] = [['yes', 55], ['no', 25], ['unknown', 20]];
// 요청 종류: 회신 상담은 대부분 진료 통역이고, 건강보험 문의가 12%다
const REQ_W: [RequestType, number][] = [['interpret', 50], ['booking', 20], ['policy', 15], ['referral', 10], ['other', 5]];
// 연락 방식: 회신 상담 방법 전화 67%, 방문·출장 30%
const CONTACT_W: [ContactMethod, number][] = [['phone', 67], ['visit', 30], ['kakao', 3]];

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
    // 사례마다 하나씩 뽑는다(시드 순서를 지키려고 여러 개를 뽑지 않는다)
    const requestTypes = [weighted(r, REQ_W)];
    const contactMethod = weighted(r, CONTACT_W);
    const coverage = routeCoverage({ workRelated: sc.work, insurance, ulsan90: insurance === 'no' ? weighted(r, [['yes', 1], ['no', 1]] as [YesNoUnknown, number][]) : null });
    const summary = buildCenterSummary({ intake, requestTypes, coverage, insurance, contactMethod });
    const { urgency, reasons } = rateUrgency({ workRelated: sc.work, insurance });
    const status: CaseStatus = n < 5 ? 'new' : n < 12 ? weighted(r, [['progress', 2], ['new', 1]] as [CaseStatus, number][]) : weighted(r, [['done', 3], ['progress', 1]] as [CaseStatus, number][]);
    cases.push({
      id: `C-${String(1000 + 24 - n)}`,
      createdAt: created.toISOString(),
      language,
      requestTypes,
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
      workRelated: sc.work,
      insurance,
      live: false,
    });
  }
  return cases;
}

// ---------------------------------------------------------------------------
// 통계 원천: 익명 레코드(날짜·구군·업종·언어·보험·시간외)만 둔다.
// 날짜·구군·언어·시간외·요청 종류 비율은 센터 회신(2026-10-31, 동구 센터 의료 상담 329건)의 분포를 따른 합성값이다.
// 업종·보험·업무 관련은 회신에 없어 이전 가중치 그대로다.
// ---------------------------------------------------------------------------
const STAT_COUNT = 329;
// 최근 6개월 월별 건수(오래된 달부터, 마지막이 이번 달)
const STAT_MONTH_W = [16, 25, 41, 85, 97, 65];
// 국적 → 언어: 러시아·카자흐스탄·우즈베키스탄·키르기스스탄·타지키스탄 → 러시아어, 인도네시아, 스리랑카 → 싱할라어, 필리핀 → 영어·필리핀어
const STAT_LANG_W: [Lang, number][] = [['ru', 44], ['id', 25], ['si', 15], ['en', 8], ['tl', 4], ['vi', 2], ['ko', 2]];
// 운영 시간 외 25건 + 주말 27건 = 52 / 329
const STAT_AFTER_HOURS = 52 / 329;
const KST_MS = 9 * 3600000;

/** 난수 하나로 최근 6개월 중 한 날을 고른다. 달은 STAT_MONTH_W 비율, 날은 그 달 안에서 고르게(이번 달은 오늘까지). */
function statDate(now: Date, u: number): Date {
  const k = new Date(now.getTime() + KST_MS);
  const total = STAT_MONTH_W.reduce((s, w) => s + w, 0);
  let x = u * total;
  let i = 0;
  while (i < STAT_MONTH_W.length - 1 && x >= STAT_MONTH_W[i]!) {
    x -= STAT_MONTH_W[i]!;
    i += 1;
  }
  const back = STAT_MONTH_W.length - 1 - i;
  const span = back === 0 ? k.getUTCDate() : new Date(Date.UTC(k.getUTCFullYear(), k.getUTCMonth() - back + 1, 0)).getUTCDate();
  const day = 1 + Math.floor((x / STAT_MONTH_W[i]!) * span);
  const t = Date.UTC(k.getUTCFullYear(), k.getUTCMonth() - back, day, k.getUTCHours(), k.getUTCMinutes(), k.getUTCSeconds(), k.getUTCMilliseconds());
  return new Date(t - KST_MS);
}

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
  for (let n = 0; n < STAT_COUNT; n += 1) {
    out.push({
      date: statDate(now, r()),
      district: weighted(r, DISTRICT_W),
      industry: weighted(r, INDUSTRY_W),
      language: weighted(r, STAT_LANG_W),
      insurance: weighted(r, INS_W),
      afterHours: r() < STAT_AFTER_HOURS,
      requestType: weighted(r, REQ_W),
      workRelated: weighted(r, [['yes', 48], ['no', 34], ['unknown', 18]] as [YesNoUnknown, number][]),
    });
  }
  return out;
}

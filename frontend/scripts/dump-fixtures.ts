// 백엔드 규칙 동기화 테스트(backend/tests/test_parity.py)의 기대값을 프론트 도메인 함수로 만든다.
// 사람이 기대값을 적지 않는다. 입력 목록만 여기에 두고 출력은 프론트 코드가 낸다.
//
//   cd frontend
//   npx rolldown scripts/dump-fixtures.ts --file /tmp/dump.mjs --format esm \
//     && TZ=Asia/Seoul node /tmp/dump.mjs > ../backend/tests/fixtures/parity.json
//
// 운영 시간·mock 시각은 로컬 시각을 쓰므로 반드시 TZ=Asia/Seoul로 실행한다.

import { buildMockCases, buildStatRecords, rng } from '../src/data/mock';
import { defaultCategory, rateUrgency } from '../src/domain/centerCase';
import type { CoverageInput, CoveragePath } from '../src/domain/coverage';
import { isAfterHours, nextOpenDay, routeCoverage } from '../src/domain/coverage';
import type { ContactMethod, Profile, ReportField, RequestType } from '../src/domain/templates';
import { buildCallScript, buildCenterSummary, buildClinicianReport, buildDeskSheet, REPORT_FIELDS } from '../src/domain/templates';
import type { Intake } from '../src/domain/triage';
import { extractFromText, mergeExtraction, recommendDepartment, triage } from '../src/domain/triage';
import type { BodyPart, Lang, Symptom, YesNoUnknown } from '../src/domain/vocab';
import { BODY_PARTS, LANGS, SYMPTOMS } from '../src/domain/vocab';

if (new Date('2026-10-26T00:00:00Z').getHours() !== 9) {
  throw new Error('TZ=Asia/Seoul로 실행해야 한다');
}

const NOW = new Date('2026-10-26T01:00:00.000Z');

const intake = (over: Partial<Intake>): Intake => ({
  id: 'in-test',
  language: 'en',
  bodyParts: [],
  symptoms: [],
  freeText: '',
  onset: null,
  workRelated: null,
  workType: null,
  industry: null,
  district: null,
  createdAt: NOW.toISOString(),
  ...over,
});

// ---------------------------------------------------------------------------
// 진료과(응급 여부는 판정하지 않는다, backlog 43)
// ---------------------------------------------------------------------------
const triageInputs: Intake[] = [];
// 진료과 규칙표: 부위 × 증상 한 쌍씩 전부
for (const b of Object.keys(BODY_PARTS) as BodyPart[]) {
  for (const s of Object.keys(SYMPTOMS) as Symptom[]) {
    triageInputs.push(intake({ bodyParts: [b], symptoms: [s] }));
  }
}
// 여러 부위·증상 조합과 빈 입력
triageInputs.push(
  intake({ bodyParts: ['skin', 'hand'], symptoms: ['chemical', 'rash'] }),
  intake({ bodyParts: ['eye', 'hand'], symptoms: ['cut'] }),
  intake({ bodyParts: ['teeth', 'head'], symptoms: ['burn'] }),
  intake({ bodyParts: ['head', 'arm'], symptoms: ['numb'] }),
  intake({ bodyParts: ['head', 'abdomen'], symptoms: ['pain'] }),
  intake({ bodyParts: ['chest', 'back'], symptoms: ['pain'] }),
  intake({ bodyParts: [], symptoms: [] }),
  intake({ bodyParts: ['hand'], symptoms: [] }),
  intake({ bodyParts: [], symptoms: ['pain'], freeText: 'I fell from a ladder' }),
  intake({ language: 'en', bodyParts: ['arm'], symptoms: ['rash'], freeText: 'Rash after painting the ship' }),
);

// ---------------------------------------------------------------------------
// 자유 입력 추출
// ---------------------------------------------------------------------------
const EXTRACT_TEXTS = [
  'Ngón tay bị kẹp vào máy dập, bị sưng.',
  'Tôi bị đau lưng ở nhà máy hôm qua.',
  'Tôi bị đau lưng ở nhà sau giờ làm.',
  'Bụi vào mắt khi đang mài.',
  'Bị bỏng nhẹ ở tay khi hàn điện.',
  'Sốt và ho 3 ngày.',
  'Ngứa, mẩn đỏ ở tay, có thể do sơn.',
  'Đau răng một tuần.',
  'Đau bụng và nôn từ hôm qua.',
  'Da bị rát sau khi tiếp xúc hóa chất',
  'My finger got caught in the press machine, it is swollen.',
  'Back pain after lifting heavy parts.',
  'Rash after painting the ship',
  'I hurt my knee at work this morning',
  'I have a cough, fever and my throat is sore for a few days',
  'Something in my eye while grinding',
  'I cut my hand at home last night and it bleeds',
  'My ear hurts',
  'Stomach ache for a week',
  'pain',
  '프레스 기계에 손가락이 끼어서 부었어요',
  '무거운 걸 들다가 허리를 다쳤어요. 어제부터 아파요',
  '용접하다가 팔에 화상을 입었어요',
  '집에서 넘어져서 무릎이 아파요',
  '며칠째 기침하고 열이 나요',
  '눈에 뭐가 들어갔어요',
  '공장에서 시너 냄새를 맡고 어지러워요',
  '온몸이 가렵고 두드러기가 났어요',
  '',
];
const extractCases = EXTRACT_TEXTS.flatMap((freeText, n) => {
  const empty = intake({ language: (['vi', 'en', 'ko'] as Lang[])[n % 3]!, freeText });
  const preset = intake({ language: 'en', freeText, bodyParts: ['leg'], onset: 'week', workRelated: 'no' });
  return [empty, preset].map((i) => {
    const extraction = extractFromText(i.freeText);
    return { input: i, output: { extraction, intake: mergeExtraction(i, extraction) } };
  });
});

// ---------------------------------------------------------------------------
// 제도 경로·긴급도
// ---------------------------------------------------------------------------
const YNU: YesNoUnknown[] = ['yes', 'no', 'unknown'];
const routeCases: { input: CoverageInput; output: unknown }[] = [];
for (const workRelated of YNU) {
  for (const insurance of YNU) {
    for (const ulsan90 of [...YNU, null]) {
      const input = { workRelated, insurance, ulsan90 };
      routeCases.push({ input, output: routeCoverage(input) });
    }
  }
}

const urgencyCases = [...YNU, null].flatMap((workRelated) =>
  [...YNU, null].map((insurance) => {
    const input = { workRelated, insurance };
    return { input, output: rateUrgency(input) };
  }),
);

// 센터 사례 분야 기본값(backlog 41): 경로 다섯(없음 포함) × 요청 종류 조합
const PATHS: (CoveragePath | null)[] = ['industrial', 'nhis', 'ulsanSupport', 'center', null];
const CATEGORY_REQUESTS: RequestType[][] = [[], ['policy'], ['interpret'], ['policy', 'interpret'], ['booking', 'policy'], ['referral'], ['other']];
const categoryCases = PATHS.flatMap((coveragePath) =>
  CATEGORY_REQUESTS.map((requestTypes) => {
    const input = { coveragePath, requestTypes };
    return { input, output: defaultCategory(input) };
  }),
);

// ---------------------------------------------------------------------------
// 템플릿: 언어 20종 × 첫 방문 여부 × 업무 관련 여부
// ---------------------------------------------------------------------------
const TEMPLATE_INTAKES: Partial<Intake>[] = [
  { bodyParts: ['hand'], symptoms: ['cut', 'bleeding'], onset: 'today', workType: 'grinding', industry: 'shipbuilding', district: 'dong', freeText: 'Cut on a steel plate' },
  { bodyParts: ['head', 'eye'], symptoms: ['pain'], onset: null },
  { bodyParts: ['back'], symptoms: ['swelling'], onset: 'days', workType: 'lifting', industry: 'autoparts' },
  { bodyParts: ['abdomen'], symptoms: ['nausea', 'dizzy'], onset: 'week', district: 'ulju', freeText: '어제부터 토했어요' },
  { bodyParts: [], symptoms: [] },
];
const WORK: (YesNoUnknown | null)[] = ['yes', 'no', 'unknown', null];

const deskCases: unknown[] = [];
const callCases: unknown[] = [];
for (const lang of LANGS) {
  TEMPLATE_INTAKES.forEach((over, n) => {
    for (const workRelated of WORK) {
      const i = intake({ ...over, language: lang, workRelated });
      const department = i.bodyParts.length && i.symptoms.length ? recommendDepartment(i.bodyParts, i.symptoms).primary : 'family';
      for (const firstVisit of [true, false]) {
        deskCases.push({ input: { intake: i, department, firstVisit, lang }, output: buildDeskSheet(i, department, firstVisit, lang) });
      }
      if (workRelated === WORK[n % WORK.length]) {
        callCases.push({ input: { intake: i, department, lang }, output: buildCallScript(i, department, lang) });
      }
    }
  });
}

const PROFILES: (Profile | null)[] = [
  null,
  { birthDate: '1995-03-10', sex: 'male', height: 170, weight: 65.5, drinking: 'sometimes', smoking: 'quit' },
  { birthDate: '2000-12-31', sex: 'female', height: null, weight: null, drinking: null, smoking: 'no' },
  { birthDate: 'not-a-date', sex: 'female', height: 158.2, weight: 0, drinking: 'often', smoking: null },
];
const INCLUDED: ReportField[][] = [[...REPORT_FIELDS], ['symptoms', 'bodyParts', 'note'], []];
const clinicianCases: unknown[] = [];
for (const lang of LANGS) {
  TEMPLATE_INTAKES.forEach((over, n) => {
    const i = intake({ ...over, language: lang, workRelated: WORK[n % WORK.length]! });
    INCLUDED.forEach((included, k) => {
      const profile = PROFILES[(n + k) % PROFILES.length]!;
      const meds = k === 0 ? 'Paracetamol 500mg' : '';
      const { id: _id, createdAt: _createdAt, ...output } = buildClinicianReport(i, included, profile, meds);
      clinicianCases.push({ input: { intake: i, included, profile, meds }, output });
    });
  });
}

const REQUESTS: RequestType[] = ['booking', 'interpret', 'policy', 'referral', 'other'];
const CONTACTS: (ContactMethod | null)[] = ['phone', 'sms', 'kakao', 'zalo', 'visit', null];
const INSURANCE: (YesNoUnknown | null)[] = ['yes', 'no', 'unknown', null];
const centerCases: unknown[] = [];
let k = 0;
for (const lang of LANGS) {
  for (const over of TEMPLATE_INTAKES) {
    for (const workRelated of WORK) {
      const i = intake({ ...over, language: lang, workRelated });
      const insurance = INSURANCE[k % INSURANCE.length]!;
      const coverage = k % 3 === 0 ? null : routeCoverage({ workRelated: workRelated ?? 'unknown', insurance: insurance ?? 'unknown', ulsan90: k % 2 ? 'yes' : 'no' });
      const input = {
        intake: i,
        // 넷에 하나는 둘을 고른다(backlog 37)
        requestTypes: k % 4 === 0 ? [REQUESTS[k % REQUESTS.length]!, REQUESTS[(k + 1) % REQUESTS.length]!] : [REQUESTS[k % REQUESTS.length]!],
        coverage,
        insurance,
        contactMethod: CONTACTS[k % CONTACTS.length]!,
      };
      centerCases.push({ input, output: buildCenterSummary(input) });
      k += 1;
    }
  }
}

// ---------------------------------------------------------------------------
// 운영 시간(Asia/Seoul)
// ---------------------------------------------------------------------------
const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const hoursCases: unknown[] = [];
// 2026-10-23(금) 00:00 KST부터 5일 동안 1시간 간격 + 경계 직전·직후
for (let h = 0; h < 24 * 5; h += 1) {
  const base = new Date(Date.UTC(2026, 9, 22, 15) + h * 3600000);
  for (const at of [base, new Date(base.getTime() - 1)]) {
    hoursCases.push({ input: at.toISOString(), output: { afterHours: isAfterHours(at), nextOpenDate: ymd(nextOpenDay(at)) } });
  }
}

// ---------------------------------------------------------------------------
// mock 데이터
// ---------------------------------------------------------------------------
const firstTen = (seed: number) => {
  const r = rng(seed);
  return Array.from({ length: 10 }, () => r());
};

const out = {
  generatedAt: new Date().toISOString(),
  now: NOW.toISOString(),
  triage: triageInputs.map((input) => ({ input, output: triage(input) })),
  extract: extractCases,
  route: routeCases,
  urgency: urgencyCases,
  category: categoryCases,
  desk: deskCases,
  call: callCases,
  clinician: clinicianCases,
  center: centerCases,
  hours: hoursCases,
  rng: { 20261024: firstTen(20261024), 77: firstTen(77) },
  mockCases: buildMockCases(NOW),
  statRecords: buildStatRecords(NOW).map((r) => ({ ...r, date: r.date.toISOString() })),
};

console.log(JSON.stringify(out, null, 1));

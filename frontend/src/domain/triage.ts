// 증상 분류(POST /triage 대응)를 브라우저 안에서 흉내 낸다.
// - 응급 여부는 판정하지 않는다(backlog 43). 틀린 판정이 헛된 확신을 주지 않게, 119는 판정 없이 늘 보이는 버튼으로만 안내한다.
// - 증상 추출: LLM 자리. 데모에서는 다국어 키워드 사전으로 추출하고, 못 찾은 항목은 버튼으로 다시 묻는다.
// - 진료과 추천: 결정적 규칙표. 같은 입력이면 같은 결과.

import type { BodyPart, Department, District, Industry, Lang, Onset, Symptom, WorkType, YesNoUnknown } from './vocab';

export interface Intake {
  id: string;
  language: Lang;
  bodyParts: BodyPart[];
  symptoms: Symptom[];
  freeText: string;
  onset: Onset | null;
  workRelated: YesNoUnknown | null;
  workType: WorkType | null;
  industry: Industry | null;
  district: District | null;
  createdAt: string;
  // 손상(외상) 여부. 진료과 모델 B 입력(backend backlog 10). 규칙은 쓰지 않는다. 답하지 않으면 키를 넣지 않는다(서버도 응답에서 뺀다).
  injury?: boolean;
}

export interface TriageResult {
  department: { primary: Department; alt: Department } | null;
  missing: ('bodyParts' | 'symptoms')[];
}

// ---------------------------------------------------------------------------
// 진료과 규칙표
// ---------------------------------------------------------------------------
const MSK: BodyPart[] = ['back', 'arm', 'hand', 'leg', 'foot'];

export function recommendDepartment(bodyParts: BodyPart[], symptoms: Symptom[]): { primary: Department; alt: Department } {
  const b = new Set(bodyParts);
  const s = new Set(symptoms);
  if (s.has('chemical')) return { primary: 'occ', alt: b.has('skin') ? 'derm' : 'internal' };
  if (b.has('eye') || s.has('foreign')) return { primary: 'ophth', alt: 'family' };
  if (b.has('teeth')) return { primary: 'dental', alt: 'family' };
  if (s.has('burn')) return { primary: 'surgery', alt: 'derm' };
  if (s.has('cut') || s.has('bleeding')) {
    return { primary: 'surgery', alt: MSK.some((p) => b.has(p)) ? 'ortho' : 'family' };
  }
  if (b.has('skin') || s.has('rash')) return { primary: 'derm', alt: 'family' };
  if (b.has('ent') || s.has('cough')) return { primary: 'ent', alt: 'internal' };
  if (MSK.some((p) => b.has(p))) return { primary: 'ortho', alt: s.has('numb') ? 'neuro' : 'family' };
  if (b.has('head')) return { primary: 'neuro', alt: 'internal' };
  if (b.has('abdomen') || b.has('chest') || b.has('whole') || s.has('fever') || s.has('nausea') || s.has('dizzy')) {
    return { primary: 'internal', alt: 'family' };
  }
  return { primary: 'family', alt: 'internal' };
}

export function triage(intake: Intake): TriageResult {
  const missing: TriageResult['missing'] = [];
  if (intake.bodyParts.length === 0) missing.push('bodyParts');
  if (intake.symptoms.length === 0) missing.push('symptoms');
  return {
    department: missing.length === 0 ? recommendDepartment(intake.bodyParts, intake.symptoms) : null,
    missing,
  };
}

// ---------------------------------------------------------------------------
// 자유 입력 추출(LLM 자리). 찾지 못한 값은 null로 두고 추측하지 않는다.
// ---------------------------------------------------------------------------
const includesAny = (text: string, words: string[]) => words.some((w) => text.includes(w));

const BODY_WORDS: Record<BodyPart, string[]> = {
  head: ['머리', 'head', 'đầu'],
  eye: ['눈', 'eye', 'mắt'],
  ent: ['귀', '코', '목구멍', ' ear', 'nose', 'throat', ' tai', 'mũi', 'họng'],
  teeth: ['이빨', '치아', '잇몸', 'tooth', 'teeth', 'gum', 'răng', 'lợi'],
  chest: ['가슴', 'chest', 'ngực'],
  abdomen: ['배가', '복부', 'stomach', 'belly', 'abdomen', 'bụng'],
  back: ['허리', '등이', 'my back', 'lower back', 'waist', 'lưng'],
  arm: ['팔', '어깨', ' arm', 'shoulder', 'cánh tay', 'vai'],
  hand: ['손', 'hand', 'finger', 'wrist', 'bàn tay', 'ngón tay', 'cổ tay'],
  leg: ['다리', '무릎', 'leg', 'knee', 'đầu gối', 'chân'],
  foot: ['발', 'foot', 'feet', 'ankle', 'toe', 'bàn chân', 'cổ chân'],
  skin: ['피부', 'skin', 'da '],
  whole: ['온몸', '전신', 'whole body', 'all over', 'toàn thân', 'khắp người'],
};

const SYMPTOM_WORDS: Record<Symptom, string[]> = {
  // 'painting'과 겹치지 않도록 영어 pain은 끝 경계를 붙인다.
  pain: ['아파', '아프', '통증', 'pain ', 'pain,', 'pain.', 'painful', 'hurt', 'ache', 'đau'],
  swelling: ['붓', '부었', 'swell', 'swollen', 'sưng'],
  cut: ['베였', '베인', '찢어', 'cut', 'wound', 'vết cắt', 'bị cắt', 'rách'],
  bleeding: ['피가', '출혈', 'bleed', 'blood', 'chảy máu', 'máu'],
  burn: ['화상', '데었', 'burn', 'bỏng'],
  numb: ['저려', '저림', 'numb', 'tingl', 'tê'],
  cantmove: ['못 움직', '움직일 수 없', "can't move", 'cannot move', 'không cử động', 'khó cử động'],
  fever: ['열이', '열나', 'fever', 'sốt'],
  cough: ['기침', 'cough', ' ho ', ' ho,'],
  dizzy: ['어지러', 'dizzy', 'chóng mặt', 'choáng'],
  rash: ['가려', '두드러기', '발진', 'itch', 'rash', 'ngứa', 'phát ban', 'mẩn'],
  nausea: ['토했', '구토', '메스꺼', 'vomit', 'nausea', 'threw up', 'buồn nôn', 'nôn'],
  breath: ['숨쉬기', '숨이 차', 'breath', 'khó thở'],
  chemical: ['화학', '약품', '시너', 'chemical', 'solvent', 'thinner', 'hóa chất', 'dung môi'],
  foreign: ['눈에 뭐가', '이물', 'something in my eye', 'dust in my eye', 'bụi vào mắt', 'dị vật'],
};

const ONSET_WORDS: Record<Onset, string[]> = {
  today: ['오늘', '방금', 'today', 'just now', 'this morning', 'tonight', 'hôm nay', 'vừa', 'sáng nay', 'tối nay'],
  yesterday: ['어제', 'yesterday', 'last night', 'hôm qua', 'tối qua'],
  days: ['며칠', '2일', '3일', 'few days', '2 days', '3 days', 'vài ngày', '2 ngày', '3 ngày'],
  week: ['일주일', '한 달', 'week', 'month', 'tuần', 'tháng'],
};

const WORK_WORDS = ['일하다', '작업', '공장', '회사에서', 'at work', 'while working', 'factory', 'machine', 'đang làm', 'lúc làm', 'ở công ty', 'nhà máy', 'máy'];
const NOT_WORK_WORDS = ['집에서', '퇴근 후', 'at home', 'after work', 'ở nhà', 'sau giờ làm'];

const WORK_TYPE_WORDS: Record<WorkType, string[]> = {
  welding: ['용접', 'weld', 'thợ hàn', 'máy hàn', 'hàn điện', 'đang hàn'],
  lifting: ['들다가', '무거운', '운반', 'lift', 'carry', 'nâng', 'khuân', 'bê '],
  machine: ['프레스', '기계', 'press', 'machine', 'máy dập', 'máy'],
  grinding: ['연마', '그라인더', 'grind', 'grinder', 'mài'],
  painting: ['도장', '페인트', 'paint', 'sơn'],
  assembly: ['조립', 'assembl', 'lắp ráp'],
};

export interface Extraction {
  bodyParts: BodyPart[];
  symptoms: Symptom[];
  onset: Onset | null;
  workRelated: YesNoUnknown | null;
  workType: WorkType | null;
}

function matchKeys<K extends string>(text: string, dict: Record<K, string[]>): K[] {
  return (Object.keys(dict) as K[]).filter((k) => includesAny(text, dict[k]));
}

export function extractFromText(freeText: string): Extraction {
  const text = ` ${freeText.toLowerCase()} `;
  const onsets = matchKeys(text, ONSET_WORDS);
  let workRelated: YesNoUnknown | null = null;
  // "ở nhà máy"(공장에서)가 "ở nhà"(집에서)로 잡히지 않도록 공장 표현을 먼저 지운다.
  if (includesAny(text.replaceAll('nhà máy', ''), NOT_WORK_WORDS)) workRelated = 'no';
  else if (includesAny(text, WORK_WORDS)) workRelated = 'yes';
  return {
    bodyParts: matchKeys(text, BODY_WORDS),
    symptoms: matchKeys(text, SYMPTOM_WORDS),
    onset: onsets[0] ?? null,
    workRelated,
    workType: matchKeys(text, WORK_TYPE_WORDS)[0] ?? null,
  };
}

/** 버튼 입력을 우선하고, 빈 항목만 추출값으로 채운다. */
export function mergeExtraction(intake: Intake, ex: Extraction): Intake {
  return {
    ...intake,
    bodyParts: intake.bodyParts.length ? intake.bodyParts : ex.bodyParts,
    symptoms: intake.symptoms.length ? intake.symptoms : ex.symptoms,
    onset: intake.onset ?? ex.onset,
    workRelated: intake.workRelated ?? ex.workRelated,
    workType: intake.workType ?? ex.workType,
  };
}

/** 자유 입력 추출 한 번의 결과(POST /api/extract 응답과 같은 형태). */
export interface ExtractResult {
  extraction: Extraction;
  /** 버튼 입력을 우선하고 빈 항목만 추출값으로 채운 Intake */
  intake: Intake;
  /** 추출로 채운 값이 있는지 */
  filled: boolean;
  /** 서버 전용 선택 필드. 브라우저 추출에는 없다 */
  source?: 'llm' | 'keywords';
}

/** 추출로 채운 값이 있는지. 백엔드 `filled_by_extraction`과 같은 판단이다. */
function filledByExtraction(before: Intake, merged: Intake): boolean {
  return (
    (before.bodyParts.length === 0 && merged.bodyParts.length > 0) ||
    (before.symptoms.length === 0 && merged.symptoms.length > 0) ||
    merged.onset !== before.onset ||
    merged.workRelated !== before.workRelated ||
    merged.workType !== before.workType
  );
}

/** 자유 입력에서 추출해 빈 항목을 채운다(extractFromText + mergeExtraction). 단독 모드와 서버 실패 시의 대체 함수다. */
export function extractIntake(intake: Intake): ExtractResult {
  const extraction = extractFromText(intake.freeText);
  const merged = mergeExtraction(intake, extraction);
  return { extraction, intake: merged, filled: filledByExtraction(intake, merged) };
}

export function newIntake(language: Lang): Intake {
  return {
    id: `in-${Date.now().toString(36)}`,
    language,
    bodyParts: [],
    symptoms: [],
    freeText: '',
    onset: null,
    workRelated: null,
    workType: null,
    industry: null,
    district: null,
    createdAt: new Date().toISOString(),
  };
}

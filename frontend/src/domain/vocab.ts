// 고정 어휘: 신체 부위·증상·진료과·업종·구군 등.
// 여기에는 한국어(의료진·센터 표시)와 발음 표기(전화 스크립트용)를 두고, 근로자 모국어 표기는 lang/<언어>.ts에서 합친다.
// 한국어를 고른 근로자는 한국어 표기를 그대로 보고, 발음 표기는 쓰지 않는다.

import { PACKS } from './lang';
import type { LangPack } from './lang/types';

// 순서는 동기화 테스트 기대값(parity.json)의 순서다. 처음 세 언어 뒤에 붙여 기존 기대값이 바뀌지 않게 한다.
// 화면의 언어 목록 순서는 i18n/index.ts의 LANGUAGE_OPTIONS가 정한다.
export const LANGS = ['en', 'vi', 'ko', 'ne', 'ru', 'mn', 'my', 'si', 'ar', 'uz', 'ja', 'zh-CN', 'zh-TW', 'kk', 'km', 'ky', 'th', 'fr', 'tl', 'id'] as const;
export type Lang = (typeof LANGS)[number];
/** 한국어를 뺀 근로자 모국어. 언어마다 lang/<언어>.ts 내용 묶음이 있다 */
export type NativeLang = Exclude<Lang, 'ko'>;
const NATIVE_LANGS = LANGS.filter((l): l is NativeLang => l !== 'ko');

interface KoTerm {
  ko: string;
  /** 로마자 발음. 베트남어를 뺀 모든 외국어 사용자에게 보인다 */
  roman: string;
  /** 베트남어 사용자용 발음 표기 */
  viPron: string;
}

/** 한국어·발음 표기에 모든 근로자 언어의 표기를 더한 어휘 항목 */
export type Term = KoTerm & Record<Lang, string>;

/** 한국어 표에 각 언어 묶음의 표기를 합친다. 키 순서는 한국어 표를 따른다. */
function withNative<K extends string>(base: Record<K, KoTerm>, pick: (p: LangPack) => Record<K, string>): Record<K, Term> {
  const out = {} as Record<K, Term>;
  for (const k of Object.keys(base) as K[]) {
    const native = Object.fromEntries(NATIVE_LANGS.map((l) => [l, pick(PACKS[l])[k]])) as Record<NativeLang, string>;
    out[k] = { ...base[k], ...native };
  }
  return out;
}

/** 근로자 언어에 맞는 발음 표기. 한국어 사용자는 발음 표기가 필요 없어 빈 문자열을 돌려준다. */
export function pron(term: Term, lang: Lang): string {
  if (lang === 'ko') return '';
  return lang === 'vi' ? term.viPron : term.roman;
}

/** 날짜·시간 표시 로캘 */
export const LOCALES: Record<Lang, string> = {
  en: 'en-GB',
  vi: 'vi-VN',
  ko: 'ko-KR',
  ne: 'ne-NP',
  ru: 'ru-RU',
  mn: 'mn-MN',
  my: 'my-MM',
  si: 'si-LK',
  ar: 'ar-AE',
  uz: 'uz-Latn-UZ',
  ja: 'ja-JP',
  'zh-CN': 'zh-CN',
  'zh-TW': 'zh-TW',
  kk: 'kk-KZ',
  km: 'km-KH',
  ky: 'ky-KG',
  th: 'th-TH',
  fr: 'fr-FR',
  tl: 'fil-PH',
  id: 'id-ID',
};

/** 오른쪽에서 왼쪽으로 쓰는 언어. 문서 방향(dir)을 바꾼다 */
export const RTL_LANGS: Lang[] = ['ar'];

const BODY_PARTS_KO = {
  head: { ko: '머리', roman: 'meo-ri', viPron: 'mơ-ri' },
  eye: { ko: '눈', roman: 'nun', viPron: 'nun' },
  ent: { ko: '귀·코·목', roman: 'gwi, ko, mok', viPron: 'guy, cô, mốc' },
  teeth: { ko: '이·잇몸', roman: 'i, in-mom', viPron: 'i, in-môm' },
  chest: { ko: '가슴', roman: 'ga-seum', viPron: 'ca-xưm' },
  abdomen: { ko: '배', roman: 'bae', viPron: 'be' },
  back: { ko: '허리·등', roman: 'heo-ri, deung', viPron: 'hơ-ri, tưng' },
  arm: { ko: '팔·어깨', roman: 'pal, eo-kkae', viPron: 'pan, ơ-ke' },
  hand: { ko: '손·손가락', roman: 'son, son-ga-rak', viPron: 'xôn, xôn-ca-rác' },
  leg: { ko: '다리·무릎', roman: 'da-ri, mu-reup', viPron: 'ta-ri, mu-rứp' },
  foot: { ko: '발·발목', roman: 'bal, bal-mok', viPron: 'pan, pan-mốc' },
  skin: { ko: '피부', roman: 'pi-bu', viPron: 'pi-bu' },
  whole: { ko: '온몸', roman: 'on-mom', viPron: 'ôn-môm' },
} satisfies Record<string, KoTerm>;
export type BodyPart = keyof typeof BODY_PARTS_KO;
export const BODY_PARTS = withNative(BODY_PARTS_KO, (p) => p.terms.bodyParts);

// 증상 한국어 표기는 "~이/가 있습니다" 문장에 들어가도록 명사형으로 둔다.
const SYMPTOMS_KO = {
  pain: { ko: '통증', roman: 'tong-jeung', viPron: 'thông-chưng' },
  swelling: { ko: '부기', roman: 'bu-gi', viPron: 'bu-ghi' },
  cut: { ko: '베인 상처', roman: 'be-in sang-cheo', viPron: 'bê-in xang-chơ' },
  bleeding: { ko: '출혈', roman: 'chul-hyeol', viPron: 'chun-hiơn' },
  burn: { ko: '화상', roman: 'hwa-sang', viPron: 'hoa-xang' },
  numb: { ko: '저림', roman: 'jeo-rim', viPron: 'chơ-rim' },
  cantmove: { ko: '움직이기 어려움', roman: 'um-ji-gi-gi eo-ryeo-um', viPron: 'um-chi-ghi-ghi ơ-riơ-um' },
  fever: { ko: '열', roman: 'yeol', viPron: 'iơn' },
  cough: { ko: '기침', roman: 'gi-chim', viPron: 'ki-chim' },
  dizzy: { ko: '어지러움', roman: 'eo-ji-reo-um', viPron: 'ơ-chi-rơ-um' },
  rash: { ko: '발진·가려움', roman: 'bal-jin, ga-ryeo-um', viPron: 'pan-chin, ca-riơ-um' },
  nausea: { ko: '구토·메스꺼움', roman: 'gu-to, me-seu-kkeo-um', viPron: 'cu-thô, mê-xư-cơ-um' },
  breath: { ko: '호흡 곤란', roman: 'ho-heup gol-lan', viPron: 'hô-hứp côn-lan' },
  chemical: { ko: '화학물질 노출', roman: 'hwa-hak-mul-jil no-chul', viPron: 'hoa-hác-mun-chin nô-chun' },
  foreign: { ko: '눈의 이물감', roman: 'nu-ne i-mul-gam', viPron: 'nu-nê i-mun-cam' },
} satisfies Record<string, KoTerm>;
export type Symptom = keyof typeof SYMPTOMS_KO;
export const SYMPTOMS = withNative(SYMPTOMS_KO, (p) => p.terms.symptoms);

const DEPARTMENTS_KO = {
  ortho: { ko: '정형외과', roman: 'jeong-hyeong-oe-gwa', viPron: 'chơng-hiơng-uê-qua' },
  surgery: { ko: '외과', roman: 'oe-gwa', viPron: 'uê-qua' },
  internal: { ko: '내과', roman: 'nae-gwa', viPron: 'ne-qua' },
  ophth: { ko: '안과', roman: 'an-gwa', viPron: 'an-qua' },
  ent: { ko: '이비인후과', roman: 'i-bi-in-hu-gwa', viPron: 'i-bi-in-hu-qua' },
  derm: { ko: '피부과', roman: 'pi-bu-gwa', viPron: 'pi-bu-qua' },
  dental: { ko: '치과', roman: 'chi-gwa', viPron: 'chi-qua' },
  neuro: { ko: '신경과', roman: 'sin-gyeong-gwa', viPron: 'xin-ghiơng-qua' },
  family: { ko: '가정의학과', roman: 'ga-jeong-ui-hak-gwa', viPron: 'ca-chơng-ưi-hác-qua' },
  occ: { ko: '직업환경의학과', roman: 'ji-geop-hwan-gyeong-ui-hak-gwa', viPron: 'chi-gớp-hoan-ghiơng-ưi-hác-qua' },
} satisfies Record<string, KoTerm>;
export type Department = keyof typeof DEPARTMENTS_KO;
export const DEPARTMENTS = withNative(DEPARTMENTS_KO, (p) => p.terms.departments);

const ONSETS_KO = {
  today: { ko: '오늘', roman: 'o-neul', viPron: 'ô-nưn' },
  yesterday: { ko: '어제', roman: 'eo-je', viPron: 'ơ-chê' },
  days: { ko: '2~3일 전', roman: 'i-sam-il jeon', viPron: 'i-xam-in chơn' },
  week: { ko: '일주일 이상 전', roman: 'il-ju-il i-sang jeon', viPron: 'in-chu-in i-xang chơn' },
} satisfies Record<string, KoTerm>;
export type Onset = keyof typeof ONSETS_KO;
export const ONSETS = withNative(ONSETS_KO, (p) => p.terms.onsets);

const INDUSTRIES_KO = {
  shipbuilding: { ko: '조선', roman: 'jo-seon', viPron: 'chô-xơn' },
  autoparts: { ko: '자동차 부품', roman: 'ja-dong-cha bu-pum', viPron: 'cha-đông-cha bu-pum' },
  chemical: { ko: '화학', roman: 'hwa-hak', viPron: 'hoa-hác' },
  construction: { ko: '건설', roman: 'geon-seol', viPron: 'cơn-xơn' },
  other: { ko: '기타', roman: 'gi-ta', viPron: 'ki-tha' },
} satisfies Record<string, KoTerm>;
export type Industry = keyof typeof INDUSTRIES_KO;
export const INDUSTRIES = withNative(INDUSTRIES_KO, (p) => p.terms.industries);

const WORK_TYPES_KO = {
  welding: { ko: '용접', roman: 'yong-jeop', viPron: 'iông-chớp' },
  lifting: { ko: '중량물 운반', roman: 'jung-nyang-mul un-ban', viPron: 'chung-niang-mun un-ban' },
  machine: { ko: '기계(프레스 등) 작업', roman: 'gi-gye jak-eop', viPron: 'ki-ghiê chác-ớp' },
  grinding: { ko: '절단·연마', roman: 'jeol-dan, yeon-ma', viPron: 'chơn-tan, iơn-ma' },
  painting: { ko: '도장·화학물질 취급', roman: 'do-jang', viPron: 'tô-chang' },
  assembly: { ko: '조립', roman: 'jo-rip', viPron: 'chô-ríp' },
} satisfies Record<string, KoTerm>;
export type WorkType = keyof typeof WORK_TYPES_KO;
export const WORK_TYPES = withNative(WORK_TYPES_KO, (p) => p.terms.workTypes);

const DISTRICTS_KO = {
  jung: { ko: '중구', roman: 'jung-gu', viPron: 'chung-cu' },
  nam: { ko: '남구', roman: 'nam-gu', viPron: 'nam-cu' },
  dong: { ko: '동구', roman: 'dong-gu', viPron: 'tông-cu' },
  buk: { ko: '북구', roman: 'buk-gu', viPron: 'búc-cu' },
  ulju: { ko: '울주군', roman: 'ul-ju-gun', viPron: 'un-chu-cun' },
} satisfies Record<string, KoTerm>;
export type District = keyof typeof DISTRICTS_KO;
export const DISTRICTS = withNative(DISTRICTS_KO, (p) => p.terms.districts);

export type YesNoUnknown = 'yes' | 'no' | 'unknown';

// 프로필 성별(S-02). 보고서·센터 요청 문장에 쓴다.
const SEXES_KO = {
  female: { ko: '여성', roman: 'yeo-seong', viPron: 'iơ-xơng' },
  male: { ko: '남성', roman: 'nam-seong', viPron: 'nam-xơng' },
} satisfies Record<string, KoTerm>;
export type Sex = keyof typeof SEXES_KO;
export const SEXES = withNative(SEXES_KO, (p) => p.terms.sexes);

export const LANGUAGE_NAMES_KO: Record<Lang, string> = {
  en: '영어',
  vi: '베트남어',
  ko: '한국어',
  ne: '네팔어',
  ru: '러시아어',
  mn: '몽골어',
  my: '미얀마어',
  si: '싱할라어',
  ar: '아랍어',
  uz: '우즈베크어',
  ja: '일본어',
  'zh-CN': '중국어(간체)',
  'zh-TW': '중국어(번체)',
  kk: '카자흐어',
  km: '크메르어',
  ky: '키르기스어',
  th: '태국어',
  fr: '프랑스어',
  tl: '필리핀어',
  id: '인도네시아어',
};

// ---------------------------------------------------------------------------
// 국적(frontend backlog 42). ISO 3166-1 alpha-2 두 글자 대문자. 이름은 Intl.DisplayNames로 화면 언어에 맞춰 보인다(번역 표를 두지 않는다).
// ---------------------------------------------------------------------------
/** 센터 회신(2026-10-31) 의료 상담 329건의 국적 12개국, 많은 순 */
export const CENTER_NATIONALITIES = ['ID', 'RU', 'KZ', 'LK', 'PH', 'UZ', 'VN', 'KR', 'KG', 'TL', 'TJ', 'MA'] as const;

/** ISO 3166-1 alpha-2 공식 코드 전체(249개). S-03 "그 밖" 목록 */
export const ISO_COUNTRIES =
  'AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW'.split(' ');

/** 국적 칸이 받는 값: 두 글자 대문자(서버도 같은 꼴만 받는다) */
export const isNationality = (v: unknown): v is string => typeof v === 'string' && /^[A-Z]{2}$/.test(v);

const regionNames = new Map<string, Intl.DisplayNames | null>();

/** 국적 코드의 이름. 브라우저가 이름을 모르면 코드 그대로 */
export function countryName(code: string, locale: string): string {
  if (!regionNames.has(locale)) {
    try {
      regionNames.set(locale, new Intl.DisplayNames([locale], { type: 'region' }));
    } catch {
      regionNames.set(locale, null);
    }
  }
  try {
    return regionNames.get(locale)?.of(code) ?? code;
  } catch {
    return code;
  }
}

/** 한국어 단어 끝 받침 여부에 따라 조사를 고른다(이/가, 은/는 등). */
export function josa(word: string, withBatchim: string, withoutBatchim: string): string {
  const last = word.trim().at(-1) ?? '';
  const code = last.charCodeAt(0) - 0xac00;
  if (code < 0 || code > 11171) return word + withoutBatchim;
  return word + (code % 28 === 0 ? withoutBatchim : withBatchim);
}

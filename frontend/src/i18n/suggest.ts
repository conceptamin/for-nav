// S-01 언어 추천. 폰 언어 목록(navigator.languages)을 지원 언어로 맞추고, 함께 읽을 가능성이 높은 언어를 뒤에 붙인다.
// 폰 언어는 화면이 읽어 넘긴다(순수 함수라 DOM을 모른다). 서버가 옮기는 규칙이 아니라 domain/에 두지 않는다. 추천은 순서만 정하고 언어를 고르지는 않는다(backlog 20).

import { LANGS, type Lang } from '../domain/vocab';

/** 추천 말풍선 최대 개수. 나머지 언어는 "다른 언어" 칩으로 모두 보인다 */
const MAX_SUGGESTED = 4;

/**
 * 지원하지 않는 폰 언어 → 가장 가까운 지원 언어. 서로 알아듣거나 같은 문자를 쓰는 언어로 옮긴다.
 * 키는 BCP 47 태그 전체 또는 기본 언어 부분이다.
 */
const DEVICE_ALIASES: Record<string, Lang> = {
  fil: 'tl',
  ms: 'id',
  lo: 'th',
  hi: 'ne',
  uk: 'ru',
  be: 'ru',
  tg: 'ru',
};

/**
 * 가까운 언어 표: 이 언어를 쓰는 사람이 함께 읽을 가능성이 높은 언어(제2언어·서로 알아듣는 정도).
 * 계통상 거리가 아니다. 영어는 표 뒤에 늘 붙으므로 적지 않는다. 원어민·센터 상담원 검토 대상(backlog 20 메모).
 */
const NEAR: Partial<Record<Lang, Lang[]>> = {
  kk: ['ru', 'ky', 'uz'],
  ky: ['ru', 'kk', 'uz'],
  uz: ['ru', 'kk', 'ky'],
  mn: ['ru', 'kk'],
  ru: ['kk', 'ky', 'uz'],
  'zh-CN': ['zh-TW'],
  'zh-TW': ['zh-CN'],
  km: ['th'],
  ar: ['fr'],
};

/** 폰 언어 추천을 쓸 수 없을 때(지원 언어가 하나도 없음): 공용어와 이 나라 언어 */
const FALLBACK: Lang[] = ['en', 'ko'];

function isLang(tag: string): tag is Lang {
  return (LANGS as readonly string[]).includes(tag);
}

/** BCP 47 태그 하나를 지원 언어로. 중국어는 지역·문자 표기로 간체·번체를 나눈다 */
export function matchLang(tag: string): Lang | null {
  const [base, ...rest] = tag.split('-');
  const lower = base.toLowerCase();
  if (lower === 'zh') return rest.some((p) => ['TW', 'HK', 'MO', 'Hant'].includes(p)) ? 'zh-TW' : 'zh-CN';
  if (isLang(lower)) return lower;
  return DEVICE_ALIASES[lower] ?? null;
}

export interface LangSuggestion {
  /** 폰 언어에서 찾은 첫 지원 언어. 질문 말풍선의 언어. 없으면 null(영어로 묻는다) */
  first: Lang | null;
  /** 위에 크게 놓을 대답 말풍선 */
  suggested: Lang[];
  /** 나머지 언어. order의 순서를 지킨다 */
  rest: Lang[];
}

/** 추천 순서: ① 폰 언어 목록에서 지원되는 것(순서대로) ② 첫 언어의 가까운 언어 ③ 영어. 중복 없이 최대 4개 */
export function suggestLangs(deviceLangs: readonly string[], order: readonly Lang[]): LangSuggestion {
  const device = deviceLangs.map(matchLang).filter((l): l is Lang => l !== null);
  const first = device[0] ?? null;
  const picked = first ? [...device, ...(NEAR[first] ?? []), 'en' as const] : FALLBACK;
  const suggested = [...new Set(picked)].slice(0, MAX_SUGGESTED);
  return { first, suggested, rest: order.filter((l) => !suggested.includes(l)) };
}

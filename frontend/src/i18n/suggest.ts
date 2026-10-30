// S-01 언어 순서. 폰 언어 목록(navigator.languages)에서 처음 맞는 지원 언어 하나만 맨 앞에 두고, 나머지는 정해진 순서 그대로다.
// 추천 언어를 따로 묶거나 크게 보이지 않는다. 언어 사이에 위아래가 있어 보이지 않게 하려는 것이다(backlog 24).
// 폰 언어는 화면이 읽어 넘긴다(순수 함수라 DOM을 모른다). 서버가 옮기는 규칙이 아니라 domain/에 두지 않는다.

import { LANGS, type Lang } from '../domain/vocab';

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

export interface LangOrder {
  /** 폰 언어에서 찾은 첫 지원 언어. 질문의 언어. 없으면 null(영어로 묻는다) */
  first: Lang | null;
  /** 격자에 놓을 순서: first가 있으면 맨 앞, 나머지는 order 그대로 */
  langs: Lang[];
}

export function orderLangs(deviceLangs: readonly string[], order: readonly Lang[]): LangOrder {
  const first = deviceLangs.map(matchLang).find((l): l is Lang => l !== null) ?? null;
  return { first, langs: first ? [first, ...order.filter((l) => l !== first)] : [...order] };
}

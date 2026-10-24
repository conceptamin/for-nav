// 언어 리소스. 새 언어는 파일 하나를 추가하고 MESSAGES에 등록하면 된다(코드 변경 최소화).

import { useApp } from '../state/AppState';
import type { Lang, Term } from '../domain/vocab';
import { en, type MessageKey } from './en';
import { ko } from './ko';
import { vi } from './vi';

const MESSAGES: Record<Lang, Record<MessageKey, string>> = { en, vi, ko };

export const LANGUAGE_OPTIONS: { lang: Lang; native: string; english: string }[] = [
  { lang: 'en', native: 'English', english: 'English' },
  { lang: 'vi', native: 'Tiếng Việt', english: 'Vietnamese' },
  { lang: 'ko', native: '한국어', english: 'Korean' },
];

export type { MessageKey };

export function translate(lang: Lang, key: MessageKey): string {
  return MESSAGES[lang][key];
}

/** 현재 언어의 문구 함수와 어휘 표시 함수 */
export function useT() {
  const { lang } = useApp();
  const l: Lang = lang ?? 'en';
  return {
    lang: l,
    t: (key: MessageKey) => MESSAGES[l][key],
    term: (term: Term) => term[l],
  };
}

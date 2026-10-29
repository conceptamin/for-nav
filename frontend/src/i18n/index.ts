// 언어 리소스. 새 언어는 파일 하나를 추가하고 MESSAGES에 등록하면 된다(코드 변경 최소화).
// 어휘·접수 도우미 문장은 domain/lang/<언어>.ts에 따로 있다.

import { useApp } from '../state/AppState';
import type { Lang, Term } from '../domain/vocab';
import { ar } from './ar';
import { en, type MessageKey } from './en';
import { fr } from './fr';
import { id } from './id';
import { ja } from './ja';
import { kk } from './kk';
import { km } from './km';
import { ko } from './ko';
import { ky } from './ky';
import { mn } from './mn';
import { my } from './my';
import { ne } from './ne';
import { ru } from './ru';
import { si } from './si';
import { th } from './th';
import { tl } from './tl';
import { uz } from './uz';
import { vi } from './vi';
import { zhCN } from './zh-CN';
import { zhTW } from './zh-TW';

const MESSAGES: Record<Lang, Record<MessageKey, string>> = {
  en,
  vi,
  ko,
  ne,
  ru,
  mn,
  my,
  si,
  ar,
  uz,
  ja,
  'zh-CN': zhCN,
  'zh-TW': zhTW,
  kk,
  km,
  ky,
  th,
  fr,
  tl,
  id,
};

// 언어 선택 화면의 순서. 요청받은 국기 목록(backlog 16)의 순서를 따른다.
export const LANGUAGE_OPTIONS: { lang: Lang; native: string; english: string }[] = [
  { lang: 'ko', native: '한국어', english: 'Korean' },
  { lang: 'ne', native: 'नेपाली', english: 'Nepali' },
  { lang: 'ru', native: 'Русский', english: 'Russian' },
  { lang: 'mn', native: 'Монгол', english: 'Mongolian' },
  { lang: 'my', native: 'မြန်မာ', english: 'Burmese' },
  { lang: 'vi', native: 'Tiếng Việt', english: 'Vietnamese' },
  { lang: 'si', native: 'සිංහල', english: 'Sinhala' },
  { lang: 'ar', native: 'العربية', english: 'Arabic' },
  { lang: 'en', native: 'English', english: 'English' },
  { lang: 'uz', native: 'Oʻzbekcha', english: 'Uzbek' },
  { lang: 'ja', native: '日本語', english: 'Japanese' },
  { lang: 'zh-CN', native: '简体中文', english: 'Chinese (Simplified)' },
  { lang: 'zh-TW', native: '繁體中文', english: 'Chinese (Traditional)' },
  { lang: 'kk', native: 'Қазақша', english: 'Kazakh' },
  { lang: 'km', native: 'ខ្មែរ', english: 'Khmer' },
  { lang: 'ky', native: 'Кыргызча', english: 'Kyrgyz' },
  { lang: 'th', native: 'ไทย', english: 'Thai' },
  { lang: 'fr', native: 'Français', english: 'French' },
  { lang: 'tl', native: 'Filipino', english: 'Filipino' },
  { lang: 'id', native: 'Bahasa Indonesia', english: 'Indonesian' },
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

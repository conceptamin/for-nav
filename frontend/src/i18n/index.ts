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
// flag는 S-01 "다른 언어" 알약의 국기(backlog 21). 국기는 나라 표시라 언어와 1:1이 아니다. 그 목록 이미지의 국기를 그대로 쓴다(번체도 🇨🇳)
export const LANGUAGE_OPTIONS: { lang: Lang; native: string; english: string; flag: string }[] = [
  { lang: 'ko', native: '한국어', english: 'Korean', flag: '🇰🇷' },
  { lang: 'ne', native: 'नेपाली', english: 'Nepali', flag: '🇳🇵' },
  { lang: 'ru', native: 'Русский', english: 'Russian', flag: '🇷🇺' },
  { lang: 'mn', native: 'Монгол', english: 'Mongolian', flag: '🇲🇳' },
  { lang: 'my', native: 'မြန်မာ', english: 'Burmese', flag: '🇲🇲' },
  { lang: 'vi', native: 'Tiếng Việt', english: 'Vietnamese', flag: '🇻🇳' },
  { lang: 'si', native: 'සිංහල', english: 'Sinhala', flag: '🇱🇰' },
  { lang: 'ar', native: 'العربية', english: 'Arabic', flag: '🇦🇪' },
  { lang: 'en', native: 'English', english: 'English', flag: '🇺🇸' },
  { lang: 'uz', native: 'Oʻzbekcha', english: 'Uzbek', flag: '🇺🇿' },
  { lang: 'ja', native: '日本語', english: 'Japanese', flag: '🇯🇵' },
  { lang: 'zh-CN', native: '简体中文', english: 'Chinese (Simplified)', flag: '🇨🇳' },
  { lang: 'zh-TW', native: '繁體中文', english: 'Chinese (Traditional)', flag: '🇨🇳' },
  { lang: 'kk', native: 'Қазақша', english: 'Kazakh', flag: '🇰🇿' },
  { lang: 'km', native: 'ខ្មែរ', english: 'Khmer', flag: '🇰🇭' },
  { lang: 'ky', native: 'Кыргызча', english: 'Kyrgyz', flag: '🇰🇬' },
  { lang: 'th', native: 'ไทย', english: 'Thai', flag: '🇹🇭' },
  { lang: 'fr', native: 'Français', english: 'French', flag: '🇫🇷' },
  { lang: 'tl', native: 'Filipino', english: 'Filipino', flag: '🇵🇭' },
  { lang: 'id', native: 'Bahasa Indonesia', english: 'Indonesian', flag: '🇮🇩' },
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

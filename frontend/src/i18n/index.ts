// 언어 리소스. 새 언어는 파일 하나를 추가하고 MESSAGES에 등록하면 된다(코드 변경 최소화).
// 어휘·접수 도우미 문장은 domain/lang/<언어>.ts에 따로 있다.

import { useApp } from '../state/AppState';
import type { Lang, Term } from '../domain/vocab';
import { LOCALES } from '../domain/vocab';
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
// country는 S-01 언어 칸의 국기 그림 public/flags/<country>.svg(flag-icons, MIT, backlog 24). 국기 이모지는 Windows가 그리지 못해 그림 파일을 쓴다.
// 국기는 나라 표시라 언어와 1:1이 아니다. 요청 목록 이미지의 국기를 그대로 쓴다(번체도 cn)
export const LANGUAGE_OPTIONS: { lang: Lang; native: string; english: string; country: string }[] = [
  { lang: 'ko', native: '한국어', english: 'Korean', country: 'kr' },
  { lang: 'ne', native: 'नेपाली', english: 'Nepali', country: 'np' },
  { lang: 'ru', native: 'Русский', english: 'Russian', country: 'ru' },
  { lang: 'mn', native: 'Монгол', english: 'Mongolian', country: 'mn' },
  { lang: 'my', native: 'မြန်မာ', english: 'Burmese', country: 'mm' },
  { lang: 'vi', native: 'Tiếng Việt', english: 'Vietnamese', country: 'vn' },
  { lang: 'si', native: 'සිංහල', english: 'Sinhala', country: 'lk' },
  { lang: 'ar', native: 'العربية', english: 'Arabic', country: 'ae' },
  { lang: 'en', native: 'English', english: 'English', country: 'us' },
  { lang: 'uz', native: 'Oʻzbekcha', english: 'Uzbek', country: 'uz' },
  { lang: 'ja', native: '日本語', english: 'Japanese', country: 'jp' },
  { lang: 'zh-CN', native: '简体中文', english: 'Chinese (Simplified)', country: 'cn' },
  { lang: 'zh-TW', native: '繁體中文', english: 'Chinese (Traditional)', country: 'cn' },
  { lang: 'kk', native: 'Қазақша', english: 'Kazakh', country: 'kz' },
  { lang: 'km', native: 'ខ្មែរ', english: 'Khmer', country: 'kh' },
  { lang: 'ky', native: 'Кыргызча', english: 'Kyrgyz', country: 'kg' },
  { lang: 'th', native: 'ไทย', english: 'Thai', country: 'th' },
  { lang: 'fr', native: 'Français', english: 'French', country: 'fr' },
  { lang: 'tl', native: 'Filipino', english: 'Filipino', country: 'ph' },
  { lang: 'id', native: 'Bahasa Indonesia', english: 'Indonesian', country: 'id' },
];

export type { MessageKey };

export function translate(lang: Lang, key: MessageKey): string {
  return MESSAGES[lang][key];
}

// ---------------------------------------------------------------------------
// 날짜 표시(backlog 34). 브라우저 기본 날짜 칸은 앱 언어를 따르지 않아 직접 그린다.
// 연·월·일 순서는 언어별 표로 정하고(CLDR 긴 날짜 형식 기준), 달 이름은 브라우저(Intl)가 그 언어를 알 때만 쓴다.
// 언어 자료가 줄어든 브라우저(일부 WebView·Electron)는 모르는 언어를 기본 언어로 그리거나 'M09'로 그려서다.
// ---------------------------------------------------------------------------
export type DatePart = 'year' | 'month' | 'day';

export const DATE_ORDER: Record<Lang, DatePart[]> = (() => {
  const dmy: DatePart[] = ['day', 'month', 'year'];
  const ymd: DatePart[] = ['year', 'month', 'day'];
  const mdy: DatePart[] = ['month', 'day', 'year'];
  return {
    en: dmy, vi: dmy, ko: ymd, ne: ymd, ru: dmy, mn: ymd, my: ymd, si: ymd, ar: dmy, uz: dmy,
    ja: ymd, 'zh-CN': ymd, 'zh-TW': ymd, kk: dmy, km: dmy, ky: dmy, th: dmy, fr: dmy, tl: mdy, id: dmy,
  };
})();

/**
 * 날짜를 그 언어의 모양으로 그리는 Intl 설정. 그레고리력으로 고정한다
 * (태국어 기본인 불기 연도가 저장값·홈 나 줄의 서기 연도와 어긋나지 않게). 'YYYY-MM-DD'는 UTC 자정으로 읽는다
 */
export function dateFormat(lang: Lang, opts: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  return new Intl.DateTimeFormat(LOCALES[lang], { ...opts, calendar: 'gregory', timeZone: 'UTC' });
}

const dateLocaleCache = new Map<Lang, boolean>();
/** 이 브라우저가 그 언어의 달 이름을 아는지. 모르면 숫자로 그린다 */
export function hasDateLocale(lang: Lang): boolean {
  let ok = dateLocaleCache.get(lang);
  if (ok === undefined) {
    try {
      ok =
        Intl.DateTimeFormat.supportedLocalesOf([LOCALES[lang]]).length > 0 &&
        !/^M\d+$/.test(dateFormat(lang, { month: 'long' }).format(Date.UTC(2000, 8, 1)));
    } catch {
      ok = false;
    }
    dateLocaleCache.set(lang, ok);
  }
  return ok;
}

/** 'YYYY-MM-DD'를 그 언어의 날짜(예: 3 May 1990, 1990년 5월 3일)로. 달 이름을 모르는 브라우저는 숫자(3/5/1990). 형식이 아니면 그대로 */
export function formatIsoDate(iso: string, lang: Lang): string {
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) return iso;
  if (hasDateLocale(lang)) return dateFormat(lang, { year: 'numeric', month: 'long', day: 'numeric' }).format(Date.UTC(y, m - 1, d));
  const parts: Record<DatePart, number> = { year: y, month: m, day: d };
  return DATE_ORDER[lang].map((p) => parts[p]).join('/');
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

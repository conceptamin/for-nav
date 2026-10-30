// 근로자 모국어별 내용 묶음 등록표. 한국어는 vocab.ts·templates.ts에 직접 있다.
// 영어·베트남어를 뺀 언어는 기계 번역 초안이라 원어민 검수가 필요하다.

import type { NativeLang } from '../vocab';
import { ar } from './ar';
import { en } from './en';
import { fr } from './fr';
import { id } from './id';
import { ja } from './ja';
import { kk } from './kk';
import { km } from './km';
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
import type { LangPack } from './types';

export const PACKS: Record<NativeLang, LangPack> = { en, vi, ne, ru, mn, my, si, ar, uz, ja, 'zh-CN': zhCN, 'zh-TW': zhTW, kk, km, ky, th, fr, tl, id };

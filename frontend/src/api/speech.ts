// 통화 자막용 받아쓰기(backlog 26). 브라우저 Web Speech API(SpeechRecognition)로 내 마이크를 받아쓴다.
// 통화 중에만 api/call.ts가 켠다. 브라우저가 스스로 멈추면(onend) 끌 때까지 다시 켠다.
// 앱 WebView 안에서는 app-front가 setHostSpeech로 등록한 호스트 음성 인식을 대신 쓴다(backlog 37).
// 받아쓴 글은 console에 찍지 않는다. 오류 기록은 오류 이름만 남긴다.

import type { Lang } from '../domain/vocab';
import { LOCALES } from '../domain/vocab';

/** 브라우저가 멈춘 뒤 다시 켜기까지 기다리는 시간. 네트워크 오류가 이어질 때 빈틈없이 다시 켜지 않게 한다 */
export const SPEECH_RESTART_MS = 300;

/**
 * 앱 언어 → 받아쓰기 언어(BCP-47). 대부분 날짜 표기용 LOCALES와 같고, Chrome 음성 인식이 다른 이름을 쓰는 것만 바꾼다.
 * 우즈베크어는 문자 표기(Latn)가 붙으면 인식하지 않고, 아랍어는 표준 아랍어(사우디)가 가장 넓게 인식된다.
 */
export const SPEECH_LANGS: Record<Lang, string> = { ...LOCALES, uz: 'uz-UZ', ar: 'ar-SA' };

// lib.dom에 SpeechRecognition 본체 타입이 없어 쓰는 만큼만 적는다(이벤트 타입은 있다).
interface Recognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
type RecognitionCtor = new () => Recognition;

function recognitionCtor(): RecognitionCtor | null {
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export interface SpeechHandlers {
  /** 말하는 중(final: false)과 확정 문장(final: true). 확정 뒤에는 말하는 중이 빈 글로 다시 온다 */
  onText: (text: string, final: boolean) => void;
  /** 이 브라우저·언어로는 받아쓸 수 없다(권한 거부·언어 미지원). 다시 켜지 않는다 */
  onUnsupported: () => void;
}

/**
 * 앱 호스트의 음성 인식(backlog 37). lang은 SPEECH_LANGS 값(BCP-47)이고, 끄는 함수를 돌려준다.
 * 다시 켜기·오류 처리는 등록한 쪽이 맡고, 받아쓸 수 없으면 onUnsupported를 부른다. 화면은 다리를 모른다.
 */
export type HostSpeech = (lang: string, on: SpeechHandlers) => () => void;

let hostSpeech: HostSpeech | null = null;

/** 앱(app-front)이 호스트가 음성 인식을 알릴 때 등록한다. WebView에는 Web Speech API가 없다. 브라우저에서는 아무도 부르지 않는다 */
export function setHostSpeech(fn: HostSpeech | null): void {
  hostSpeech = fn;
}

/** 이 브라우저(또는 앱 호스트)에 받아쓰기가 있는가. Firefox에는 없다. 언어 지원은 켜 봐야 안다(language-not-supported) */
export function isSpeechSupported(): boolean {
  return hostSpeech !== null || recognitionCtor() !== null;
}

// 다시 켜지 않는 오류. 나머지(no-speech·network·aborted 등)는 onend 뒤 다시 켠다
const FATAL = new Set<string>(['not-allowed', 'service-not-allowed', 'language-not-supported', 'audio-capture']);
/** 결과 없이 network 오류가 이만큼 이어지면 끈다. 음성 인식 서버가 없는 Chromium(Electron·Brave 등)은 계속 network 오류를 낸다 */
export const SPEECH_MAX_NETWORK_ERRORS = 3;

/**
 * 받아쓰기를 켜고 끄는 함수를 돌려준다. 앱 호스트가 등록했으면 그것을 쓴다.
 * 받아쓰기가 없는 브라우저면 바로 onUnsupported를 부르고 아무것도 하지 않는다
 */
export function startSpeech(lang: Lang, on: SpeechHandlers): () => void {
  if (hostSpeech) return hostSpeech(SPEECH_LANGS[lang], on);
  const Ctor = recognitionCtor();
  if (!Ctor) {
    on.onUnsupported();
    return () => {};
  }
  let stopped = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let current: Recognition | null = null;
  let networkErrors = 0;

  const run = () => {
    if (stopped) return;
    const r = new Ctor();
    current = r;
    r.lang = SPEECH_LANGS[lang];
    r.continuous = true;
    r.interimResults = true;
    r.onresult = (e) => {
      networkErrors = 0;
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        const text = res[0]?.transcript.trim() ?? '';
        if (res.isFinal) {
          if (text) on.onText(text, true);
        } else {
          interim += `${text} `;
        }
      }
      on.onText(interim.trim(), false);
    };
    r.onerror = (e) => {
      if (e.error === 'network') networkErrors += 1;
      if (!FATAL.has(e.error) && networkErrors < SPEECH_MAX_NETWORK_ERRORS) return;
      console.warn(`[speech] ${e.error} → 받아쓰기 끔`);
      stopped = true;
      on.onUnsupported();
    };
    r.onend = () => {
      current = null;
      on.onText('', false);
      if (!stopped) timer = setTimeout(run, SPEECH_RESTART_MS);
    };
    try {
      r.start();
    } catch {
      // 이미 켜져 있는 등으로 start가 실패하면 onend가 오지 않으므로 여기서 다시 잡는다
      current = null;
      if (!stopped) timer = setTimeout(run, SPEECH_RESTART_MS);
    }
  };

  run();
  return () => {
    stopped = true;
    if (timer) clearTimeout(timer);
    // stop은 듣던 말을 확정해 보내지만 통화가 끝난 뒤라 쓸모가 없다. 바로 버린다
    current?.abort();
    current = null;
  };
}

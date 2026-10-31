// 근로자 영역 상태.
// - 세션(sessionStorage): 언어, 동의, 현재 증상 입력·판정, 제도 경로 결과, 상담 채팅 토큰
// - 기기(localStorage): 로그인한 계정(`umn.account`), 계정별 프로필(여러 개, backlog 34)·리포트·보낸 센터 사례 id(`umn.device.<계정 키>`)
//   → 같은 휴대폰에서 다른 계정으로 들어오면 앞 계정의 프로필·리포트가 보이지 않는다(backlog 28).
//   데모 로그인(단독 모드·서버 WORKER_AUTH=off)의 계정 키는 `demo`다. 서버 세션은 api/auth.ts가 보고, 여기에는 계정 키만 둔다.
// - 메모리: 서버 설정값(정보 기준일·센터 운영 시간). 저장하지 않고 시작할 때마다 GET /api/meta로 받는다

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { loadMeta } from '../api/meta';
import type { CoverageInput, CoverageResult, Meta } from '../domain/coverage';
import { DEFAULT_META } from '../domain/coverage';
import type { ClinicianReport, Profile } from '../domain/templates';
import type { Intake, TriageResult } from '../domain/triage';
import type { Lang } from '../domain/vocab';
import { RTL_LANGS } from '../domain/vocab';
import { readJson, removeKey, writeJson } from './storage';

export interface Consents {
  terms: boolean;
  sensitive: boolean;
  ai: boolean;
}

export type LoginKind = 'demo' | 'google';

/** 이 기기에서 로그인한 계정. 서버가 꺼져 있어도 이 값으로 계속 쓴다(backlog 28 결정 2) */
interface Account {
  key: string;
  kind: LoginKind;
}

interface SessionState {
  lang: Lang | null;
  consents: Consents;
  intake: Intake | null;
  triage: TriageResult | null;
  /** 이번 세션에서 응급 판정이 한 번이라도 있었는지(센터 긴급도에 사용) */
  emergencySeen: boolean;
  coverage: { input: CoverageInput; result: CoverageResult } | null;
  /** 사례 id → 상담 채팅 토큰(API 모드 S-12 전송 응답). 그 사례 채팅에 붙는 열쇠라 탭을 닫으면 사라지는 세션에 둔다 */
  chatTokens: Record<string, string>;
}

/** 한 계정에 여러 개 둘 수 있는 프로필 하나(backlog 34). 이름은 받지 않으므로 성별·생년월일로 구별해 보인다 */
export interface ProfileEntry {
  id: string;
  profile: Profile;
}

interface DeviceState {
  profiles: ProfileEntry[];
  /** 지금 쓰는 프로필. 리포트·센터 요청에 들어가는 것은 이 프로필이다 */
  activeProfileId: string | null;
  memberReports: ClinicianReport[];
  myCaseIds: string[];
}

const SESSION_KEY = 'umn.session';
const ACCOUNT_KEY = 'umn.account';
/** 계정별 기기 저장소. 계정 키를 뒤에 붙인다 */
const DEVICE_PREFIX = 'umn.device.';
/** 계정을 나누기 전(backlog 28 이전)의 기기 저장소. 처음 읽을 때 데모 계정으로 옮긴다 */
const LEGACY_DEVICE_KEY = 'umn.device';
export const DEMO_ACCOUNT = 'demo';

const deviceKey = (account: string) => `${DEVICE_PREFIX}${account}`;
const isAccount = (a: Partial<Account> | null): a is Account =>
  Boolean(a && typeof a.key === 'string' && a.key && (a.kind === 'demo' || a.kind === 'google'));

const initialSession: SessionState = {
  lang: null,
  consents: { terms: false, sensitive: false, ai: false },
  intake: null,
  triage: null,
  emergencySeen: false,
  coverage: null,
  chatTokens: {},
};
const initialDevice: DeviceState = { profiles: [], activeProfileId: null, memberReports: [], myCaseIds: [] };

/** 프로필 id. http로 여는 같은 Wi-Fi 휴대폰에서는 crypto.randomUUID가 없어 시각과 난수로 만든다 */
const newProfileId = () => `p${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

function readDevice(account: string | null): DeviceState {
  if (!account) return initialDevice;
  if (account === DEMO_ACCOUNT) {
    // 계정을 나누기 전에 이 기기에 쌓인 프로필·리포트는 데모 계정 것이다. 한 번만 옮긴다
    const legacy = readJson<Partial<DeviceState> | null>(localStorage, LEGACY_DEVICE_KEY, null);
    if (legacy && readJson(localStorage, deviceKey(DEMO_ACCOUNT), null) === null) {
      writeJson(localStorage, deviceKey(DEMO_ACCOUNT), legacy);
    }
    if (legacy) removeKey(localStorage, LEGACY_DEVICE_KEY);
  }
  // 프로필을 여러 개 두기 전(backlog 34 이전)의 `profile` 하나는 첫 프로필로 옮긴다
  const { profile, ...stored } = readJson<Partial<DeviceState> & { profile?: Profile | null }>(localStorage, deviceKey(account), {});
  const device: DeviceState = { ...initialDevice, ...stored };
  if (!stored.profiles && profile) {
    const id = newProfileId();
    device.profiles = [{ id, profile }];
    device.activeProfileId = id;
  }
  return device;
}

/** 지금 쓰는 프로필. id가 가리키는 것이 없으면 첫 프로필이다 */
function activeEntry(d: DeviceState): ProfileEntry | null {
  return d.profiles.find((e) => e.id === d.activeProfileId) ?? d.profiles[0] ?? null;
}

interface AppContextValue extends SessionState, Omit<DeviceState, 'activeProfileId'> {
  /** 정보 기준일·센터 운영 시간. 단독 모드와 서버 실패 시에는 브라우저 상수다 */
  meta: Meta;
  /** 지금 쓰는 프로필(`profiles` 중 하나). 리포트·센터 요청·홈 나 줄은 이것을 쓴다 */
  profile: Profile | null;
  activeProfileId: string | null;
  /** 로그인한 계정 키. 없으면 로그인 화면으로 간다 */
  account: string | null;
  loginKind: LoginKind | null;
  /** 로그인했고 프로필(생년월일·성별)까지 있다. 홈 이후 화면은 이것이 참일 때만 열린다 */
  ready: boolean;
  setLang: (lang: Lang) => void;
  setConsents: (c: Consents) => void;
  /** 로그인. 그 계정의 기기 저장소(프로필·리포트)로 바꾼다 */
  signIn: (account: string, kind: LoginKind) => void;
  /** 로그아웃. 계정과 현재 입력·판정을 비운다(언어·동의는 남긴다). 계정의 프로필·리포트는 기기에 남는다 */
  signOut: () => void;
  /** 서버 세션이 끝났다(401·서버 확인). 계정만 비우고 현재 입력은 남긴다(다시 로그인하면 이어서 쓴다) */
  endSession: () => void;
  /** 지금 쓰는 프로필을 고친다. 프로필이 하나도 없으면 첫 프로필로 만든다 */
  saveProfile: (p: Profile) => void;
  /** 같은 계정에 프로필을 하나 더 만들고 그 프로필로 바꾼다 */
  addProfile: (p: Profile) => void;
  selectProfile: (id: string) => void;
  /** 프로필 하나를 지운다. 마지막 하나는 지우지 않는다(프로필 없이 홈에 머무는 길을 만들지 않는다) */
  deleteProfile: (id: string) => void;
  setIntake: (intake: Intake | null) => void;
  setTriage: (t: TriageResult | null) => void;
  setCoverage: (c: SessionState['coverage']) => void;
  saveReport: (r: ClinicianReport) => void;
  /** 보낸 사례 id는 기기에, 상담 채팅 토큰(있으면)은 세션에 둔다 */
  addMyCase: (id: string, chatToken?: string) => void;
  reports: ClinicianReport[];
  clearMyData: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState>(() => ({ ...initialSession, ...readJson(sessionStorage, SESSION_KEY, {}) }));
  const [account, setAccount] = useState<Account | null>(() => {
    const a = readJson<Partial<Account> | null>(localStorage, ACCOUNT_KEY, null);
    return isAccount(a) ? a : null;
  });
  const [device, setDevice] = useState<DeviceState>(() => readDevice(account?.key ?? null));
  const [meta, setMeta] = useState<Meta>(DEFAULT_META);

  // API 모드에서만 서버를 부른다. 실패하면 loadMeta가 브라우저 상수를 돌려준다.
  useEffect(() => {
    let alive = true;
    loadMeta().then((m) => alive && setMeta(m));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => writeJson(sessionStorage, SESSION_KEY, session), [session]);
  useEffect(() => {
    if (account) writeJson(localStorage, ACCOUNT_KEY, account);
    else removeKey(localStorage, ACCOUNT_KEY);
  }, [account]);
  // 계정이 바뀔 때는 아래 switchAccount가 저장소를 함께 바꾼다. 여기서는 지금 계정의 값만 쓴다
  useEffect(() => {
    if (account) writeJson(localStorage, deviceKey(account.key), device);
  }, [account, device]);

  useEffect(() => {
    document.documentElement.lang = session.lang ?? 'ko';
    document.documentElement.dir = session.lang && RTL_LANGS.includes(session.lang) ? 'rtl' : 'ltr';
  }, [session.lang]);

  const patch = useCallback((p: Partial<SessionState>) => setSession((s) => ({ ...s, ...p })), []);

  const switchAccount = useCallback((next: Account | null) => {
    setAccount(next);
    setDevice(readDevice(next?.key ?? null));
  }, []);

  const value = useMemo<AppContextValue>(() => {
    const clearInputs = () =>
      setSession((s) => ({ ...initialSession, lang: s.lang, consents: s.consents }));
    const active = activeEntry(device);
    return {
      ...session,
      ...device,
      profile: active?.profile ?? null,
      activeProfileId: active?.id ?? null,
      meta,
      account: account?.key ?? null,
      loginKind: account?.kind ?? null,
      ready: Boolean(account && active),
      setLang: (lang) => patch({ lang }),
      setConsents: (consents) => patch({ consents }),
      signIn: (key, kind) => {
        if (account?.key === key && account.kind === kind) return;
        switchAccount({ key, kind });
      },
      signOut: () => {
        switchAccount(null);
        clearInputs();
      },
      endSession: () => switchAccount(null),
      saveProfile: (profile) =>
        setDevice((d) => {
          const cur = activeEntry(d);
          if (!cur) {
            const id = newProfileId();
            return { ...d, profiles: [{ id, profile }], activeProfileId: id };
          }
          return { ...d, profiles: d.profiles.map((e) => (e.id === cur.id ? { ...e, profile } : e)) };
        }),
      addProfile: (profile) =>
        setDevice((d) => {
          const id = newProfileId();
          return { ...d, profiles: [...d.profiles, { id, profile }], activeProfileId: id };
        }),
      selectProfile: (id) => setDevice((d) => (d.profiles.some((e) => e.id === id) ? { ...d, activeProfileId: id } : d)),
      deleteProfile: (id) =>
        setDevice((d) => {
          if (d.profiles.length < 2) return d;
          const profiles = d.profiles.filter((e) => e.id !== id);
          return { ...d, profiles, activeProfileId: d.activeProfileId === id ? profiles[0].id : d.activeProfileId };
        }),
      setIntake: (intake) => patch({ intake }),
      setTriage: (triage) =>
        setSession((s) => ({ ...s, triage, emergencySeen: s.emergencySeen || Boolean(triage?.emergency) })),
      setCoverage: (coverage) => patch({ coverage }),
      saveReport: (r) => setDevice((d) => ({ ...d, memberReports: [r, ...d.memberReports] })),
      addMyCase: (id, chatToken) => {
        setDevice((d) => ({ ...d, myCaseIds: [id, ...d.myCaseIds] }));
        if (chatToken) setSession((s) => ({ ...s, chatTokens: { ...s.chatTokens, [id]: chatToken } }));
      },
      reports: device.memberReports,
      clearMyData: () => {
        // 이 계정의 기기 저장소를 지우고 로그아웃한다(서버 세션은 화면이 api/auth.ts의 logoutWorker로 지운다)
        if (account) removeKey(localStorage, deviceKey(account.key));
        switchAccount(null);
        clearInputs();
      },
    };
  }, [session, device, meta, account, patch, switchAccount]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('AppStateProvider 안에서만 사용할 수 있습니다');
  return ctx;
}

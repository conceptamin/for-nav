// 근로자 영역 상태.
// - 세션(sessionStorage): 언어, 동의, 이용 방식, 현재 증상 입력·판정, 제도 경로 결과, 비회원 리포트
//   → 비회원 입력은 브라우저 세션이 끝나면 사라진다.
// - 기기(localStorage): 회원 프로필, 회원 리포트, 회원이 보낸 센터 사례 id
// - 메모리: 서버 설정값(정보 기준일·센터 운영 시간). 저장하지 않고 시작할 때마다 GET /api/meta로 받는다

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { loadMeta } from '../api/meta';
import type { CoverageInput, CoverageResult, Meta } from '../domain/coverage';
import { DEFAULT_META } from '../domain/coverage';
import type { ClinicianReport, Profile } from '../domain/templates';
import type { Intake, TriageResult } from '../domain/triage';
import type { Lang } from '../domain/vocab';
import { readJson, removeKey, writeJson } from './storage';

export interface Consents {
  terms: boolean;
  sensitive: boolean;
  ai: boolean;
}

interface SessionState {
  lang: Lang | null;
  consents: Consents;
  mode: 'guest' | 'member' | null;
  intake: Intake | null;
  triage: TriageResult | null;
  /** 이번 세션에서 응급 판정이 한 번이라도 있었는지(센터 긴급도에 사용) */
  emergencySeen: boolean;
  coverage: { input: CoverageInput; result: CoverageResult } | null;
  guestReports: ClinicianReport[];
}

interface DeviceState {
  profile: Profile | null;
  memberReports: ClinicianReport[];
  myCaseIds: string[];
}

const SESSION_KEY = 'umn.session';
const DEVICE_KEY = 'umn.device';

const initialSession: SessionState = {
  lang: null,
  consents: { terms: false, sensitive: false, ai: false },
  mode: null,
  intake: null,
  triage: null,
  emergencySeen: false,
  coverage: null,
  guestReports: [],
};
const initialDevice: DeviceState = { profile: null, memberReports: [], myCaseIds: [] };

interface AppContextValue extends SessionState, DeviceState {
  /** 정보 기준일·센터 운영 시간. 단독 모드와 서버 실패 시에는 브라우저 상수다 */
  meta: Meta;
  setLang: (lang: Lang) => void;
  setConsents: (c: Consents) => void;
  startGuest: () => void;
  signUp: (p: Profile) => void;
  setIntake: (intake: Intake | null) => void;
  setTriage: (t: TriageResult | null) => void;
  setCoverage: (c: SessionState['coverage']) => void;
  saveReport: (r: ClinicianReport) => void;
  addMyCase: (id: string) => void;
  reports: ClinicianReport[];
  clearMyData: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState>(() => ({ ...initialSession, ...readJson(sessionStorage, SESSION_KEY, {}) }));
  const [device, setDevice] = useState<DeviceState>(() => ({ ...initialDevice, ...readJson(localStorage, DEVICE_KEY, {}) }));
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
  useEffect(() => writeJson(localStorage, DEVICE_KEY, device), [device]);

  useEffect(() => {
    document.documentElement.lang = session.lang ?? 'ko';
  }, [session.lang]);

  const patch = useCallback((p: Partial<SessionState>) => setSession((s) => ({ ...s, ...p })), []);

  const value = useMemo<AppContextValue>(() => {
    // 회원 정보가 기기에 있으면 회원으로 이어서 쓴다.
    const mode = session.mode ?? (device.profile ? 'member' : null);
    return {
      ...session,
      ...device,
      meta,
      mode,
      setLang: (lang) => patch({ lang }),
      setConsents: (consents) => patch({ consents }),
      startGuest: () => patch({ mode: 'guest' }),
      signUp: (profile) => {
        setDevice((d) => ({ ...d, profile }));
        patch({ mode: 'member' });
      },
      setIntake: (intake) => patch({ intake }),
      setTriage: (triage) =>
        setSession((s) => ({ ...s, triage, emergencySeen: s.emergencySeen || Boolean(triage?.emergency) })),
      setCoverage: (coverage) => patch({ coverage }),
      saveReport: (r) => {
        if (mode === 'member') setDevice((d) => ({ ...d, memberReports: [r, ...d.memberReports] }));
        else setSession((s) => ({ ...s, guestReports: [r, ...s.guestReports] }));
      },
      addMyCase: (id) => setDevice((d) => ({ ...d, myCaseIds: [id, ...d.myCaseIds] })),
      reports: mode === 'member' ? device.memberReports : session.guestReports,
      clearMyData: () => {
        removeKey(localStorage, DEVICE_KEY);
        setDevice(initialDevice);
        setSession((s) => ({ ...initialSession, lang: s.lang, consents: s.consents }));
      },
    };
  }, [session, device, meta, patch]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('AppStateProvider 안에서만 사용할 수 있습니다');
  return ctx;
}

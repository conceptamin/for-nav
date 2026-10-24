// 센터 접수함 저장소(GET/PATCH /center/cases 대응).
// 데모에서는 localStorage를 서버 DB 대신 쓴다. 같은 브라우저의 다른 탭(센터 화면)에도
// storage 이벤트로 즉시 반영되어 "근로자 전송 → 센터 접수함 도착(5초 이내)"을 시연할 수 있다.

import { useEffect, useState } from 'react';
import { buildMockCases } from '../data/mock';
import type { CaseStatus, CenterCase } from '../domain/centerCase';
import { readJson, writeJson } from './storage';

const LIVE_KEY = 'umn.center.liveCases';
const STATUS_KEY = 'umn.center.statusOverrides';
const CHANGE_EVENT = 'umn-center-change';

const mockCases = buildMockCases();

function loadAll(): CenterCase[] {
  const live = readJson<CenterCase[]>(localStorage, LIVE_KEY, []);
  const overrides = readJson<Record<string, CaseStatus>>(localStorage, STATUS_KEY, {});
  return [...live, ...mockCases]
    .map((c) => (overrides[c.id] ? { ...c, status: overrides[c.id]! } : c))
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export function addLiveCase(c: CenterCase): void {
  const live = readJson<CenterCase[]>(localStorage, LIVE_KEY, []);
  writeJson(localStorage, LIVE_KEY, [c, ...live]);
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function setCaseStatus(id: string, status: CaseStatus): void {
  const overrides = readJson<Record<string, CaseStatus>>(localStorage, STATUS_KEY, {});
  writeJson(localStorage, STATUS_KEY, { ...overrides, [id]: status });
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

/** 데모 초기화: 실제 전송 사례와 상태 변경을 지운다. */
export function resetCenterDemo(): void {
  writeJson(localStorage, LIVE_KEY, []);
  writeJson(localStorage, STATUS_KEY, {});
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function useCenterCases(): CenterCase[] {
  const [cases, setCases] = useState(loadAll);
  useEffect(() => {
    const refresh = () => setCases(loadAll());
    window.addEventListener('storage', refresh);
    window.addEventListener(CHANGE_EVENT, refresh);
    // 다른 기기·탭 이벤트를 놓친 경우를 대비한 2초 주기 갱신
    const timer = window.setInterval(refresh, 2000);
    return () => {
      window.removeEventListener('storage', refresh);
      window.removeEventListener(CHANGE_EVENT, refresh);
      window.clearInterval(timer);
    };
  }, []);
  return cases;
}

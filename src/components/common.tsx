// 근로자 화면 공통 컴포넌트

import type { ReactNode } from 'react';
import { useT } from '../i18n';
import type { YesNoUnknown } from '../domain/vocab';

/** 카카오맵 검색 링크(PRD Q4: 형식·사용 조건 확인 필요). 앱 미설치 시 웹으로 열린다. */
export function kakaoSearchUrl(query: string): string {
  return `https://map.kakao.com/link/search/${encodeURIComponent(query)}`;
}

/** 비응급 결과 화면마다 붙는 "심해지면 119" 안내 */
export function Worse119() {
  const { t } = useT();
  return (
    <div className="notice danger" role="note">
      🚑 {t('worse119')}
    </div>
  );
}

/** 제도·기관 정보 결과에 붙는 최종 결정 문구와 기준일 */
export function PolicyDisclaimer({ infoDate }: { infoDate: string }) {
  const { t } = useT();
  return (
    <p className="footer-note">
      ⓘ {t('covFinal')} · {t('covInfoDate')} {infoDate}
    </p>
  );
}

export function Chip({ pressed, onClick, children }: { pressed: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" className="chip" aria-pressed={pressed} onClick={onClick}>
      {children}
    </button>
  );
}

/** 예/아니요/모름 선택 */
export function YesNoSeg({
  value,
  onChange,
  withUnknown = true,
}: {
  value: YesNoUnknown | null;
  onChange: (v: YesNoUnknown) => void;
  withUnknown?: boolean;
}) {
  const { t } = useT();
  const opts: YesNoUnknown[] = withUnknown ? ['yes', 'no', 'unknown'] : ['yes', 'no'];
  return (
    <div className="seg" role="group">
      {opts.map((o) => (
        <Chip key={o} pressed={value === o} onClick={() => onChange(o)}>
          {t(o)}
        </Chip>
      ))}
    </div>
  );
}

/** 단일 선택 버튼 묶음 */
export function SingleSelect<K extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: K[];
  value: K | null;
  onChange: (v: K) => void;
  label: (k: K) => string;
}) {
  return (
    <div className="chips" role="group">
      {options.map((o) => (
        <Chip key={o} pressed={value === o} onClick={() => onChange(o)}>
          {label(o)}
        </Chip>
      ))}
    </div>
  );
}

export function toggleIn<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item];
}

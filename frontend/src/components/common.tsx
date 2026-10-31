// 근로자 화면 공통 컴포넌트

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { DATE_ORDER, dateFormat, hasDateLocale, useT, type DatePart } from '../i18n';
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

/**
 * 진행 막대 + `3 / 10`(backlog 35). 분모는 실제로 지나갈 화면 수다. 막대는 기본 `progress`라
 * 스크린리더가 값을 읽고, 옆 숫자는 같은 내용이라 aria-hidden이다
 */
export function Progress({ current, total, label }: { current: number; total: number; label: string }) {
  return (
    <div className="progress">
      <progress value={current} max={total} aria-label={label} />
      {/* RTL에서 `9 / 6`으로 뒤집히지 않게 숫자 묶음만 왼→오 */}
      <span className="count" dir="ltr" aria-hidden>
        {current} / {total}
      </span>
    </div>
  );
}

/** 예/아니요/모름 선택. 선택지 목록(가로 꽉, 왼쪽 정렬) */
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
    <div className="options" role="group">
      {opts.map((o) => (
        <Chip key={o} pressed={value === o} onClick={() => onChange(o)}>
          {t(o)}
        </Chip>
      ))}
    </div>
  );
}

const pad2 = (n: number) => String(n).padStart(2, '0');
const parseIso = (v: string) => {
  const [y, m, d] = v.split('-').map(Number);
  return { year: y || 0, month: m || 0, day: d || 0 };
};
const daysInMonth = (y: number, m: number) => new Date(Date.UTC(y, m, 0)).getUTCDate();

/**
 * 생년월일 고르기(backlog 34). 브라우저 기본 `input[type=date]`는 앱 언어가 아니라 휴대폰·브라우저 언어로
 * `연도-월-일` 자리표시를 그려서, 연·월·일 select 셋을 그 언어의 순서(`DATE_ORDER`)와 이름으로 둔다.
 * 셋을 다 골라야 'YYYY-MM-DD'를 내보내고, 하나라도 비면 ''를 내보낸다.
 */
export function BirthDateInput({
  id,
  value,
  onChange,
  minYear,
  maxYear,
}: {
  id?: string;
  value: string;
  onChange: (iso: string) => void;
  minYear: number;
  maxYear: number;
}) {
  const { lang, t } = useT();
  const [parts, setParts] = useState(() => parseIso(value));
  // 밖에서 값이 바뀌면(계정·프로필 전환) 따라간다. 고르는 중(일부만 고름)의 ''는 덮어쓰지 않는다
  useEffect(() => {
    if (value) setParts(parseIso(value));
    else setParts((p) => (p.year && p.month && p.day ? { year: 0, month: 0, day: 0 } : p));
  }, [value]);

  // 달 이름(그리고 1990년·28日 같은 꼬리)은 브라우저가 그 언어를 알 때만 Intl로, 모르면 숫자로 그린다
  const label = useMemo<Record<DatePart, (n: number) => string>>(() => {
    if (!hasDateLocale(lang)) return { year: String, month: String, day: String };
    const yearFmt = dateFormat(lang, { year: 'numeric' });
    const monthFmt = dateFormat(lang, { month: 'long' });
    const dayFmt = dateFormat(lang, { day: 'numeric' });
    return {
      year: (y) => yearFmt.format(Date.UTC(y, 0, 1)),
      month: (m) => monthFmt.format(Date.UTC(2000, m - 1, 1)),
      day: (d) => dayFmt.format(Date.UTC(2000, 0, d)),
    };
  }, [lang]);
  const names: Record<DatePart, string> = { year: t('dateYear'), month: t('dateMonth'), day: t('dateDay') };

  const range = (from: number, to: number) => Array.from({ length: to - from + 1 }, (_, i) => from + i);
  const options: Record<DatePart, number[]> = {
    year: range(minYear, maxYear).reverse(),
    month: range(1, 12),
    day: range(1, parts.year && parts.month ? daysInMonth(parts.year, parts.month) : 31),
  };

  const set = (part: DatePart, n: number) => {
    const next = { ...parts, [part]: n };
    // 2월 30일처럼 그 달에 없는 날은 그 달의 마지막 날로
    if (next.year && next.month && next.day) next.day = Math.min(next.day, daysInMonth(next.year, next.month));
    setParts(next);
    onChange(next.year && next.month && next.day ? `${next.year}-${pad2(next.month)}-${pad2(next.day)}` : '');
  };

  return (
    <div className="date-parts" role="group">
      {DATE_ORDER[lang].map((part, i) => (
        <select
          key={part}
          id={i === 0 ? id : undefined}
          className={`input ${part}`}
          aria-label={names[part]}
          value={parts[part] || ''}
          onChange={(e) => set(part, Number(e.target.value))}
        >
          <option value="" disabled>
            {names[part]}
          </option>
          {options[part].map((n) => (
            <option key={n} value={n}>
              {label[part](n)}
            </option>
          ))}
        </select>
      ))}
    </div>
  );
}

/** 하나 고르기. 선택지 목록(가로 꽉, 왼쪽 정렬) */
export function SingleSelect<K extends string>({
  options,
  value,
  onChange,
  label,
  inline,
}: {
  options: K[];
  value: K | null;
  onChange: (v: K) => void;
  label: (k: K) => string;
  /** 선택지가 둘셋뿐이고 글자가 짧을 때(성별·음주·흡연) 가로 칸 */
  inline?: boolean;
}) {
  return (
    <div className={inline ? 'options inline' : 'options'} role="group">
      {options.map((o) => (
        <Chip key={o} pressed={value === o} onClick={() => onChange(o)}>
          {label(o)}
        </Chip>
      ))}
    </div>
  );
}

/**
 * 통증 점수 슬라이더(0~10). 얼굴 → 단계 이름 → 숫자 → range → 양 끝 레이블.
 * 움직이기 전에는 값이 없다(답하지 않으면 키가 없다).
 */
export function PainRange({ value, onChange }: { value: number | undefined; onChange: (n: number) => void }) {
  const { t } = useT();
  const n = value ?? 0;
  const face = n <= 3 ? '🙂' : n <= 6 ? '😐' : '😣';
  const level = n <= 3 ? t('painMild') : n <= 6 ? t('painModerate') : t('painSevere');
  return (
    <div className="range">
      <div className="face" aria-hidden>
        {face}
      </div>
      <p className="level">{level}</p>
      <div className="num">{value === undefined ? '–' : value}</div>
      <input type="range" min={0} max={10} step={1} value={n} aria-label={t('painQ')} onChange={(e) => onChange(Number(e.target.value))} />
      <div className="ends" aria-hidden>
        <span>0 · {t('painNone')}</span>
        <span>10 · {t('painWorst')}</span>
      </div>
    </div>
  );
}

export const MAX_PHOTOS = 3;

export interface PhotoItem {
  url: string;
  name: string;
}

/**
 * 사진 올리기. 사진은 브라우저 메모리(object URL)에만 두고 서버·저장소에 보내지 않는다(보낼 API가 없다).
 * 화면을 떠나면 URL을 해제해 사라진다.
 */
export function PhotoPicker({ photos, onChange }: { photos: PhotoItem[]; onChange: (p: PhotoItem[]) => void }) {
  const { t } = useT();
  const add = (files: FileList | null) => {
    if (!files) return;
    const room = MAX_PHOTOS - photos.length;
    const added = Array.from(files)
      .slice(0, Math.max(0, room))
      .map((f) => ({ url: URL.createObjectURL(f), name: f.name }));
    if (added.length) onChange([...photos, ...added]);
  };
  const remove = (i: number) => {
    URL.revokeObjectURL(photos[i].url);
    onChange(photos.filter((_, j) => j !== i));
  };
  return (
    <div>
      <div className="photos-head">
        <span className="small">{t('photosTitle')}</span>
        <span className="small muted">
          {photos.length}/{MAX_PHOTOS}
        </span>
      </div>
      <hr className="divider" />
      <div className="photos">
        {photos.length < MAX_PHOTOS && (
          <label className="photo-add">
            <span>
              <span className="plus" aria-hidden>
                +
              </span>
              {t('photoAdd')}
            </span>
            <input type="file" accept="image/*" multiple onChange={(e) => { add(e.target.files); e.target.value = ''; }} />
          </label>
        )}
        {photos.map((p, i) => (
          <div className="photo" key={p.url}>
            <img src={p.url} alt={p.name} />
            <button type="button" className="rm" aria-label={`${t('photoRemove')} ${i + 1}`} onClick={() => remove(i)}>
              ✕
            </button>
          </div>
        ))}
      </div>
      <p className="footer-note">{t('photosNote')}</p>
    </div>
  );
}

/** 화면이 사라질 때 object URL을 해제한다. 사진 상태를 가진 화면에서 한 번 부른다 */
export function usePhotoCleanup(photos: PhotoItem[]) {
  const ref = useRef(photos);
  ref.current = photos;
  useEffect(() => () => ref.current.forEach((p) => URL.revokeObjectURL(p.url)), []);
}

export function toggleIn<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item];
}

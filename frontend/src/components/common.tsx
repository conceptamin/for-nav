// 근로자 화면 공통 컴포넌트

import { useEffect, useRef, type ReactNode } from 'react';
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

/** 단계 숫자 원. 장식이라 aria-hidden이고, 단계 수는 글로 알려 주지 않는다(design.md "접근성") */
export function Steps({ count, current }: { count: number; current: number }) {
  return (
    <ol className="steps" aria-hidden>
      {Array.from({ length: count }, (_, i) => (
        <li key={i} className={i === current ? 'on' : undefined}>
          {i + 1}
        </li>
      ))}
    </ol>
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

// S-01 언어 선택, S-02 약관 동의, S-03 로그인(데모) → 프로필, S-04 홈
// 온보딩 세 화면. 배치는 Figma 화면 골격(backlog/08-figma-layout.md)을 따른다.

import { useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { SingleSelect } from '../../components/common';
import { useScreenBar } from '../../components/WorkerLayout';
import { LANGUAGE_OPTIONS, translate, useT } from '../../i18n';
import type { Consents } from '../../state/AppState';
import { useApp } from '../../state/AppState';
import type { Profile } from '../../domain/templates';
import { suggestLangs } from '../../i18n/suggest';
import { LOCALES, RTL_LANGS, SEXES, type Lang } from '../../domain/vocab';

// ---------------------------------------------------------------------------
// S-01: 언어 격자(backlog 24). 폰 언어로 묻고, 20개 언어를 같은 크기 칸(국기 + 모국어 이름 + 영어 이름) 두 줄 격자로 모두 보인다.
// 폰 언어 추천(suggestLangs)은 위 격자에 바탕색만 다르게, 나머지는 "다른 언어" 아래 격자에. 앱 바가 없다.
// ---------------------------------------------------------------------------
const LANG_OPTION = new Map(LANGUAGE_OPTIONS.map((o) => [o.lang, o]));

export function LanguagePage() {
  const app = useApp();
  const navigate = useNavigate();
  useScreenBar({ hidden: true });
  const consented = app.consents.terms && app.consents.sensitive && app.consents.ai;
  const { first, suggested, rest } = useMemo(
    () => suggestLangs(navigator.languages ?? [navigator.language], LANGUAGE_OPTIONS.map((o) => o.lang)),
    [],
  );
  // 질문은 폰 언어로. 폰 언어를 모르면 영어로 묻고, 영어가 아니면 아래에 영어 한 줄을 붙인다(추천이 틀렸을 때를 위해)
  const ask: Lang = first ?? 'en';
  const choose = (lang: Lang) => {
    app.setLang(lang);
    navigate(consented ? (app.mode ? '/home' : '/signup') : '/consent');
  };

  const tile = (l: Lang, suggest = false) => {
    const o = LANG_OPTION.get(l);
    return (
      <button key={l} type="button" className={suggest ? 'tile suggest' : 'tile'} lang={l} onClick={() => choose(l)}>
        <span className="flag" aria-hidden="true">
          {o?.flag}
        </span>
        <span className="name">
          <strong>{o?.native}</strong>
          {l !== 'en' && (
            <span className="en" lang="en">
              {o?.english}
            </span>
          )}
        </span>
      </button>
    );
  };

  return (
    <div className="w-screen w-lang" dir={RTL_LANGS.includes(ask) ? 'rtl' : undefined}>
      <div className="ask" lang={ask}>
        <h1>{translate(ask, 'langAsk')}</h1>
        {ask !== 'en' && (
          <p className="small muted" lang="en" dir="ltr">
            {translate('en', 'langAsk')}
          </p>
        )}
      </div>
      <div className="lang-grid">{suggested.map((l) => tile(l, true))}</div>
      <h2 lang={ask}>{translate(ask, 'langOther')}</h2>
      <div className="lang-grid">{rest.map((l) => tile(l))}</div>
      <p className="footer-note" lang={ask}>
        {translate(ask, 'langHint')}
      </p>
      <p className="footer-note" style={{ textAlign: 'center' }}>
        <Link to="/center">센터 상담원 화면 →</Link>
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-02: 이용약관·민감정보·외부 AI 고지를 분리해 각각 동의받는다.
// 전체 동의 한 줄 → 구분선 → 항목 줄(체크 + 제목 + › 가 한 면, 전문은 같은 화면 안에서 펼친다) → 바닥 다음. 단계 원은 없다.
// ---------------------------------------------------------------------------
export function ConsentPage() {
  const app = useApp();
  const { t } = useT();
  const navigate = useNavigate();
  const [c, setC] = useState<Consents>(app.consents);
  const [open, setOpen] = useState<keyof Consents | null>(null);
  const all = c.terms && c.sensitive && c.ai;
  useScreenBar({ title: t('consentTitle'), onBack: () => navigate('/') });

  const items: { key: keyof Consents; title: string; body: string }[] = [
    { key: 'terms', title: t('consentTermsTitle'), body: t('consentTermsBody') },
    { key: 'sensitive', title: t('consentSensitiveTitle'), body: t('consentSensitiveBody') },
    { key: 'ai', title: t('consentAiTitle'), body: t('consentAiBody') },
  ];

  return (
    <div className="w-screen">
      <h1>{t('consentTitle')}</h1>
      <label className="check">
        <input type="checkbox" checked={all} onChange={(e) => setC({ terms: e.target.checked, sensitive: e.target.checked, ai: e.target.checked })} />
        <span>
          <strong>{t('consentAll')}</strong>
          <span className="small muted">{t('consentIntro')}</span>
        </span>
      </label>
      <hr className="divider" />
      <div className="stack">
        {items.map((it) => (
          <div key={it.key}>
            <div className="check-row">
              <label className="check">
                <input type="checkbox" checked={c[it.key]} onChange={(e) => setC({ ...c, [it.key]: e.target.checked })} />
                <span>
                  <span className="small muted">[{t('required')}]</span> {it.title}
                </span>
              </label>
              <button
                type="button"
                className="btn ghost"
                aria-expanded={open === it.key}
                aria-label={`${t('consentReadFull')}: ${it.title}`}
                onClick={() => setOpen(open === it.key ? null : it.key)}
              >
                {open === it.key ? '⌄' : '›'}
              </button>
            </div>
            {open === it.key && <p className="small muted">{it.body}</p>}
          </div>
        ))}
      </div>
      <p className="footer-note">{t('consentCenterLater')}</p>
      {!all && <p className="small muted">{t('consentNeedAll')}</p>}
      <footer className="w-footer">
        <button
          type="button"
          className="btn block"
          disabled={!all}
          onClick={() => {
            app.setConsents(c);
            navigate(app.mode ? '/home' : '/signup');
          }}
        >
          {t('next')}
        </button>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-03: 로그인(데모) → 프로필. 서버에 인증이 없으므로 Google 버튼은 회원 모드로 들어가 프로필로 간다.
// 프로필의 필수는 생년월일·성별뿐. 이름·연락처·체류 자격은 받지 않는다.
// ---------------------------------------------------------------------------
export function SignupPage() {
  const app = useApp();
  const { t } = useT();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = params.get('next') ?? '/home';
  // 회원이 /my의 '프로필 수정'으로 들어오면(next가 있고 프로필이 있다) 로그인 화면을 건너뛰고 프로필 단계로 간다
  const editing = app.mode === 'member' && Boolean(app.profile) && params.has('next');
  const [form, setForm] = useState(editing);
  const [p, setP] = useState<Profile>(
    app.profile ?? { birthDate: '', sex: 'male', height: null, weight: null, drinking: null, smoking: null },
  );
  const [sexChosen, setSexChosen] = useState(Boolean(app.profile));
  const valid = /^\d{4}-\d{2}-\d{2}$/.test(p.birthDate) && sexChosen;
  const num = (v: string) => (v ? Math.max(0, Number(v)) || null : null);
  // 로그인은 로고 화면이라 앱 바가 없다. 프로필 단계에서만 ← 가 있다
  useScreenBar({
    title: form ? t('profileTitle') : t('loginTitle'),
    hidden: !form,
    onBack: () => (form ? (editing ? navigate(next) : setForm(false)) : navigate('/consent')),
  });

  if (!form) {
    return (
      <div className="w-screen">
        <div className="w-logo">
          <img className="mark" src="/logo.png" width="64" height="64" alt="" />
          <h1>{t('appName')}</h1>
          <p className="muted">{t('appTag')}</p>
        </div>
        <div className="stack">
          <button type="button" className="btn secondary block big" onClick={() => setForm(true)}>
            <span className="mark" aria-hidden>
              G
            </span>
            {t('loginGoogle')}
          </button>
          <button
            type="button"
            className="btn ghost block"
            onClick={() => {
              app.startGuest();
              navigate(next);
            }}
          >
            {t('loginGuest')}
          </button>
          <p className="footer-note">{t('loginDemoNote')}</p>
          <p className="footer-note">🔒 {t('signupNoVisa')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-screen">
      <h1>{t('profileTitle')}</h1>
      <p className="small muted">🔒 {t('signupNoVisa')}</p>
      <div className="field">
        <label htmlFor="bd">
          {t('birthDate')} <span className="small muted">({t('required')})</span>
        </label>
        <input id="bd" type="date" value={p.birthDate} max="2010-12-31" onChange={(e) => setP({ ...p, birthDate: e.target.value })} />
      </div>
      <div className="field">
        <span className="label">
          {t('sex')} <span className="small muted">({t('required')})</span>
        </span>
        <SingleSelect
          inline
          options={['male', 'female'] as Profile['sex'][]}
          value={sexChosen ? p.sex : null}
          onChange={(s) => {
            setSexChosen(true);
            setP({ ...p, sex: s });
          }}
          label={(k) => t(k)}
        />
      </div>
      <div className="row" style={{ alignItems: 'flex-start' }}>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="h">
            {t('heightCm')} <span className="small muted">({t('optional')})</span>
          </label>
          <input id="h" type="number" inputMode="numeric" value={p.height ?? ''} onChange={(e) => setP({ ...p, height: num(e.target.value) })} />
        </div>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="w">
            {t('weightKg')} <span className="small muted">({t('optional')})</span>
          </label>
          <input id="w" type="number" inputMode="numeric" value={p.weight ?? ''} onChange={(e) => setP({ ...p, weight: num(e.target.value) })} />
        </div>
      </div>
      <div className="field">
        <span className="label">
          {t('drinking')} <span className="small muted">({t('optional')})</span>
        </span>
        <SingleSelect
          inline
          options={['none', 'sometimes', 'often'] as NonNullable<Profile['drinking']>[]}
          value={p.drinking}
          onChange={(v) => setP({ ...p, drinking: v })}
          label={(k) => t(({ none: 'drinkNone', sometimes: 'drinkSometimes', often: 'drinkOften' } as const)[k])}
        />
      </div>
      <div className="field">
        <span className="label">
          {t('smoking')} <span className="small muted">({t('optional')})</span>
        </span>
        <SingleSelect
          inline
          options={['no', 'yes', 'quit'] as NonNullable<Profile['smoking']>[]}
          value={p.smoking}
          onChange={(v) => setP({ ...p, smoking: v })}
          label={(k) => t(({ no: 'smokeNo', yes: 'smokeYes', quit: 'smokeQuit' } as const)[k])}
        />
      </div>
      <footer className="w-footer">
        <button
          type="button"
          className="btn block"
          disabled={!valid}
          onClick={() => {
            app.signUp(p);
            navigate(next);
          }}
        >
          {t('signupSave')}
        </button>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-04 홈. 심토미 홈 배치로 나 줄 → 시작 카드 → 기능 목록 → 최근 메모(있을 때)(backlog/23-home-simtomi.md,
// design.md "홈"). 나 줄에는 출생 연도만 쓴다(어깨 너머로 보이는 화면). 최근 메모 카드에 판정은 보이지 않는다.
// ---------------------------------------------------------------------------
export function HomePage() {
  const app = useApp();
  const { t, term } = useT();
  const menu = [
    { to: '/guide', ico: '🏥', title: t('menuGuide'), sub: t('menuGuideSub') },
    { to: '/coverage', ico: '💳', title: t('menuCoverage'), sub: t('menuCoverageSub') },
    { to: '/center-request', ico: '🤝', title: t('menuCenter'), sub: t('menuCenterSub') },
    { to: '/my', ico: '👤', title: t('menuMy'), sub: t('menuMySub') },
  ];
  const profile = app.mode === 'member' ? app.profile : null;
  const recent = app.reports[0];
  const recentSymptoms = recent?.rows.find((row) => row.field === 'symptoms') ?? recent?.rows[0];
  const recentParts = recent?.rows.find((row) => row.field === 'bodyParts');
  return (
    <div className="stack wide">
      {profile ? (
        <Link to="/my" className="row link home-me">
          <span>
            {term(SEXES[profile.sex])} · {profile.birthDate.slice(0, 4)}
          </span>
          <span className="chev" aria-hidden>
            ›
          </span>
        </Link>
      ) : (
        <Link to="/signup" className="row link home-me">
          <span>
            {t('modeGuest')} · {t('myProfileCreate')}
          </span>
          <span className="chev" aria-hidden>
            ›
          </span>
        </Link>
      )}
      <Link to="/intake" className="home-hero">
        <strong>{t('menuSick')}</strong>
        <span className="sub">{t('menuSickSub')}</span>
        <span className="go">{t('homeStart')}</span>
      </Link>
      <nav className="home-list">
        {menu.map((m) => (
          <Link key={m.to} to={m.to}>
            <span className="ico" aria-hidden>
              {m.ico}
            </span>
            <span className="txt">
              <small>{m.sub}</small>
              <strong>{m.title}</strong>
            </span>
            <span className="chev" aria-hidden>
              ›
            </span>
          </Link>
        ))}
      </nav>
      {recent && (
        <>
          <h2 className="home-h2">{t('homeRecent')}</h2>
          <Link to={`/report/${recent.id}`} className="card home-recent">
            <strong>{recentSymptoms?.valueNative}</strong>
            {recentParts && (
              <p>
                {recentParts.labelNative}: {recentParts.valueNative}
              </p>
            )}
            <p className="muted">
              🕓 {new Date(recent.createdAt).toLocaleDateString(LOCALES[recent.language], { year: 'numeric', month: '2-digit', day: '2-digit' })}
            </p>
          </Link>
        </>
      )}
    </div>
  );
}

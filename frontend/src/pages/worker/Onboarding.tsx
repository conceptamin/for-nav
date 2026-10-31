// S-01 언어 선택, S-02 약관 동의, S-03 로그인(Google 또는 데모) → 프로필, S-04 홈
// 온보딩 세 화면. 배치는 Figma 화면 골격(backlog/08-figma-layout.md)을 따른다.

import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { checkWorkerAuth, loginWithGoogle, logoutWorker, useWorkerAuth } from '../../api/auth';
import { hasGoogleClientId, renderGoogleButton, useNativeGoogleSignIn, type NativeGoogleSignIn } from '../../api/googleId';
import { BirthDateInput, SingleSelect } from '../../components/common';
import { useScreenBar } from '../../components/WorkerLayout';
import { HOME_MENU, SICK_MENU } from '../../components/workerMenu';
import { LANGUAGE_OPTIONS, translate, useT } from '../../i18n';
import type { Consents } from '../../state/AppState';
import { DEMO_ACCOUNT, useApp } from '../../state/AppState';
import type { Profile } from '../../domain/templates';
import { orderLangs } from '../../i18n/suggest';
import { LOCALES, RTL_LANGS, SEXES, type Lang } from '../../domain/vocab';

// ---------------------------------------------------------------------------
// S-01: 언어 격자(backlog 24). 폰 언어로 묻고, 20개 언어를 같은 크기·같은 모양 칸(국기 + 모국어 이름 + 영어 이름)의
// 두 줄 격자 하나로 모두 보인다. 폰 언어 하나만 맨 앞에 오고 나머지는 정해진 순서다. 앱 바가 없다.
// ---------------------------------------------------------------------------
const LANG_OPTION = new Map(LANGUAGE_OPTIONS.map((o) => [o.lang, o]));

export function LanguagePage() {
  const app = useApp();
  const navigate = useNavigate();
  useScreenBar({ hidden: true });
  const consented = app.consents.terms && app.consents.sensitive && app.consents.ai;
  const { first, langs } = useMemo(
    () => orderLangs(navigator.languages ?? [navigator.language], LANGUAGE_OPTIONS.map((o) => o.lang)),
    [],
  );
  // 질문은 폰 언어로. 폰 언어를 모르면 영어로 묻고, 영어가 아니면 아래에 영어 한 줄을 붙인다(폰 언어가 본인 언어가 아닐 때를 위해)
  const ask: Lang = first ?? 'en';
  const choose = (lang: Lang) => {
    app.setLang(lang);
    navigate(consented ? (app.ready ? '/home' : '/signup') : '/consent');
  };

  const tile = (l: Lang) => {
    const o = LANG_OPTION.get(l);
    return (
      <button key={l} type="button" className="tile" lang={l} onClick={() => choose(l)}>
        <img className="flag" src={`/flags/${o?.country}.svg`} width="32" height="24" alt="" />
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
      <div className="lang-grid">{langs.map(tile)}</div>
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
            navigate(app.ready ? '/home' : '/signup');
          }}
        >
          {t('next')}
        </button>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-03: 로그인 → 프로필(backlog 28). 비회원은 없다.
// 서버가 Google 로그인을 쓰면(API 모드, WORKER_AUTH=google) Google 공식 버튼으로 로그인하고 서버 세션을 받는다.
// 앱이 네이티브 로그인을 등록했으면(backlog 35) GIS 대신 앱 로그인 버튼이고, 받은 ID 토큰을 같은 길로 서버에 보낸다.
// 단독 모드나 서버가 쓰지 않으면 지금처럼 데모 버튼(G 글자)이 이 기기의 데모 계정으로 들어간다.
// 로그인한 뒤 프로필이 없으면 프로필 단계다. 필수는 생년월일·성별뿐이고 이름·연락처·체류 자격은 받지 않는다.
// ---------------------------------------------------------------------------

const EMPTY_PROFILE: Profile = { birthDate: '', sex: 'male', height: null, weight: null, drinking: null, smoking: null };

/** 로그인 뒤 돌아갈 곳. 앱 안 경로만 받는다 */
function safeNext(next: string | null): string {
  return next && next.startsWith('/') && !next.startsWith('//') ? next : '/home';
}

function GoogleLogin({ onCredential }: { onCredential: (credential: string) => void }) {
  const { t, lang } = useT();
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const cb = useRef(onCredential);
  cb.current = onCredential;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let alive = true;
    setFailed(false);
    renderGoogleButton(el, LOCALES[lang], (c) => cb.current(c)).catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [lang, attempt]);

  return (
    <>
      <div className="gsi-button" ref={ref} hidden={failed} />
      {failed && (
        <div className="notice warn with-retry" role="alert">
          <span>{t('loginFailed')}</span>
          <button type="button" className="btn secondary" onClick={() => setAttempt((n) => n + 1)}>
            {t('retry')}
          </button>
        </div>
      )}
    </>
  );
}

/** 앱 안 네이티브 로그인 버튼. Google 브랜드 규정(흰 바탕, 공식 G 로고)을 따른다(design.md "근로자 로그인") */
function NativeGoogleButton({ onClick }: { onClick: () => void }) {
  const { t } = useT();
  return (
    <button type="button" className="btn google block" onClick={onClick}>
      <img className="g-logo" src="/google-g.svg" width="20" height="20" alt="" />
      {t('loginGoogle')}
    </button>
  );
}

export function SignupPage() {
  const app = useApp();
  const { t } = useT();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get('next'));
  const workerAuth = useWorkerAuth();
  const nativeSignIn = useNativeGoogleSignIn();
  // 로그인하고 프로필까지 있는 채로 들어오면(/my의 '프로필 수정'·'프로필 추가') 프로필 단계를 보인다. 들어올 때 정하고,
  // 로그아웃으로 계정이 비면 푼다(그 뒤 로그인한 사람은 프로필이 있으면 바로 next로 간다)
  const [editing, setEditing] = useState(() => app.ready);
  // `?new=1`(/my의 '프로필 추가')이면 빈 칸으로 열고, 저장하면 같은 계정에 프로필을 하나 더 만든다(backlog 34)
  const adding = editing && params.get('new') === '1';
  useEffect(() => {
    if (!app.account) setEditing(false);
  }, [app.account]);
  const form = Boolean(app.account) && (!app.profile || editing);
  const start = adding ? null : app.profile;
  const [p, setP] = useState<Profile>(start ?? EMPTY_PROFILE);
  const [sexChosen, setSexChosen] = useState(Boolean(start));
  const [signingIn, setSigningIn] = useState(false);
  const [loginFailed, setLoginFailed] = useState(false);
  const valid = /^\d{4}-\d{2}-\d{2}$/.test(p.birthDate) && sexChosen;
  const num = (v: string) => (v ? Math.max(0, Number(v)) || null : null);

  // 로그인했고 프로필도 있으면(다른 계정에서 이미 만들었으면) 이 화면에 머물 일이 없다
  useEffect(() => {
    if (app.ready && !editing) navigate(next, { replace: true });
  }, [app.ready, editing, next, navigate]);
  // 계정이 바뀌면(로그아웃·로그인) 그 계정의 프로필로 입력칸을 다시 채운다. 앞 계정의 값이 남지 않게 비우기도 한다
  // 추가 중에는 지금 프로필로 채우지 않는다
  useEffect(() => {
    if (adding) return;
    setP(app.profile ?? EMPTY_PROFILE);
    setSexChosen(Boolean(app.profile));
  }, [app.account, app.profile, adding]);

  // 처음 로그인한 사람의 ← 는 로그인 화면으로 돌아간다(로그아웃). 프로필 없이 홈으로 가는 길을 만들지 않는다
  const backToLogin = () => {
    app.signOut();
    void logoutWorker();
  };
  // 로그인은 로고 화면이라 앱 바가 없다. 프로필 단계에서만 ← 가 있다
  useScreenBar({
    title: form ? t(adding ? 'profileAdd' : 'profileTitle') : t('loginTitle'),
    hidden: !form,
    onBack: () => (form ? (editing ? navigate(next) : backToLogin()) : navigate('/consent')),
  });

  // ID 토큰을 얻는 길(GIS 콜백·앱 네이티브)만 다르고 서버로 보내는 것은 같다. null은 사용자가 계정 선택을 닫은 것이라 문구 없이 버튼으로 돌아간다
  const signInWith = async (getCredential: () => Promise<string | null>) => {
    setSigningIn(true);
    setLoginFailed(false);
    try {
      const credential = await getCredential();
      if (credential) app.signIn(await loginWithGoogle(credential), 'google');
    } catch {
      setLoginFailed(true);
    } finally {
      setSigningIn(false);
    }
  };
  const onCredential = (credential: string) => signInWith(async () => credential);
  const onNative = (signIn: NativeGoogleSignIn) => signInWith(signIn);

  if (!form) {
    const real = workerAuth.status === 'ready' && workerAuth.required;
    return (
      <div className="w-screen">
        <div className="w-logo">
          <img className="mark" src="/mark.png" width="64" height="64" alt="" />
          <h1>
            <img className="wordmark" src="/wordmark.png" width="107" height="28" alt={t('appName')} />
          </h1>
          <p className="muted">{t('appTag')}</p>
        </div>
        <div className="stack">
          {workerAuth.status === 'failed' ? (
            <div className="notice warn with-retry" role="alert">
              <span>{t('loginFailed')}</span>
              <button type="button" className="btn secondary" onClick={() => void checkWorkerAuth()}>
                {t('retry')}
              </button>
            </div>
          ) : real && !nativeSignIn && !hasGoogleClientId() ? (
            <div className="notice warn" role="alert">
              {t('loginNotConfigured')}
            </div>
          ) : real ? (
            <>
              {!signingIn &&
                (nativeSignIn ? (
                  <NativeGoogleButton onClick={() => void onNative(nativeSignIn)} />
                ) : (
                  <GoogleLogin onCredential={(c) => void onCredential(c)} />
                ))}
              {signingIn && (
                <button type="button" className="btn secondary block big" disabled>
                  {t('loginGoogle')}
                </button>
              )}
              {loginFailed && (
                <div className="notice warn" role="alert">
                  {t('loginFailed')}
                </div>
              )}
              <p className="footer-note">🔒 {t('loginGoogleNote')}</p>
            </>
          ) : (
            <>
              <button
                type="button"
                className="btn secondary block big"
                disabled={workerAuth.status === 'checking'}
                onClick={() => app.signIn(DEMO_ACCOUNT, 'demo')}
              >
                <span className="mark" aria-hidden>
                  G
                </span>
                {t('loginGoogle')}
              </button>
              {workerAuth.status === 'ready' && <p className="footer-note">{t('loginDemoNote')}</p>}
            </>
          )}
          <p className="footer-note">🔒 {t('signupNoVisa')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-screen">
      <h1>{t(adding ? 'profileAdd' : 'profileTitle')}</h1>
      <p className="small muted">🔒 {t('signupNoVisa')}</p>
      <div className="field">
        <label htmlFor="bd">
          {t('birthDate')} <span className="small muted">({t('required')})</span>
        </label>
        <BirthDateInput id="bd" value={p.birthDate} minYear={1940} maxYear={2010} onChange={(birthDate) => setP({ ...p, birthDate })} />
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
            if (adding) app.addProfile(p);
            else app.saveProfile(p);
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
  const profile = app.profile;
  const recent = app.reports[0];
  const recentSymptoms = recent?.rows.find((row) => row.field === 'symptoms') ?? recent?.rows[0];
  const recentParts = recent?.rows.find((row) => row.field === 'bodyParts');
  return (
    <div className="stack wide">
      {profile && (
        <Link to="/my" className="row link home-me">
          <span>
            {term(SEXES[profile.sex])} · {profile.birthDate.slice(0, 4)}
          </span>
          <span className="chev" aria-hidden>
            ›
          </span>
        </Link>
      )}
      <Link to={SICK_MENU.to} className="home-hero">
        <strong>{t(SICK_MENU.title)}</strong>
        <span className="sub">{t(SICK_MENU.sub)}</span>
        <span className="go">{t('homeStart')}</span>
      </Link>
      <nav className="home-list">
        {HOME_MENU.map((m) => (
          <Link key={m.to} to={m.to}>
            <span className="ico" aria-hidden>
              {m.ico}
            </span>
            <span className="txt">
              <small>{t(m.sub)}</small>
              <strong>{t(m.title)}</strong>
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
          {/* 링크 안에 버튼을 넣을 수 없어 카드 본문 링크와 삭제 버튼을 나눈다(backlog 52) */}
          <div className="card home-recent">
            <Link to={`/report/${recent.id}`}>
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
            <button
              type="button"
              className="btn ghost"
              onClick={() => {
                if (window.confirm(t('reportDeleteConfirm'))) app.deleteReport(recent.id);
              }}
            >
              🗑️ {t('reportDelete')}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

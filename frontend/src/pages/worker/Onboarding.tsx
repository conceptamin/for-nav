// S-01 언어 선택, S-02 약관 동의, S-03 회원가입·비회원, S-04 홈

import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { Chip, SingleSelect } from '../../components/common';
import { LANGUAGE_OPTIONS, useT } from '../../i18n';
import type { Consents } from '../../state/AppState';
import { useApp } from '../../state/AppState';
import type { Profile } from '../../domain/templates';

// ---------------------------------------------------------------------------
// S-01
// ---------------------------------------------------------------------------
export function LanguagePage() {
  const app = useApp();
  const navigate = useNavigate();
  const consented = app.consents.terms && app.consents.sensitive && app.consents.ai;
  return (
    <div className="stack">
      <div className="card" style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '2.4rem' }} aria-hidden>
          🏥
        </div>
        <h1>Choose your language</h1>
        <p className="muted">Chọn ngôn ngữ · 언어를 선택하세요</p>
      </div>
      {LANGUAGE_OPTIONS.map((o) => (
        <button
          key={o.lang}
          type="button"
          className="btn secondary block big"
          onClick={() => {
            app.setLang(o.lang);
            navigate(consented ? (app.mode ? '/home' : '/signup') : '/consent');
          }}
        >
          {o.native}
          {o.native !== o.english && <span className="muted small">({o.english})</span>}
        </button>
      ))}
      <p className="footer-note" style={{ textAlign: 'center' }}>
        <Link to="/center">센터 상담원 화면(데모) →</Link>
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-02: 이용약관·민감정보·외부 AI 고지를 분리해 각각 동의받는다.
// ---------------------------------------------------------------------------
export function ConsentPage() {
  const app = useApp();
  const { t } = useT();
  const navigate = useNavigate();
  const [c, setC] = useState<Consents>(app.consents);
  const all = c.terms && c.sensitive && c.ai;

  const items: { key: keyof Consents; title: string; body: string }[] = [
    { key: 'terms', title: t('consentTermsTitle'), body: t('consentTermsBody') },
    { key: 'sensitive', title: t('consentSensitiveTitle'), body: t('consentSensitiveBody') },
    { key: 'ai', title: t('consentAiTitle'), body: t('consentAiBody') },
  ];

  return (
    <div>
      <h1>{t('consentTitle')}</h1>
      <p className="muted">{t('consentIntro')}</p>
      <div className="stack" style={{ margin: '12px 0' }}>
        {items.map((it) => (
          <div className="card" key={it.key} style={{ marginBottom: 0 }}>
            <h2>
              {it.title} <span className="small muted">({t('required')})</span>
            </h2>
            <p className="small muted">{it.body}</p>
            <label className="check">
              <input type="checkbox" checked={c[it.key]} onChange={(e) => setC({ ...c, [it.key]: e.target.checked })} />
              <span>{t('consentAgree')}</span>
            </label>
          </div>
        ))}
      </div>
      <button type="button" className="btn secondary block" onClick={() => setC({ terms: true, sensitive: true, ai: true })}>
        {t('consentAll')}
      </button>
      <p className="footer-note">{t('consentCenterLater')}</p>
      {!all && <p className="small muted">{t('consentNeedAll')}</p>}
      <button
        type="button"
        className="btn block big"
        style={{ marginTop: 8 }}
        disabled={!all}
        onClick={() => {
          app.setConsents(c);
          navigate(app.mode ? '/home' : '/signup');
        }}
      >
        {t('next')}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-03: 필수는 생년월일·성별뿐. 이름·연락처·체류 자격은 받지 않는다.
// ---------------------------------------------------------------------------
export function SignupPage() {
  const app = useApp();
  const { t } = useT();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = params.get('next') ?? '/home';
  const [form, setForm] = useState(false);
  const [p, setP] = useState<Profile>(
    app.profile ?? { birthDate: '', sex: 'male', height: null, weight: null, drinking: null, smoking: null },
  );
  const [sexChosen, setSexChosen] = useState(Boolean(app.profile));
  const valid = /^\d{4}-\d{2}-\d{2}$/.test(p.birthDate) && sexChosen;
  const num = (v: string) => (v ? Math.max(0, Number(v)) || null : null);

  if (!form) {
    return (
      <div className="stack">
        <h1>{t('signupTitle')}</h1>
        <div className="card">
          <button
            type="button"
            className="btn block big secondary"
            onClick={() => {
              app.startGuest();
              navigate(next);
            }}
          >
            {t('guestBtn')}
          </button>
          <p className="small muted" style={{ marginTop: 8 }}>
            {t('guestHint')}
          </p>
        </div>
        <div className="card">
          <button type="button" className="btn block big" onClick={() => setForm(true)}>
            {t('memberBtn')}
          </button>
          <p className="small muted" style={{ marginTop: 8 }}>
            {t('memberHint')}
          </p>
        </div>
        <p className="footer-note">🔒 {t('signupNoVisa')}</p>
      </div>
    );
  }

  return (
    <div>
      <h1>{t('memberBtn')}</h1>
      <p className="small muted">🔒 {t('signupNoVisa')}</p>
      <div className="card">
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
          <div className="seg">
            {(['male', 'female'] as const).map((s) => (
              <Chip
                key={s}
                pressed={sexChosen && p.sex === s}
                onClick={() => {
                  setSexChosen(true);
                  setP({ ...p, sex: s });
                }}
              >
                {t(s)}
              </Chip>
            ))}
          </div>
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
            options={['no', 'yes', 'quit'] as NonNullable<Profile['smoking']>[]}
            value={p.smoking}
            onChange={(v) => setP({ ...p, smoking: v })}
            label={(k) => t(({ no: 'smokeNo', yes: 'smokeYes', quit: 'smokeQuit' } as const)[k])}
          />
        </div>
      </div>
      <button
        type="button"
        className="btn block big"
        disabled={!valid}
        onClick={() => {
          app.signUp(p);
          navigate(next);
        }}
      >
        {t('signupSave')}
      </button>
      <button type="button" className="btn ghost block" onClick={() => setForm(false)}>
        {t('back')}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// S-04
// ---------------------------------------------------------------------------
export function HomePage() {
  const app = useApp();
  const { t } = useT();
  const menu = [
    { to: '/intake', ico: '🤕', title: t('menuSick'), sub: t('menuSickSub'), primary: true },
    { to: '/guide', ico: '🏥', title: t('menuGuide'), sub: t('menuGuideSub') },
    { to: '/coverage', ico: '💳', title: t('menuCoverage'), sub: t('menuCoverageSub') },
    { to: '/center-request', ico: '🤝', title: t('menuCenter'), sub: t('menuCenterSub') },
    { to: '/my', ico: '📄', title: t('menuMy'), sub: t('menuMySub') },
  ];
  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
        <h1 style={{ margin: 0 }}>{t('homeHello')}</h1>
        <Link to="/signup" className="pill low" style={{ textDecoration: 'none' }}>
          {app.mode === 'member' ? t('modeMember') : t('modeGuest')}
        </Link>
      </div>
      <nav className="menu">
        {menu.map((m) => (
          <Link key={m.to} to={m.to} className={m.primary ? 'primary' : undefined}>
            <span className="ico" aria-hidden>
              {m.ico}
            </span>
            <span>
              <strong>{m.title}</strong>
              <small>{m.sub}</small>
            </span>
          </Link>
        ))}
      </nav>
    </div>
  );
}

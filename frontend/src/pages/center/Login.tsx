// C-00 센터 직원 로그인(backlog 27, backend 17). 이메일 → 메일로 받은 6자리 코드. 센터 화면이라 한국어 고정이다.
// 서버가 센터 로그인을 쓰지 않거나(CENTER_AUTH=off, 단독 모드) 이미 로그인했으면 바로 돌아간다.
// 등록되지 않은 이메일도 같은 안내를 본다(서버가 등록 여부를 알려 주지 않는다). 이메일·코드는 console에 찍지 않는다.

import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { AUTH_RESEND_MS, getMe, requestCode, safeFrom, verifyCode } from '../../api/auth';
import { clearCases } from '../../api/center';
import { ApiError } from '../../api/http';
import { CenterHeader } from './Center';

const TEXT = {
  title: '센터 직원 로그인',
  intro: '센터에 등록된 이메일로 6자리 로그인 코드를 보내 드립니다.',
  checking: '로그인을 확인하는 중입니다.',
  email: '이메일',
  sendCode: '코드 받기',
  sent: '등록된 이메일이면 코드를 보냈습니다. 메일함을 확인해 주세요. 코드는 10분 동안 쓸 수 있습니다.',
  code: '6자리 코드',
  login: '로그인',
  resend: '코드 다시 받기',
  resendWait: (s: number) => `코드 다시 받기 (${s}초)`,
  changeEmail: '이메일 바꾸기',
  wrong: '코드가 맞지 않거나 만료되었습니다.',
  invalid: '이메일 형식을 확인해 주세요.',
  rate: '요청이 너무 많습니다. 잠시 뒤 다시 시도해 주세요.',
  network: '서버에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.',
} as const;

type Problem = 'wrong' | 'invalid' | 'rate' | 'network';

export function CenterLoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const target = safeFrom(params.get('from'));
  const [checked, setChecked] = useState(false);
  const [step, setStep] = useState<'email' | 'code'>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [sentAt, setSentAt] = useState<number | null>(null);
  // 이 화면에서 코드 요청이 한 번이라도 받아들여졌는가("보냈습니다" 안내를 보일지)
  const [sent, setSent] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  // 로그인이 필요 없거나 이미 로그인했으면 이 화면에 머물 이유가 없다. 확인에 실패하면 화면을 그대로 보인다
  useEffect(() => {
    let alive = true;
    getMe().then(
      (me) => {
        if (!alive) return;
        if (!me.required || me.email) navigate(target, { replace: true });
        else setChecked(true);
      },
      () => alive && setChecked(true),
    );
    return () => {
      alive = false;
    };
  }, [navigate, target]);

  // "코드 다시 받기" 남은 초. 1초마다 한 번 다시 그린다(애니메이션 없음)
  const waitS = sentAt === null ? 0 : Math.max(0, Math.ceil((sentAt + AUTH_RESEND_MS - now) / 1000));
  useEffect(() => {
    if (waitS <= 0) return;
    const t = setTimeout(() => setNow(Date.now()), 1000);
    return () => clearTimeout(t);
  }, [waitS, now]);

  const fail = (e: unknown) => {
    const status = e instanceof ApiError ? e.status : null;
    // 서버가 로그인을 쓰지 않는다(404). 센터 화면으로 돌아간다
    if (status === 404) navigate(target, { replace: true });
    // 422는 서버가 형식을 거절했다(브라우저 email 검사는 통과한 "a@b" 등). 코드 단계에서는 틀린 코드와 같다
    else if (status === 422) setProblem(step === 'email' ? 'invalid' : 'wrong');
    else setProblem(status === 401 ? 'wrong' : status === 429 ? 'rate' : 'network');
    // 너무 자주 요청했으면 조금 전에 받은 코드가 아직 쓸 만하다. 코드 칸을 열고 다시 받기는 잠시 막는다
    if (status === 429) {
      const at = Date.now();
      setSentAt(at);
      setNow(at);
      setStep('code');
    }
  };

  const sendCode = async (e?: FormEvent) => {
    e?.preventDefault();
    if (busy || !email.trim()) return;
    setBusy(true);
    setProblem(null);
    try {
      await requestCode(email.trim());
      const at = Date.now();
      setSentAt(at);
      setNow(at);
      setSent(true);
      setCode('');
      setStep('code');
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  };

  const login = async (e: FormEvent) => {
    e.preventDefault();
    if (busy || code.length !== 6) return;
    setBusy(true);
    setProblem(null);
    try {
      await verifyCode(email.trim(), code);
      // 앞 사람의 접수함이 남아 있지 않게 비우고 들어간다
      clearCases();
      navigate(target, { replace: true });
    } catch (err) {
      fail(err);
      setBusy(false);
    }
  };

  const changeEmail = () => {
    setStep('email');
    setCode('');
    setProblem(null);
    setSentAt(null);
    setSent(false);
  };

  return (
    <div className="c-shell">
      <CenterHeader />
      <main className="c-login">
        <section className="card">
          <h1>{TEXT.title}</h1>
          {!checked ? (
            <p className="muted">{TEXT.checking}</p>
          ) : step === 'email' ? (
            <form onSubmit={sendCode}>
              <p className="muted">{TEXT.intro}</p>
              <div className="field">
                <label htmlFor="center-email">{TEXT.email}</label>
                <input
                  id="center-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={busy}
                />
              </div>
              {problem && (
                <div className="notice danger" role="alert">
                  {TEXT[problem]}
                </div>
              )}
              <button type="submit" className="btn block" disabled={busy || !email.trim()}>
                {TEXT.sendCode}
              </button>
            </form>
          ) : (
            <form onSubmit={login}>
              {sent && (
                <div className="notice info" role="status">
                  {TEXT.sent}
                </div>
              )}
              <div className="field">
                <label htmlFor="center-code">
                  {TEXT.code} · <span className="muted">{email.trim()}</span>
                </label>
                <input
                  id="center-code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  required
                  value={code}
                  // 붙여 넣은 "123 456"도 받도록 maxLength 대신 숫자만 남겨 6자리로 자른다
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  disabled={busy}
                />
              </div>
              {problem && (
                <div className="notice danger" role="alert">
                  {TEXT[problem]}
                </div>
              )}
              <button type="submit" className="btn block" disabled={busy || code.length !== 6}>
                {TEXT.login}
              </button>
              <div className="row">
                <button type="button" className="btn ghost" disabled={busy || waitS > 0} onClick={() => sendCode()}>
                  {waitS > 0 ? TEXT.resendWait(waitS) : TEXT.resend}
                </button>
                <button type="button" className="btn ghost" disabled={busy} onClick={changeEmail}>
                  {TEXT.changeEmail}
                </button>
              </div>
            </form>
          )}
        </section>
      </main>
    </div>
  );
}

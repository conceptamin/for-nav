// S-08 기초 정보 확인·제도 경로. 판정이 아니라 "먼저 상담할 곳" 안내다.

import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { PolicyDisclaimer, Worse119, YesNoSeg } from '../../components/common';
import { useT } from '../../i18n';
import { useApp } from '../../state/AppState';
import type { CoverageInput } from '../../domain/coverage';
import { routeCoverage } from '../../domain/coverage';
import type { YesNoUnknown } from '../../domain/vocab';

export function CoveragePage() {
  const app = useApp();
  const { t } = useT();
  const [work, setWork] = useState<YesNoUnknown | null>(app.coverage?.input.workRelated ?? app.intake?.workRelated ?? null);
  const [ins, setIns] = useState<YesNoUnknown | null>(app.coverage?.input.insurance ?? null);
  const [ulsan, setUlsan] = useState<YesNoUnknown | null>(app.coverage?.input.ulsan90 ?? null);

  const ready = work !== null && ins !== null && (ins !== 'no' || ulsan !== null);
  const input: CoverageInput | null = ready ? { workRelated: work, insurance: ins, ulsan90: ins === 'no' ? ulsan : null } : null;
  const result = input ? routeCoverage(input) : null;

  const { setCoverage } = app;
  useEffect(() => {
    if (input && result) setCoverage({ input, result });
    // 입력값이 바뀔 때만 저장한다(input·result는 매 렌더 새로 계산되므로 의존성에서 뺀다).
  }, [work, ins, ulsan]);

  return (
    <div>
      <h1>{t('covTitle')}</h1>
      <section className="card">
        <div className="field">
          <span className="label">{t('covWorkQ')}</span>
          <YesNoSeg value={work} onChange={setWork} />
        </div>
        <div className="field">
          <span className="label">{t('covInsQ')}</span>
          <YesNoSeg value={ins} onChange={setIns} />
        </div>
        {ins === 'no' && (
          <div className="field">
            <span className="label">{t('covUlsanQ')}</span>
            <YesNoSeg value={ulsan} onChange={setUlsan} />
          </div>
        )}
      </section>

      {result && (
        <section className="card" style={{ borderTop: '6px solid var(--ok)' }} aria-live="polite">
          <div className="small muted">{t('covResult')}</div>
          <h2 style={{ fontSize: '1.3rem' }}>{t(`path.${result.path}`)}</h2>
          <p>{t(`path.${result.path}.desc`)}</p>
          {result.alsoIndustrial && <div className="notice info">{t('covAlsoIndustrial')}</div>}

          <h3>{t('covDocs')}</h3>
          <ul style={{ marginTop: 0, paddingLeft: 20 }}>
            {result.docs.map((d) => (
              <li key={d}>{t(`doc.${d}`)}</li>
            ))}
          </ul>

          <h3>{t('covContacts')}</h3>
          <div className="stack" style={{ gap: 8 }}>
            {result.institutions.map((inst) => (
              <div key={inst.id} className="row" style={{ justifyContent: 'space-between', flexWrap: 'nowrap' }}>
                <span>{t(`inst.${inst.id}`)}</span>
                {inst.phone ? (
                  <a className="btn secondary" href={`tel:${inst.phone}`} style={{ minHeight: 44, whiteSpace: 'nowrap' }}>
                    ☎️ {inst.phone}
                  </a>
                ) : (
                  <span className="small muted" style={{ textAlign: 'right' }}>
                    {t('covConfirmAtCenter')}
                  </span>
                )}
              </div>
            ))}
          </div>
          <PolicyDisclaimer infoDate={result.infoDate} />
          <Link className="btn block" style={{ marginTop: 10 }} to="/center-request?type=policy">
            🤝 {t('covAskCenter')}
          </Link>
        </section>
      )}
      <Worse119 />
    </div>
  );
}

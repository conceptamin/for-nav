// 빌드 산출물이 외부 origin(CDN·폰트·지도 타일 등)을 참조하지 않는지 검사한다.
// HTML·CSS는 http(s) URL을 하나도 허용하지 않는다. JS는 브라우저가 요청하지 않는
// 식별자·오류 메시지 문자열만 허용한다. 실행 중 외부 요청 여부는 E2E가 따로 확인한다.
import { readdirSync, readFileSync } from 'node:fs';
import { extname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

// pathname은 Windows에서 드라이브 문자 앞에 / 가 붙고 비ASCII 문자가 퍼센트 인코딩된 채 남는다.
const DIST = fileURLToPath(new URL('../dist/', import.meta.url));

const JS_ALLOWED: ReadonlyArray<[prefix: string, reason: string]> = [
  ['http://www.w3.org/', 'SVG·MathML·XLink XML 네임스페이스 식별자(React DOM createElementNS)'],
  ['https://react.dev/errors/', 'React 프로덕션 오류 메시지의 문서 링크 문자열'],
  ['https://reactrouter.com/', 'React Router 경고 메시지의 문서 링크 문자열'],
  ['http://localhost', 'React Router가 상대 경로를 파싱할 때 쓰는 URL 기준값'],
];

function files(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory() ? files(join(dir, entry.name)) : [join(dir, entry.name)],
  );
}

const violations: string[] = [];
const allowed = new Map<string, number>();
const all = files(DIST);
for (const file of all) {
  const ext = extname(file);
  if (!['.html', '.css', '.js', '.mjs', '.svg', '.json', '.webmanifest'].includes(ext)) continue;
  for (const [url] of readFileSync(file, 'utf8').matchAll(/https?:\/\/[^\s"'`()<>\\]+/g)) {
    const rule = ext === '.js' || ext === '.mjs' ? JS_ALLOWED.find(([prefix]) => url.startsWith(prefix)) : undefined;
    if (rule) {
      allowed.set(rule[0], (allowed.get(rule[0]) ?? 0) + 1);
    } else {
      violations.push(`${relative(DIST, file)}: ${url}`);
    }
  }
}

if (all.length === 0) {
  console.error('dist가 비어 있습니다. npm run build를 먼저 실행하세요.');
  process.exit(1);
}
for (const [prefix, reason] of JS_ALLOWED) {
  if (allowed.has(prefix)) console.log(`허용 ${prefix} ×${allowed.get(prefix)}: ${reason}`);
}
if (violations.length > 0) {
  console.error(`외부 origin 참조 ${violations.length}건:\n${violations.join('\n')}`);
  process.exit(1);
}
console.log(`PASS: ${all.length}개 파일에 외부 origin 리소스 참조 없음`);

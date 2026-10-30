// 백엔드가 읽는 근로자 언어 묶음(backend/app/lang/packs.json, backend/app/vocab.py가 읽는다)을 프론트 src/domain/lang/에서 만든다.
// 번역 원본은 프론트다. packs.json을 손으로 고치지 않고, 언어 묶음을 바꾸면 이 명령으로 다시 만들어 함께 커밋한다.
//
//   cd frontend
//   npx rolldown scripts/dump-lang-packs.ts --file /tmp/packs.mjs --format esm \
//     && node /tmp/packs.mjs > ../backend/app/lang/packs.json

import { PACKS } from '../src/domain/lang';

console.log(JSON.stringify(PACKS, null, 2));

// "브라우저 결과를 먼저 그리고, 서버 결과가 오면 바꾼다"를 한 곳에 둔다.
// 버튼 없이 바로 뜨는 결과 화면(S-08 제도 경로, S-09·S-10 접수 도우미, S-12 요약 미리보기)이 쓴다.
// 서버 결과와 브라우저 결과가 같은 경로이므로 화면이 비거나 기다리는 순간이 없고,
// 서버가 실패하면 브라우저 결과가 그대로 남는다(README "경로별 대체 정책", 조용한 대체).

import { useEffect, useMemo, useState } from 'react';
import { isApiMode } from './http';

/**
 * @param key 입력을 문자열로 만든 것. 이 값이 바뀔 때만 다시 계산·요청한다
 * @param local 브라우저 함수. 같은 key에서는 한 번만 부른다
 * @param remote 서버를 부르는 함수. 실패하면 스스로 브라우저 결과를 돌려줘야 한다. null이면 부르지 않는다
 */
export function useServerResult<T>(key: string, local: () => T, remote: (() => Promise<T>) | null): T {
  // 같은 key에서는 같은 객체를 돌려줘, 화면이 결과를 의존성으로 써도 렌더마다 바뀌지 않게 한다.
  const localValue = useMemo(local, [key]);
  const [server, setServer] = useState<{ key: string; value: T } | null>(null);

  useEffect(() => {
    if (!remote || !isApiMode()) return;
    let alive = true;
    remote().then((value) => {
      // 늦게 온 응답이 바뀐 입력의 결과를 덮지 않게 한다.
      if (alive) setServer({ key, value });
    });
    return () => {
      alive = false;
    };
  }, [key]);

  return server && server.key === key ? server.value : localValue;
}

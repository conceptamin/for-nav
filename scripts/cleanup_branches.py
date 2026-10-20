#!/usr/bin/env python3
"""사람이 실행하는 병합 후 정리 도우미. develop을 최신화하고 PR 병합이 끝난 로컬 작업 브랜치를 지운다.

squash 병합은 develop에 새 커밋을 만들어 `git branch -d`가 브랜치를 미병합으로 본다. 이 스크립트는 로컬 브랜치
커밋이 모두 develop에 병합된 PR의 head에 같은 패치로 들어 있을 때만(병합 후 새 커밋이 없을 때만) 지운다. 원격 브랜치는 GitHub의
병합 후 자동 삭제 설정이 지우며 여기서는 push하지 않는다. AI는 --dry-run만 실행한다.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from git_flow import ROOT, context_path, git, load_config, merged_prs  # noqa: E402
from submit_pr import draft_path  # noqa: E402

KEEP = ('main', 'develop')


def contains_tip(root, tip, pr):
    """로컬 커밋이 모두 병합된 PR head에 같은 패치로 들어 있는지. GitHub의 Update branch(merge·rebase)로
    PR head만 앞서거나 다시 쓰인 경우다. git cherry의 '+'는 PR head에 없는 로컬 커밋이다."""
    git(root, 'fetch', '--quiet', 'origin', f"refs/pull/{pr['number']}/head")
    return not any(line.startswith('+') for line in git(root, 'cherry', pr['head']['sha'], tip).splitlines())


def plan(root, merged):
    """(지울 브랜치, [(남길 브랜치, 이유)]). 끝 커밋이 병합 PR head에 포함된 브랜치만 지운다."""
    prs = {}
    for pr in merged:
        prs.setdefault(pr['head']['ref'], []).append(pr)
    delete, keep = [], []
    for branch in git(root, 'for-each-ref', '--format=%(refname:short)', 'refs/heads').splitlines():
        if branch in KEEP:
            continue
        tip, candidates = git(root, 'rev-parse', branch), prs.get(branch, [])
        if any(pr['head']['sha'] == tip for pr in candidates) or any(contains_tip(root, tip, pr) for pr in candidates):
            delete.append(branch)
        elif candidates:
            keep.append((branch, '병합된 PR 이후의 커밋이 있습니다'))
        else:
            keep.append((branch, '병합된 PR이 없습니다'))
    return delete, keep


def has_ref(root, ref):
    return subprocess.run(['git', 'rev-parse', '--verify', '--quiet', ref], cwd=root, capture_output=True).returncode == 0


def forget(root, branch):
    """지운 브랜치의 PR 초안과 승인 컨텍스트를 함께 지운다."""
    draft_path(root, branch).unlink(missing_ok=True)
    context = context_path(root)
    if context.is_file() and json.loads(context.read_text()).get('branch') == branch:
        context.unlink()


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run', action='store_true', help='지울 브랜치만 출력하고 아무것도 바꾸지 않는다')
    args = parser.parse_args(argv)
    repo, _ = load_config(root)
    git(root, 'fetch', '--prune', 'origin')
    current = git(root, 'branch', '--show-current')
    dirty = bool(git(root, 'status', '--porcelain'))
    delete, keep = plan(root, merged_prs(root, repo))
    if current in delete and dirty:
        delete.remove(current)
        keep.append((current, '현재 브랜치에 커밋하지 않은 변경이 있습니다'))
    for branch in delete:
        print(f'삭제: {branch}' + (' (현재 브랜치; develop으로 전환 후)' if branch == current else ''))
    for branch, reason in keep:
        print(f'유지: {branch} — {reason}')
    if args.dry_run:
        print('dry-run: 전환·최신화·삭제 생략')
        return 0
    if current in delete:
        git(root, 'switch', 'develop')
        current = 'develop'
    if current == 'develop' and not dirty:
        git(root, 'pull', '--ff-only', 'origin', 'develop')
        print('develop 최신화 완료')
    else:
        print('develop이 아닌 브랜치나 변경이 있는 상태라 develop 최신화를 건너뜁니다')
    for branch in delete:
        git(root, 'branch', '-D', branch)
        forget(root, branch)
        if has_ref(root, f'refs/remotes/origin/{branch}'):
            print(f'원격 origin/{branch}가 남아 있습니다; GitHub PR 페이지의 Delete branch로 지우세요')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)

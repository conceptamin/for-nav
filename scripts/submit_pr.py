#!/usr/bin/env python3
"""사람이 실행하는 PR 제출 도우미. 현재 작업 브랜치를 검사·push하고 develop 대상 PR을 만든다.

AI는 이 스크립트를 실행하지 않는다. AI는 PR 본문 초안을 draft_path() 위치에 작성한다.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from git_flow import ROOT, git, run  # noqa: E402

# 브랜치 접두사 → PR 템플릿. 모두 develop 대상이며 release·hotfix는 사람이 직접 처리한다.
TEMPLATES = {'backlog/': 'backlog.md', 'feature/': 'implementation.md', 'policy/': 'policy.md'}
BASE = 'develop'


def template_for(branch):
    for prefix, name in TEMPLATES.items():
        if branch.startswith(prefix):
            return name
    raise ValueError(f'{branch}: backlog/·feature/·policy/ 브랜치만 이 스크립트로 제출합니다')


def draft_path(root, branch):
    return Path(git(root, 'rev-parse', '--absolute-git-dir')) / 'yardpilot-pr' / f"{branch.replace('/', '__')}.md"


def split_title(text):
    """초안 첫 줄이 '# 제목'이면 PR 제목으로 쓰고 본문에서 뗀다."""
    first, _, rest = text.partition('\n')
    if first.startswith('# '):
        return first[2:].strip(), rest.lstrip('\n')
    return None, text


def plan(root, branch, *, title=None, body_file=None):
    template = template_for(branch)
    if git(root, 'status', '--porcelain'):
        raise ValueError('깨끗한 작업 트리 필요; 커밋하지 않은 변경이 있습니다')
    subjects = git(root, 'log', '--reverse', '--format=%s', f'origin/{BASE}..HEAD').splitlines()
    if not subjects:
        raise ValueError(f'origin/{BASE}보다 앞선 커밋이 없습니다')
    draft = draft_path(root, branch)
    if body_file:
        source = Path(body_file)
    elif draft.is_file():
        source = draft
    else:
        source = root / '.github/PULL_REQUEST_TEMPLATE' / template
    draft_title, body = split_title(source.read_text())
    return dict(branch=branch, base=BASE, template=template, source=str(source), body=body,
                title=title or draft_title or subjects[0], placeholder=source.name == template)


def precheck(root, branch):
    if branch.startswith('backlog/'):
        run(root, sys.executable, 'scripts/harness.py', 'check')
    elif branch.startswith('feature/'):
        run(root, sys.executable, 'scripts/git_flow.py', 'check-context')
    elif branch.startswith('policy/'):
        approver = json.loads((root / '.github/git-flow.json').read_text()).get('approver') or ''
        login = run(root, 'gh', 'api', 'user', '--jq', '.login')
        if login.lower() != approver.lower():
            raise ValueError(f'정책 PR은 approver({approver})가 제출해야 합니다; 현재 gh 계정은 {login}')


def open_pr_url(root, branch):
    return run(root, 'gh', 'pr', 'list', '--head', branch, '--state', 'open', '--json', 'url', '--jq', '.[0].url')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--title', help='PR 제목 (기본: 초안 첫 줄의 "# 제목", 없으면 첫 커밋 제목)')
    parser.add_argument('--body-file', help='PR 본문 파일 (기본: AI 초안, 없으면 로컬 템플릿)')
    parser.add_argument('--dry-run', action='store_true', help='검사와 제출 계획만 출력하고 push·PR 생성은 하지 않는다')
    args = parser.parse_args(argv)
    root = ROOT
    branch = git(root, 'branch', '--show-current')
    git(root, 'fetch', '--quiet', 'origin', BASE)
    info = plan(root, branch, title=args.title, body_file=args.body_file)
    precheck(root, branch)
    existing = open_pr_url(root, branch)
    print(f"브랜치: {branch} → {BASE}\n제목: {info['title']}\n본문: {info['source']}")
    if info['placeholder']:
        print('주의: AI 초안이 없어 빈 템플릿으로 제출합니다. 웹에서 본문을 채우세요.')
    if existing:
        print(f'열린 PR이 이미 있어 push만 합니다: {existing}')
    if args.dry_run:
        print('dry-run: push·PR 생성 생략')
        return 0
    # pre-push 훅을 그대로 거친다. 훅 우회 옵션은 쓰지 않는다.
    run(root, 'git', 'push', '--set-upstream', 'origin', branch)
    if existing:
        return 0
    body = Path(git(root, 'rev-parse', '--absolute-git-dir')) / 'yardpilot-pr-body.tmp'
    body.write_text(info['body'])
    try:
        print(run(root, 'gh', 'pr', 'create', '--base', BASE, '--head', branch,
                  '--title', info['title'], '--body-file', str(body)))
    finally:
        body.unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)

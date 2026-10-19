#!/usr/bin/env python3
"""Approved phase backlog gate. Requires Git and authenticated read-only gh access."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(root, *args):
    result = subprocess.run(args, cwd=root, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or f'{args[0]} failed')
    return result.stdout.strip()


def git(root, *args):
    return run(root, 'git', *args)


def api(root, repo, endpoint):
    return json.loads(run(root, 'gh', 'api', f'repos/{repo}/{endpoint}'))


def pages(root, repo, endpoint):
    result = []
    for page in range(1, 101):
        batch = api(root, repo, f'{endpoint}?per_page=100&page={page}')
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise ValueError('API pagination limit exceeded')


def validate(root, context, *, clean_document=False):
    config = json.loads((root / '.github/git-flow.json').read_text())
    repo, approver = config.get('repository'), config.get('approver')
    if not repo or not approver or not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
        raise ValueError('repository와 approver 설정 필요; 승인 없이 시작할 수 없습니다')
    path = context['backlog']
    match = re.fullmatch(r'backlog/(frontend|backend|modeling)/(phase-\d+)\.md', path)
    if not match:
        raise ValueError('영역별 phase Markdown 경로가 필요합니다')
    pr = api(root, repo, f"pulls/{int(context['approval_pr'])}")
    if not pr.get('merged_at') or pr['base']['ref'] != 'develop' or pr['base']['repo']['full_name'] != repo:
        raise ValueError('develop에 병합된 백로그 PR이 필요합니다')
    reviews = pages(root, repo, f"pulls/{pr['number']}/reviews")
    decisions = [r for r in reviews if r['user']['login'].lower() == approver.lower()
                 and r['state'] in ('APPROVED', 'CHANGES_REQUESTED', 'DISMISSED')]
    latest = max(decisions, key=lambda r: r['id']) if decisions else None
    if not latest or latest['state'] != 'APPROVED' or latest['commit_id'] != pr['head']['sha']:
        raise ValueError('지정 승인자의 최신 head 승인 필요')
    files = pages(root, repo, f"pulls/{pr['number']}/files")
    if not any(f['filename'] == path and f['status'] != 'removed' for f in files):
        raise ValueError('승인 PR에 해당 백로그 문서가 없습니다')
    if any(not re.fullmatch(r'backlog/(frontend|backend|modeling)/phase-\d+\.md', f['filename']) for f in files):
        raise ValueError('백로그 승인 PR에는 phase 문서만 포함할 수 있습니다')
    sha = pr['merge_commit_sha']
    if context.get('revision', sha) != sha:
        raise ValueError('승인 revision 불일치')
    comment = api(root, repo, f"issues/comments/{int(context['request_comment'])}")
    if (comment['issue_url'] != f'https://api.github.com/repos/{repo}/issues/{pr["number"]}'
            or comment['user']['type'] != 'User'
            or comment.get('author_association') not in ('OWNER', 'MEMBER', 'COLLABORATOR')
            or comment['created_at'] <= pr['merged_at']
            or comment['body'].strip() != f'implement {path} {sha}'):
        raise ValueError('병합 후 저장소 참여자가 남긴 정확한 implement 요청 댓글 필요')
    remote = git(root, 'remote', 'get-url', 'origin')
    if remote not in (f'https://github.com/{repo}.git', f'https://github.com/{repo}', f'git@github.com:{repo}.git'):
        raise ValueError('origin과 설정 repository 불일치')
    git(root, 'fetch', 'origin', 'develop')
    git(root, 'fetch', 'origin', f'refs/pull/{pr["number"]}/head')
    approved = git(root, 'rev-parse', f'{sha}:{path}')
    current = git(root, 'rev-parse', f'origin/develop:{path}')
    head_blob = git(root, 'rev-parse', f"{pr['head']['sha']}:{path}")
    if approved != current or approved != head_blob:
        raise ValueError('승인 문서가 변경되었습니다; 백로그 재승인 필요')
    if clean_document and git(root, 'hash-object', path) != approved:
        raise ValueError('로컬 백로그가 승인 문서와 다릅니다')
    return dict(context, revision=sha, repository=repo, approved_blob=approved)


def context_path(root):
    return Path(git(root, 'rev-parse', '--absolute-git-dir')) / 'yardpilot-approval.json'


def check_context(root):
    context = json.loads(context_path(root).read_text())
    if git(root, 'branch', '--show-current') != context['branch']:
        raise ValueError('승인된 작업 브랜치에서만 구현 가능합니다')
    return validate(root, context)


def check_message(message, context):
    expected = {'Backlog': context['backlog'], 'Backlog-PR': f"https://github.com/{context['repository']}/pull/{context['approval_pr']}",
                'Backlog-Revision': context['revision']}
    for key, value in expected.items():
        matches = re.findall(rf'^{key}: (.+)$', message, re.MULTILINE)
        if matches != [value]:
            raise ValueError(f'{key}: {value} trailer를 정확히 한 번 기록해야 합니다')


def check_push(data):
    for line in data.splitlines():
        local_ref, local_sha, remote_ref, remote_sha = line.split()
        if remote_ref in ('refs/heads/main', 'refs/heads/develop') or remote_ref.startswith('refs/tags/'):
            raise ValueError('보호 브랜치·태그 직접 push 금지; 사람이 PR/릴리스를 처리합니다')
        if set(local_sha) == {'0'}:
            raise ValueError('브랜치 삭제는 사람이 병합 확인 후 처리합니다')



def check_pr(root):
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    pr = event['pull_request']
    repo = event['repository']['full_name']
    branch, base = pr['head']['ref'], pr['base']['ref']
    files = pages(root, repo, f"pulls/{pr['number']}/files")
    if branch.startswith('backlog/') and base == 'develop':
        if not files or any(not re.fullmatch(r'backlog/(frontend|backend|modeling)/phase-\d+\.md', f['filename']) for f in files):
            raise ValueError('백로그 PR에는 phase 문서만 허용합니다')
        return
    if branch.startswith('release/') and base in ('main', 'develop'):
        return  # Human release management; protected-branch review is required.
    if base != 'develop' or not branch.startswith('feature/'):
        raise ValueError('구현 PR은 feature → develop만 허용합니다; hotfix는 별도 승인 절차 필요')
    body = pr.get('body') or ''
    def field(name):
        values = re.findall(rf'^{name}: (.+)$', body, re.MULTILINE)
        if len(values) != 1:
            raise ValueError(f'PR 본문의 {name} 필드 필요')
        return values[0].strip()
    context = validate(root, dict(backlog=field('Backlog'), approval_pr=int(field('Approval-PR')),
                                  request_comment=int(field('Request-Comment')), revision=field('Backlog-Revision')))
    _, lane, filename = context['backlog'].split('/')
    if not re.fullmatch(rf'feature/{lane}/{Path(filename).stem}-[a-z0-9]+(?:-[a-z0-9]+)*', branch):
        raise ValueError('브랜치와 백로그 영역/phase 불일치')
    commits = pages(root, repo, f"pulls/{pr['number']}/commits")
    if len(commits) != pr['commits']:
        raise ValueError('전체 PR 커밋을 확인할 수 없습니다')
    for commit in commits:
        check_message(commit['commit']['message'], context)


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    start = sub.add_parser('start')
    start.add_argument('--backlog', required=True)
    start.add_argument('--approval-pr', required=True, type=int)
    start.add_argument('--request-comment', required=True, type=int)
    start.add_argument('--slug', required=True)
    sub.add_parser('check-context')
    msg = sub.add_parser('commit-msg')
    msg.add_argument('file')
    sub.add_parser('pre-push')
    sub.add_parser('check-pr')
    args = parser.parse_args(argv)
    if args.action == 'check-pr':
        check_pr(root)
    elif args.action == 'pre-push':
        check_push(sys.stdin.read())
    elif args.action == 'start':
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', args.slug):
            raise ValueError('slug는 소문자·숫자·하이픈만 허용합니다')
        if git(root, 'status', '--porcelain'):
            raise ValueError('깨끗한 작업 트리 필요')
        context = validate(root, dict(backlog=args.backlog, approval_pr=args.approval_pr,
                                     request_comment=args.request_comment), clean_document=True)
        _, lane, filename = args.backlog.split('/')
        context['branch'] = f'feature/{lane}/{Path(filename).stem}-{args.slug}'
        git(root, 'switch', '-c', context['branch'], 'origin/develop')
        context_path(root).write_text(json.dumps(context, indent=2) + '\n')
        print(context['branch'])
    elif args.action == 'check-context':
        check_context(root)
        print('PASS: 승인 PR·사람 요청·작업 브랜치 확인')
    else:
        branch = git(root, 'branch', '--show-current')
        if branch in ('main', 'develop'):
            raise ValueError(f'{branch} 직접 커밋 금지; 작업 브랜치에서 PR로 병합합니다')
        if branch.startswith('backlog/'):
            staged = git(root, 'diff', '--cached', '--name-only').splitlines()
            if not staged or any(not re.fullmatch(r'backlog/(frontend|backend|modeling)/phase-\d+\.md', p) for p in staged):
                raise ValueError('backlog 브랜치는 phase 문서만 커밋 가능합니다')
        else:
            check_message(Path(args.file).read_text(), check_context(root))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)

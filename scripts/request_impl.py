#!/usr/bin/env python3
"""사람이 실행하는 구현 요청 도우미. 병합된 백로그 PR을 찾아 `implement <문서> <병합 SHA>` 댓글을 단다.

AI는 이 스크립트를 실행하지 않는다(--dry-run 제외). 댓글은 실행한 사람의 gh 계정으로 남으며 구현 요청의 감사 기록이다.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from git_flow import (ROOT, approved_pr, check_documents, find_request, latest_backlog_pr,  # noqa: E402
                      load_config, run, validate)


def prepare(root, path, number=None):
    """댓글을 달기 전에 승인·문서 상태를 start와 같은 기준으로 확인한다."""
    repo, approver = load_config(root)
    number = number or latest_backlog_pr(root, repo, path)
    pr = approved_pr(root, repo, approver, path, number)
    check_documents(root, repo, pr, path)
    return repo, pr, f"implement {path} {pr['merge_commit_sha']}"


def post(root, repo, pr, body):
    return run(root, 'gh', 'api', '-X', 'POST', f"repos/{repo}/issues/{pr['number']}/comments",
               '-f', f'body={body}', '--jq', '.id')


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('backlog', help='backlog/<영역>/phase-XX.md')
    parser.add_argument('--pr', type=int, help='승인 PR 번호 (기본: 이 문서를 담아 가장 최근 병합된 백로그 PR)')
    parser.add_argument('--dry-run', action='store_true', help='검사와 남길 댓글만 출력하고 댓글은 달지 않는다')
    args = parser.parse_args(argv)
    repo, pr, body = prepare(root, args.backlog, args.pr)
    print(f"승인 PR: https://github.com/{repo}/pull/{pr['number']}\n댓글: {body}")
    existing = find_request(root, repo, pr, args.backlog)
    if existing:
        print(f'이미 구현 요청 댓글이 있습니다(ID {existing}); 새로 달지 않습니다')
    elif args.dry_run:
        print('dry-run: 댓글 생략')
        return 0
    else:
        existing = int(post(root, repo, pr, body))
        # 방금 단 댓글이 start 검증을 통과하는지 확인한다(예: 저장소 참여자가 아닌 계정).
        try:
            validate(root, dict(backlog=args.backlog, approval_pr=pr['number'], request_comment=existing))
        except ValueError as error:
            raise ValueError(f'댓글(ID {existing})이 구현 요청으로 인정되지 않습니다: {error}') from error
        print(f'구현 요청 댓글을 남겼습니다(ID {existing})')
    print(f'이제 AI에게 "{args.backlog} 구현해줘"라고 요청하세요.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)

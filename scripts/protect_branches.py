#!/usr/bin/env python3
"""GitHub ruleset that blocks direct pushes and ungated merges to main/develop.

plan prints the ruleset, check reads the remote state, apply is run by the repository owner only.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NAME = 'yardpilot-protected-branches'
BRANCHES = ('main', 'develop')
CHECKS = ('approval-gate', 'harness')  # Job names in .github/workflows/git-flow.yml and harness.yml.
GITHUB_ACTIONS = 15368  # Only GitHub Actions check runs satisfy the gate; commit statuses cannot spoof it.


def ruleset(approvals):
    return {
        'name': NAME,
        'target': 'branch',
        'enforcement': 'active',
        'bypass_actors': [],  # No admin, team, or app bypass.
        'conditions': {'ref_name': {'include': [f'refs/heads/{b}' for b in BRANCHES], 'exclude': []}},
        'rules': [
            {'type': 'deletion'},
            {'type': 'non_fast_forward'},
            {'type': 'pull_request', 'parameters': {
                'required_approving_review_count': approvals,
                'dismiss_stale_reviews_on_push': True,
                'require_code_owner_review': True,
                'require_last_push_approval': approvals > 0,
                'required_review_thread_resolution': True}},
            {'type': 'required_status_checks', 'parameters': {
                'strict_required_status_checks_policy': True,
                'required_status_checks': [{'context': c, 'integration_id': GITHUB_ACTIONS} for c in CHECKS]}},
        ],
    }


def gh(root, *args, payload=None):
    result = subprocess.run(['gh', 'api', *args], cwd=root, text=True, capture_output=True,
                            input=None if payload is None else json.dumps(payload))
    if result.returncode:
        raise ValueError(result.stderr.strip() or 'gh api failed')
    return json.loads(result.stdout or 'null')


def repository(root, override):
    repo = override or json.loads((root / '.github/git-flow.json').read_text()).get('repository')
    if not repo or not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
        raise ValueError('--repo owner/name 또는 .github/git-flow.json repository 설정 필요')
    return repo


def existing(root, repo):
    matches = [r for r in gh(root, f'repos/{repo}/rulesets?per_page=100&includes_parents=false') if r['name'] == NAME]
    if len(matches) > 1:
        raise ValueError(f'{NAME} 룰셋이 여러 개입니다; GitHub 설정에서 하나만 남기세요')
    return gh(root, f"repos/{repo}/rulesets/{matches[0]['id']}") if matches else None


def contains(actual, desired):
    if isinstance(desired, dict):
        return isinstance(actual, dict) and all(k in actual and contains(actual[k], v) for k, v in desired.items())
    if isinstance(desired, list):
        return isinstance(actual, list) and all(any(contains(a, d) for a in actual) for d in desired)
    return actual == desired


def problems(actual, desired):
    if actual is None:
        return [f'{NAME} 룰셋이 없습니다; 소유자가 apply를 실행해야 합니다']
    found = []
    if 'bypass_actors' not in actual:
        found.append('bypass_actors를 읽을 수 없습니다; 관리자 권한으로 확인하세요')
    elif actual['bypass_actors']:
        found.append(f"우회 권한이 있습니다: {actual['bypass_actors']}")
    for key in ('target', 'enforcement', 'conditions'):
        if not contains(actual.get(key), desired[key]):
            found.append(f'{key} 불일치: {actual.get(key)}')
    for rule in desired['rules']:
        if not contains(actual.get('rules', []), [rule]):
            found.append(f"{rule['type']} 규칙 누락 또는 불일치")
    return found


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'check', 'apply'))
    parser.add_argument('--repo', help='owner/name; 기본값은 .github/git-flow.json repository')
    parser.add_argument('--approvals', type=int, default=1,
                        help='필수 승인 수 (기본 1). PR 작성자는 자기 PR을 승인할 수 없습니다')
    args = parser.parse_args(argv)
    if args.approvals < 0:
        raise ValueError('--approvals는 0 이상이어야 합니다')
    desired = ruleset(args.approvals)
    if args.action == 'plan':
        print(json.dumps(desired, indent=2, ensure_ascii=False))
        return 0
    repo = repository(root, args.repo)
    current = existing(root, repo)
    if args.action == 'apply':
        if current:
            gh(root, '-X', 'PUT', f"repos/{repo}/rulesets/{current['id']}", '--input', '-', payload=desired)
        else:
            gh(root, '-X', 'POST', f'repos/{repo}/rulesets', '--input', '-', payload=desired)
        current = existing(root, repo)
    found = problems(current, desired)
    for problem in found:
        print(f'FAIL: {problem}', file=sys.stderr)
    if found:
        return 1
    print(f"PASS: {repo} {', '.join(BRANCHES)} 직접 push·삭제·force push 차단, PR·승인 {args.approvals}·{', '.join(CHECKS)} 필수")
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)

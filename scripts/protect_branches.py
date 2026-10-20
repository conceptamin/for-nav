#!/usr/bin/env python3
"""GitHub rulesets that block direct pushes and ungated merges to main/develop and fix each branch's merge method.

plan prints the rulesets, check reads the remote state, apply is run by the repository owner only.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# 브랜치별 허용 병합 방식. develop은 PR 하나가 커밋 하나가 되도록 squash만, main은 release 이력을 develop과
# 잇도록 merge commit만 허용한다(main을 squash하면 다음 release에서 이력이 갈라져 충돌한다).
MERGE_METHODS = {'develop': 'squash', 'main': 'merge'}
LEGACY = 'yardpilot-protected-branches'  # 병합 방식을 고정하지 않던 main/develop 공용 룰셋. apply가 교체한다.
CHECKS = ('approval-gate', 'harness')  # Job names in .github/workflows/git-flow.yml and harness.yml.
GITHUB_ACTIONS = 15368  # Only GitHub Actions check runs satisfy the gate; commit statuses cannot spoof it.


def name(branch):
    return f'yardpilot-protected-{branch}'


def ruleset(branch, approvals):
    return {
        'name': name(branch),
        'target': 'branch',
        'enforcement': 'active',
        'bypass_actors': [],  # No admin, team, or app bypass.
        'conditions': {'ref_name': {'include': [f'refs/heads/{branch}'], 'exclude': []}},
        'rules': [
            {'type': 'deletion'},
            {'type': 'non_fast_forward'},
            {'type': 'pull_request', 'parameters': {
                'required_approving_review_count': approvals,
                'dismiss_stale_reviews_on_push': True,
                'require_code_owner_review': True,
                'require_last_push_approval': approvals > 0,
                'required_review_thread_resolution': True,
                'allowed_merge_methods': [MERGE_METHODS[branch]]}},
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
    """관리 대상 이름의 룰셋 {이름: 상세}. 같은 이름이 여러 개면 실패한다."""
    names = {LEGACY, *map(name, MERGE_METHODS)}
    found = {}
    for summary in gh(root, f'repos/{repo}/rulesets?per_page=100&includes_parents=false'):
        if summary['name'] in names:
            if summary['name'] in found:
                raise ValueError(f"{summary['name']} 룰셋이 여러 개입니다; GitHub 설정에서 하나만 남기세요")
            found[summary['name']] = gh(root, f"repos/{repo}/rulesets/{summary['id']}")
    return found


def contains(actual, desired):
    if isinstance(desired, dict):
        return isinstance(actual, dict) and all(k in actual and contains(actual[k], v) for k, v in desired.items())
    if isinstance(desired, list):
        return isinstance(actual, list) and all(any(contains(a, d) for a in actual) for d in desired)
    return actual == desired


def problems(actual, desired):
    if actual is None:
        return ['룰셋이 없습니다; 소유자가 apply를 실행해야 합니다']
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
    # 목록 포함 비교로는 서버 기본값(merge·squash·rebase 모두 허용)도 통과하므로 병합 방식은 정확히 비교한다.
    pull = next((r for r in actual.get('rules', []) if r.get('type') == 'pull_request'), {})
    methods = sorted((pull.get('parameters') or {}).get('allowed_merge_methods') or [])
    want = next(r for r in desired['rules'] if r['type'] == 'pull_request')['parameters']['allowed_merge_methods']
    if methods != want:
        found.append(f'병합 방식 불일치: {methods} (기대 {want})')
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
    if args.action == 'plan':
        print(json.dumps([ruleset(b, args.approvals) for b in MERGE_METHODS], indent=2, ensure_ascii=False))
        return 0
    repo = repository(root, args.repo)
    current = existing(root, repo)
    if args.action == 'apply':
        for branch in MERGE_METHODS:
            desired = ruleset(branch, args.approvals)
            if desired['name'] in current:
                gh(root, '-X', 'PUT', f"repos/{repo}/rulesets/{current[desired['name']]['id']}", '--input', '-', payload=desired)
            else:
                gh(root, '-X', 'POST', f'repos/{repo}/rulesets', '--input', '-', payload=desired)
        # 새 룰셋이 생긴 뒤에 구 룰셋을 지워 보호가 비는 순간이 없게 한다.
        if LEGACY in current:
            gh(root, '-X', 'DELETE', f"repos/{repo}/rulesets/{current[LEGACY]['id']}")
        current = existing(root, repo)
    found = []
    for branch in MERGE_METHODS:
        desired = ruleset(branch, args.approvals)
        found += [f"{desired['name']}: {p}" for p in problems(current.get(desired['name']), desired)]
    if LEGACY in current:
        found.append(f'{LEGACY} 구 룰셋이 남아 있습니다; 소유자가 apply로 교체해야 합니다')
    for problem in found:
        print(f'FAIL: {problem}', file=sys.stderr)
    if found:
        return 1
    methods = ', '.join(f'{b} {m}' for b, m in MERGE_METHODS.items())
    print(f"PASS: {repo} main·develop 직접 push·삭제·force push 차단, PR·승인 {args.approvals}·{', '.join(CHECKS)} 필수, 병합 방식 {methods}")
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)

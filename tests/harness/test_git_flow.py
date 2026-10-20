import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('git_flow', Path(__file__).resolve().parents[2] / 'scripts/git_flow.py')
flow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flow)


class ApprovalGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '.github').mkdir()
        (self.root / '.github/git-flow.json').write_text(json.dumps(dict(repository='org/repo', approver='owner')))
        self.context = dict(backlog='backlog/backend/phase-01.md', approval_pr=42, request_comment=9)
        self.pr = dict(number=42, merged_at='2026-10-18T01:00:00Z', merge_commit_sha='a' * 40,
                       base=dict(ref='develop', repo=dict(full_name='org/repo')), head=dict(sha='b' * 40))
        self.review = dict(id=1, user=dict(login='owner'), state='APPROVED', commit_id='b' * 40)
        self.comment = dict(issue_url='https://api.github.com/repos/org/repo/issues/42', user=dict(type='User'),
                            author_association='COLLABORATOR', created_at='2026-10-18T02:00:00Z',
                            body=f"implement {self.context['backlog']} {'a' * 40}")
        self.files = [dict(filename=self.context['backlog'], status='added')]
        self.reviews = [self.review]
        self.listing = [dict(number=42, merged_at=self.pr['merged_at'], head=dict(ref='backlog/backend/phase-01', sha='b' * 40))]
        self.comments = [dict(self.comment, id=9)]
        self.files_by = {}
        self.addCleanup(patch.stopall)
        patch.object(flow, 'api', side_effect=lambda root, repo, endpoint: self.pr if endpoint == 'pulls/42' else self.comment).start()
        patch.object(flow, 'pages', side_effect=self.fake_pages).start()
        self.git = patch.object(flow, 'git', side_effect=lambda root, *args: 'https://github.com/org/repo.git' if args[0] == 'remote' else 'blob').start()

    def fake_pages(self, root, repo, endpoint):
        if endpoint.endswith('reviews'):
            return self.reviews
        if endpoint.startswith('pulls?'):
            return self.listing
        if endpoint.endswith('/comments'):
            return self.comments
        return self.files_by.get(int(endpoint.split('/')[1]), self.files)

    def validate(self):
        return flow.validate(self.root, self.context, clean_document=True)

    def start_git(self):
        state = self.root / 'git-state'
        state.mkdir(exist_ok=True)
        def git(root, *args):
            if args[0] == 'status':
                return ''
            if args[:2] == ('rev-parse', '--absolute-git-dir'):
                return str(state)
            if args[0] == 'remote':
                return 'https://github.com/org/repo.git'
            return 'blob'
        self.git.side_effect = git
        return state

    def test_approved_and_requested(self):
        self.assertEqual(self.validate()['revision'], 'a' * 40)

    def test_unconfigured_fails_closed(self):
        (self.root / '.github/git-flow.json').write_text('{"repository": null, "approver": null}')
        with self.assertRaises(ValueError):
            self.validate()

    def test_unmerged_wrong_base_or_approver_rejected(self):
        for key, value in [('merged_at', None), ('base', dict(ref='main', repo=dict(full_name='org/repo')))]:
            old = self.pr[key]
            self.pr[key] = value
            with self.assertRaises(ValueError):
                self.validate()
            self.pr[key] = old
        self.review['user']['login'] = 'someone-else'
        with self.assertRaises(ValueError):
            self.validate()

    def test_stale_or_dismissed_approval(self):
        self.review['commit_id'] = 'old'
        with self.assertRaises(ValueError):
            self.validate()
        self.review['commit_id'] = 'b' * 40
        self.reviews.append(dict(self.review, id=2, state='DISMISSED'))
        with self.assertRaises(ValueError):
            self.validate()

    def test_merge_by_approver_counts_as_approval(self):
        self.reviews.clear()
        self.pr['merged_by'] = dict(login='Owner')
        self.assertEqual(self.validate()['revision'], 'a' * 40)
        for merged_by in (dict(login='someone-else'), None):
            self.pr['merged_by'] = merged_by
            with self.assertRaisesRegex(ValueError, '직접 병합 필요'):
                self.validate()

    def test_ssh_alias_origin_must_resolve_to_github(self):
        self.git.side_effect = lambda root, *args: 'git@gh-alias:org/repo.git' if args[0] == 'remote' else 'blob'
        with patch.object(flow, 'run', return_value='user git\nhostname github.com\nport 22') as ssh:
            self.validate()
        ssh.assert_called_once_with(self.root, 'ssh', '-G', 'gh-alias')
        for remote, config in [('git@gh-alias:org/repo.git', 'hostname evil.example'),
                               ('git@gh-alias:other/repo.git', 'hostname github.com'),
                               ('git@-oProxyCommand=x:org/repo.git', 'hostname github.com')]:
            self.git.side_effect = lambda root, *args, remote=remote: remote if args[0] == 'remote' else 'blob'
            with patch.object(flow, 'run', return_value=config), self.assertRaisesRegex(ValueError, 'origin', msg=remote):
                self.validate()

    def test_request_must_be_human_member_after_merge_and_exact(self):
        for key, value in [('user', dict(type='Bot')), ('author_association', 'NONE'),
                           ('created_at', '2026-10-18T00:00:00Z'), ('body', 'please implement'),
                           ('issue_url', 'https://api.github.com/repos/org/repo/issues/99')]:
            old = self.comment[key]
            self.comment[key] = value
            with self.assertRaises(ValueError, msg=key):
                self.validate()
            self.comment[key] = old

    def test_scope_and_document_revision_changes_rejected(self):
        self.files.append(dict(filename='backend/app.py', status='added'))
        with self.assertRaises(ValueError):
            self.validate()
        self.files.pop()
        self.git.side_effect = lambda root, *args: ('https://github.com/org/repo.git' if args[0] == 'remote'
                                                  else 'changed' if args[-1].startswith('origin/develop:') else 'blob')
        with self.assertRaises(ValueError):
            self.validate()

    def test_start_failure_does_not_create_branch(self):
        self.git.side_effect = lambda root, *args: '' if args[0] == 'status' else 'blob'
        self.pr['merged_at'] = None
        with self.assertRaises(ValueError):
            flow.main(['start', '--backlog', self.context['backlog'], '--approval-pr', '42',
                       '--request-comment', '9', '--slug', 'auth'], self.root)
        self.assertFalse(any(call.args[1] == 'switch' for call in self.git.call_args_list))

    def test_start_creates_branch_only_after_validation(self):
        state = self.root / 'git-state'
        state.mkdir()
        def git(root, *args):
            if args[0] == 'status':
                return ''
            if args[:2] == ('rev-parse', '--absolute-git-dir'):
                return str(state)
            if args[0] == 'remote':
                return 'https://github.com/org/repo.git'
            return 'blob'
        self.git.side_effect = git
        flow.main(['start', '--backlog', self.context['backlog'], '--approval-pr', '42',
                   '--request-comment', '9', '--slug', 'auth'], self.root)
        context = json.loads((state / 'yardpilot-approval.json').read_text())
        self.assertEqual(context['branch'], 'feature/backend/phase-01-auth')
        self.git.assert_any_call(self.root, 'switch', '-c', context['branch'], 'origin/develop')

    def test_start_discovers_pr_and_request_comment(self):
        state = self.start_git()
        flow.main(['start', '--backlog', self.context['backlog'], '--slug', 'auth'], self.root)
        context = json.loads((state / 'yardpilot-approval.json').read_text())
        self.assertEqual((context['approval_pr'], context['request_comment']), (42, 9))
        self.git.assert_any_call(self.root, 'switch', '-c', 'feature/backend/phase-01-auth', 'origin/develop')

    def test_discovery_picks_latest_merged_backlog_pr_with_document(self):
        self.listing[:] = [dict(number=40, merged_at='2026-10-17T00:00:00Z', head=dict(ref='backlog/backend/phase-01')),
                           dict(number=42, merged_at='2026-10-18T01:00:00Z', head=dict(ref='backlog/backend/phase-01')),
                           dict(number=43, merged_at='2026-10-19T00:00:00Z', head=dict(ref='backlog/backend/phase-02')),
                           dict(number=44, merged_at='2026-10-20T00:00:00Z', head=dict(ref='feature/backend/phase-01-a'))]
        self.files_by[43] = [dict(filename='backlog/backend/phase-02.md', status='added')]
        self.assertEqual(flow.latest_backlog_pr(self.root, 'org/repo', self.context['backlog']), 42)
        self.listing.pop(1)
        self.assertEqual(flow.latest_backlog_pr(self.root, 'org/repo', self.context['backlog']), 40)
        self.listing.clear()
        with self.assertRaisesRegex(ValueError, '병합된 백로그 PR이 없습니다'):
            flow.latest_backlog_pr(self.root, 'org/repo', self.context['backlog'])

    def test_discovery_ignores_invalid_comments_and_start_blocks_without_request(self):
        self.comments[:] = [dict(self.comment, id=5, created_at='2026-10-18T00:00:00Z'),
                            dict(self.comment, id=6, user=dict(type='Bot')),
                            dict(self.comment, id=7, body='implement please'),
                            dict(self.comment, id=8, author_association='NONE')]
        self.start_git()
        with self.assertRaisesRegex(ValueError, 'request_impl.py'):
            flow.main(['start', '--backlog', self.context['backlog'], '--slug', 'auth'], self.root)
        self.assertFalse(any(call.args[1] == 'switch' for call in self.git.call_args_list))
        self.comments.extend([dict(self.comment, id=11), dict(self.comment, id=10)])
        self.assertEqual(flow.discover(self.root, self.context['backlog']), (42, 11))

    def test_discovered_ids_still_pass_full_gate(self):
        # 탐색은 조회일 뿐이므로 승인 조건이 깨지면 start가 브랜치를 만들지 않는다.
        self.start_git()
        self.review['commit_id'] = 'old'
        with self.assertRaisesRegex(ValueError, '최신 head 승인'):
            flow.main(['start', '--backlog', self.context['backlog'], '--slug', 'auth'], self.root)
        self.assertFalse(any(call.args[1] == 'switch' for call in self.git.call_args_list))

    def test_backlog_ci_rejects_product_code(self):
        event = self.root / 'event.json'
        event.write_text(json.dumps(dict(repository=dict(full_name='org/repo'),
                                         pull_request=dict(number=42, head=dict(ref='backlog/backend/phase-01'),
                                                           base=dict(ref='develop')))))
        with patch.dict(flow.os.environ, GITHUB_EVENT_PATH=str(event)):
            flow.check_pr(self.root)
            self.files.append(dict(filename='backend/app.py', status='added'))
            with self.assertRaises(ValueError):
                flow.check_pr(self.root)

    def check_policy_pr(self, branch='policy/solo-approval', author='Owner', base='develop'):
        event = self.root / 'event.json'
        event.write_text(json.dumps(dict(repository=dict(full_name='org/repo'),
                                         pull_request=dict(number=42, head=dict(ref=branch), base=dict(ref=base),
                                                           user=dict(login=author)))))
        with patch.dict(flow.os.environ, GITHUB_EVENT_PATH=str(event)):
            flow.check_pr(self.root)

    def test_policy_pr_by_approver_with_policy_files_only(self):
        self.files[:] = [dict(filename=name, status='modified') for name in
                         ('scripts/git_flow.py', 'tests/harness/test_git_flow.py', 'docs/GIT-FLOW.md', 'CLAUDE.md',
                          'frontend/AGENTS.md', '.github/workflows/git-flow.yml', '.githooks/commit-msg', '.gitignore')]
        self.check_policy_pr()
        for name in ('frontend/src/main.tsx', 'backlog/frontend/phase-01.md', 'fixtures/run.json',
                     'shipyard-api-contract.md', 'frontend/AGENTS.md.bak'):
            self.files.append(dict(filename=name, status='added'))
            with self.assertRaisesRegex(ValueError, '하네스·운영 규칙 파일만', msg=name):
                self.check_policy_pr()
            self.files.pop()
        self.files.append(dict(filename='docs/main.tsx', status='renamed', previous_filename='frontend/src/main.tsx'))
        with self.assertRaisesRegex(ValueError, '이동할 수 없습니다'):
            self.check_policy_pr()

    def test_policy_pr_requires_approver_author_slug_and_develop(self):
        self.files[:] = [dict(filename='docs/GIT-FLOW.md', status='modified')]
        with self.assertRaisesRegex(ValueError, '지정 승인자가 직접 제출'):
            self.check_policy_pr(author='someone-else')
        with self.assertRaisesRegex(ValueError, 'policy/<slug>'):
            self.check_policy_pr(branch='policy/Bad_Slug')
        with self.assertRaisesRegex(ValueError, 'feature → develop만'):
            self.check_policy_pr(base='main')
        self.files.clear()
        with self.assertRaisesRegex(ValueError, '하네스·운영 규칙 파일만'):
            self.check_policy_pr()

    def test_policy_branch_commit_allows_only_policy_files(self):
        message = self.root / 'MSG'
        message.write_text('정책 변경\n')
        staged = 'docs/GIT-FLOW.md\nscripts/git_flow.py'
        self.git.side_effect = lambda root, *args: 'policy/solo-approval' if args[0] == 'branch' else staged
        self.assertEqual(flow.main(['commit-msg', str(message)], self.root), 0)
        self.git.assert_any_call(self.root, 'diff', '--cached', '--name-only', '--no-renames')
        for staged in ('docs/GIT-FLOW.md\nfrontend/src/main.tsx', ''):
            with self.assertRaisesRegex(ValueError, 'policy 브랜치'):
                flow.main(['commit-msg', str(message)], self.root)

    def test_trailers_match_approved_context(self):
        context = dict(self.context, repository='org/repo', revision='a' * 40)
        message = f"세션 검증 필요\n\nBacklog: {context['backlog']}\nBacklog-PR: https://github.com/org/repo/pull/42\nBacklog-Revision: {context['revision']}\n"
        flow.check_message(message, context)
        for invalid in [message.replace('/42', '/43'), message + f"Backlog: {context['backlog']}\n", 'no trailers']:
            with self.assertRaises(ValueError):
                flow.check_message(invalid, context)

    def test_commit_on_protected_branch_rejected(self):
        message = self.root / 'MSG'
        message.write_text('direct commit\n')
        for branch in ('main', 'develop'):
            self.git.side_effect = lambda root, *args, branch=branch: branch
            with self.assertRaisesRegex(ValueError, '직접 커밋 금지'):
                flow.main(['commit-msg', str(message)], self.root)

    def test_protected_push_and_deletion_rejected(self):
        for ref, sha in [('refs/heads/main', '1' * 40), ('refs/heads/develop', '1' * 40),
                         ('refs/tags/v1', '1' * 40), ('refs/heads/feature/backend/a', '0' * 40)]:
            with self.assertRaises(ValueError):
                flow.check_push(f'HEAD {sha} {ref} {"0" * 40}\n')
        flow.check_push(f'HEAD {"1" * 40} refs/heads/feature/backend/a {"0" * 40}\n')


class PagesTest(unittest.TestCase):
    def test_query_endpoint_gets_paging_parameters(self):
        with patch.object(flow, 'api', return_value=[]) as api:
            flow.pages(None, 'org/repo', 'pulls?state=closed&base=develop')
            flow.pages(None, 'org/repo', 'pulls/1/files')
        self.assertEqual([c.args[2] for c in api.call_args_list],
                         ['pulls?state=closed&base=develop&per_page=100&page=1', 'pulls/1/files?per_page=100&page=1'])


if __name__ == '__main__':
    unittest.main()

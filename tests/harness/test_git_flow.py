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
        self.addCleanup(patch.stopall)
        patch.object(flow, 'api', side_effect=lambda root, repo, endpoint: self.pr if endpoint == 'pulls/42' else self.comment).start()
        patch.object(flow, 'pages', side_effect=lambda root, repo, endpoint: self.reviews if endpoint.endswith('reviews') else self.files).start()
        self.git = patch.object(flow, 'git', side_effect=lambda root, *args: 'https://github.com/org/repo.git' if args[0] == 'remote' else 'blob').start()

    def validate(self):
        return flow.validate(self.root, self.context, clean_document=True)

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


if __name__ == '__main__':
    unittest.main()

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location('submit_pr', SCRIPTS / 'submit_pr.py')
submit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(submit)


class SubmitPrTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.gitdir = self.root / '.git'
        (self.root / '.github/PULL_REQUEST_TEMPLATE').mkdir(parents=True)
        for name in ('backlog.md', 'implementation.md', 'policy.md'):
            (self.root / '.github/PULL_REQUEST_TEMPLATE' / name).write_text(f'## {name} 양식\n')
        self.status = ''
        self.log = '첫 커밋 제목\n두 번째 커밋'
        self.addCleanup(patch.stopall)
        patch.object(submit, 'git', side_effect=self.fake_git).start()

    def fake_git(self, root, *args):
        return {'status': self.status, 'log': self.log, 'rev-parse': str(self.gitdir)}[args[0]]

    def write_draft(self, branch, text):
        path = submit.draft_path(self.root, branch)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_branch_kind_selects_template(self):
        self.assertEqual(submit.template_for('backlog/backend/phase-01'), 'backlog.md')
        self.assertEqual(submit.template_for('feature/backend/phase-01-shell'), 'implementation.md')
        self.assertEqual(submit.template_for('policy/pr-submit-script'), 'policy.md')
        for branch in ('main', 'develop', 'release/1.0', 'hotfix/backend/phase-01-fix', 'topic'):
            with self.assertRaises(ValueError):
                submit.template_for(branch)

    def test_dirty_tree_or_no_commits_rejected(self):
        self.status = ' M CLAUDE.md'
        with self.assertRaises(ValueError):
            submit.plan(self.root, 'policy/x')
        self.status, self.log = '', ''
        with self.assertRaises(ValueError):
            submit.plan(self.root, 'policy/x')

    def test_without_draft_uses_local_template_and_first_commit(self):
        info = submit.plan(self.root, 'backlog/backend/phase-01')
        self.assertEqual(info['title'], '첫 커밋 제목')
        self.assertEqual(info['body'], '## backlog.md 양식\n')
        self.assertTrue(info['placeholder'])
        self.assertEqual(info['base'], 'develop')

    def test_draft_title_and_body_are_used(self):
        self.write_draft('policy/x', '# 초안 제목\n\n## 정책 변경\n- 이유\n')
        info = submit.plan(self.root, 'policy/x')
        self.assertEqual(info['title'], '초안 제목')
        self.assertEqual(info['body'], '## 정책 변경\n- 이유\n')
        self.assertFalse(info['placeholder'])

    def test_draft_is_bound_to_branch(self):
        self.write_draft('policy/other', '# 다른 브랜치\n본문\n')
        self.assertTrue(submit.plan(self.root, 'policy/x')['placeholder'])

    def test_explicit_title_and_body_override_draft(self):
        self.write_draft('policy/x', '# 초안 제목\n본문\n')
        body = self.root / 'body.md'
        body.write_text('직접 쓴 본문\n')
        info = submit.plan(self.root, 'policy/x', title='직접 제목', body_file=str(body))
        self.assertEqual((info['title'], info['body']), ('직접 제목', '직접 쓴 본문\n'))

    def test_policy_requires_approver_account(self):
        (self.root / '.github/git-flow.json').write_text('{"repository": "org/repo", "approver": "owner"}')
        with patch.object(submit, 'run', return_value='someone'):
            with self.assertRaises(ValueError):
                submit.precheck(self.root, 'policy/x')
        with patch.object(submit, 'run', return_value='Owner'):
            submit.precheck(self.root, 'policy/x')


if __name__ == '__main__':
    unittest.main()

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location('cleanup_branches', SCRIPTS / 'cleanup_branches.py')
cleanup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleanup)
REAL_GIT = cleanup.git


class CleanupBranchesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.gitdir = Path(self.temp.name)
        self.tips = {'main': 'm', 'develop': 'd', 'feature/backend/phase-01-auth': 'f1',
                     'policy/new-rule': 'p2', 'backlog/backend/phase-02': 'b1'}
        self.merged = [dict(number=1, head=dict(ref='feature/backend/phase-01-auth', sha='f1')),
                       dict(number=2, head=dict(ref='policy/new-rule', sha='p1')),
                       dict(number=3, head=dict(ref='main', sha='m'))]
        self.ancestors = set()  # (로컬 끝, PR head): GitHub에서 Update branch로 PR head만 앞서거나 다시 쓰인 경우
        self.current, self.dirty = 'feature/backend/phase-01-auth', ''
        self.calls = []
        self.addCleanup(patch.stopall)
        patch.object(cleanup, 'load_config', return_value=('org/repo', 'owner')).start()
        patch.object(cleanup, 'merged_prs', side_effect=lambda *a: self.merged).start()
        patch.object(cleanup, 'git', side_effect=self.git).start()
        patch.object(cleanup, 'has_ref', return_value=False).start()
        patch.object(cleanup, 'contains_tip', side_effect=lambda root, tip, pr: (tip, pr['head']['sha']) in self.ancestors).start()
        patch.object(cleanup, 'context_path', return_value=self.gitdir / 'yardpilot-approval.json').start()
        patch.object(cleanup, 'draft_path', side_effect=lambda root, b: self.gitdir / f"{b.replace('/', '__')}.md").start()

    def git(self, root, *args):
        self.calls.append(args)
        if args[0] == 'branch' and args[1] == '--show-current':
            return self.current
        if args[0] == 'status':
            return self.dirty
        if args[0] == 'for-each-ref':
            return '\n'.join(self.tips)
        if args[0] == 'rev-parse':
            return self.tips[args[1]]
        return ''

    def writes(self):
        return [c for c in self.calls if c[0] in ('switch', 'pull') or c[:2] == ('branch', '-D')]

    def test_plan_deletes_only_branches_whose_tip_was_merged(self):
        delete, keep = cleanup.plan(None, self.merged)
        self.assertEqual(delete, ['feature/backend/phase-01-auth'])
        self.assertEqual(dict(keep), {'policy/new-rule': '병합된 PR 이후의 커밋이 있습니다',
                                      'backlog/backend/phase-02': '병합된 PR이 없습니다'})

    def test_branch_updated_on_github_before_merge_is_deleted(self):
        # contains_tip 판정 자체는 실제 git이 필요해 RealCherryTest에서 검증한다.
        self.ancestors.add(('p2', 'p1'))
        delete, keep = cleanup.plan(None, self.merged)
        self.assertEqual(delete, ['feature/backend/phase-01-auth', 'policy/new-rule'])
        self.assertEqual(dict(keep), {'backlog/backend/phase-02': '병합된 PR이 없습니다'})

    def test_merged_current_branch_switches_updates_and_deletes(self):
        branch = 'feature/backend/phase-01-auth'
        cleanup.draft_path(None, branch).write_text('# 초안\n')
        cleanup.context_path(None).write_text(json.dumps(dict(branch=branch)))
        self.assertEqual(cleanup.main([], None), 0)
        self.assertEqual(self.writes(), [('switch', 'develop'), ('pull', '--ff-only', 'origin', 'develop'),
                                         ('branch', '-D', branch)])
        self.assertFalse(cleanup.draft_path(None, branch).exists())
        self.assertFalse(cleanup.context_path(None).exists())

    def test_other_context_is_kept(self):
        cleanup.context_path(None).write_text(json.dumps(dict(branch='feature/backend/phase-02-x')))
        cleanup.main([], None)
        self.assertTrue(cleanup.context_path(None).exists())

    def test_dirty_current_branch_is_kept(self):
        self.dirty = ' M backend/app.py'
        self.assertEqual(cleanup.main([], None), 0)
        self.assertEqual(self.writes(), [])

    def test_unmerged_current_branch_skips_develop_update(self):
        self.current = 'backlog/backend/phase-02'
        cleanup.main([], None)
        self.assertEqual(self.writes(), [('branch', '-D', 'feature/backend/phase-01-auth')])

    def test_dry_run_changes_nothing(self):
        self.assertEqual(cleanup.main(['--dry-run'], None), 0)
        self.assertEqual(self.writes(), [])



class RealCherryTest(unittest.TestCase):
    """contains_tip을 실제 임시 저장소로 검증한다: 같은 패치는 포함, 새 커밋은 미포함."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sh('init', '-q', '-b', 'develop')
        self.commit('base.txt', 'base')
        self.sh('switch', '-q', '-c', 'work')
        self.tip = self.commit('work.txt', 'work')
        self.sh('switch', '-q', 'develop')
        self.commit('other.txt', 'other')

    def sh(self, *args):
        return REAL_GIT(self.root, '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'core.hooksPath=/dev/null', *args)

    def commit(self, name, text):
        (self.root / name).write_text(text)
        self.sh('add', name)
        self.sh('commit', '-q', '-m', text)
        return self.sh('rev-parse', 'HEAD')

    def check(self, head):
        with patch.object(cleanup, 'git', side_effect=lambda root, *a: '' if a[0] == 'fetch' else self.sh(*a)):
            return cleanup.contains_tip(self.root, self.tip, dict(number=1, head=dict(sha=head)))

    def test_merge_update_rebase_update_and_new_commit(self):
        self.sh('switch', '-q', '-c', 'merged', self.tip)
        self.sh('merge', '-q', '--no-edit', 'develop')
        self.assertTrue(self.check(self.sh('rev-parse', 'HEAD')))
        self.sh('switch', '-q', '-c', 'rebased', 'develop')
        self.sh('cherry-pick', self.tip)
        self.assertTrue(self.check(self.sh('rev-parse', 'HEAD')))
        self.assertFalse(self.check(self.sh('rev-parse', 'develop')))


if __name__ == '__main__':
    unittest.main()

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('protect_branches', Path(__file__).resolve().parents[2] / 'scripts/protect_branches.py')
protect = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(protect)


class ProtectBranchesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '.github').mkdir()
        (self.root / '.github/git-flow.json').write_text('{"repository": null, "approver": null}')
        # Shape of GET /rulesets/{id}: server adds ids, defaults and extra parameters.
        self.remote = json.loads(json.dumps(protect.ruleset(1)))
        self.remote.update(id=7, source='org/repo', current_user_can_bypass='never')
        self.remote['rules'][2]['parameters']['allowed_merge_methods'] = ['merge', 'squash', 'rebase']
        self.listing = [dict(id=7, name=protect.NAME)]
        self.calls = []
        self.addCleanup(patch.stopall)
        patch.object(protect, 'gh', side_effect=self.gh).start()

    def gh(self, root, *args, payload=None):
        self.calls.append((args, payload))
        if args[0].endswith('rulesets?per_page=100&includes_parents=false'):
            return self.listing
        if args[0] == 'repos/org/repo/rulesets/7':
            return self.remote
        if args[0] == '-X' and args[1] == 'POST':
            self.listing = [dict(id=7, name=protect.NAME)]
        return {}

    def run_main(self, *argv):
        return protect.main([*argv, '--repo', 'org/repo'], self.root)

    def test_ruleset_blocks_direct_changes_without_bypass(self):
        desired = protect.ruleset(1)
        self.assertEqual(desired['bypass_actors'], [])
        self.assertEqual(desired['conditions']['ref_name']['include'], ['refs/heads/main', 'refs/heads/develop'])
        rules = {r['type']: r.get('parameters') for r in desired['rules']}
        self.assertEqual(set(rules), {'deletion', 'non_fast_forward', 'pull_request', 'required_status_checks'})
        self.assertEqual(rules['pull_request']['required_approving_review_count'], 1)
        self.assertTrue(rules['pull_request']['dismiss_stale_reviews_on_push'])
        self.assertTrue(rules['pull_request']['require_last_push_approval'])
        checks = rules['required_status_checks']['required_status_checks']
        self.assertEqual({c['context'] for c in checks}, {'approval-gate', 'harness'})
        self.assertTrue(all(c['integration_id'] == protect.GITHUB_ACTIONS for c in checks))

    def test_unconfigured_repository_fails_closed(self):
        with self.assertRaises(ValueError):
            protect.main(['check'], self.root)

    def test_check_passes_with_server_defaults(self):
        self.assertEqual(self.run_main('check'), 0)

    def test_check_fails_on_missing_weakened_or_bypassed_ruleset(self):
        weakenings = [
            lambda r: r.update(enforcement='evaluate'),
            lambda r: r.update(bypass_actors=[dict(actor_id=5, actor_type='RepositoryRole', bypass_mode='always')]),
            lambda r: r.pop('bypass_actors'),
            lambda r: r['conditions']['ref_name'].update(include=['refs/heads/main']),
            lambda r: r['rules'].pop(0),
            lambda r: r['rules'][2]['parameters'].update(required_approving_review_count=0),
            lambda r: r['rules'][3]['parameters']['required_status_checks'].pop(),
        ]
        original = json.dumps(self.remote)
        for weaken in weakenings:
            self.remote = json.loads(original)
            weaken(self.remote)
            self.assertEqual(self.run_main('check'), 1)
        self.listing = []
        self.assertEqual(self.run_main('check'), 1)

    def test_apply_creates_then_updates_same_ruleset(self):
        self.listing = []
        self.assertEqual(self.run_main('apply'), 0)
        self.assertIn((('-X', 'POST', 'repos/org/repo/rulesets', '--input', '-'), protect.ruleset(1)), self.calls)
        self.calls.clear()
        self.assertEqual(self.run_main('apply'), 0)
        self.assertIn((('-X', 'PUT', 'repos/org/repo/rulesets/7', '--input', '-'), protect.ruleset(1)), self.calls)
        self.assertFalse(any(args[1] == 'POST' for args, _ in self.calls if args[0] == '-X'))

    def test_duplicate_rulesets_rejected(self):
        self.listing.append(dict(id=8, name=protect.NAME))
        with self.assertRaises(ValueError):
            self.run_main('check')

    def test_plan_does_not_call_github(self):
        self.assertEqual(protect.main(['plan'], self.root), 0)
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()

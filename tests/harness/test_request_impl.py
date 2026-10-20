import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location('request_impl', SCRIPTS / 'request_impl.py')
request = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(request)

PATH = 'backlog/backend/phase-01.md'


class RequestImplTest(unittest.TestCase):
    def setUp(self):
        self.pr = dict(number=42, merge_commit_sha='a' * 40)
        self.existing = None
        self.addCleanup(patch.stopall)
        patch.object(request, 'load_config', return_value=('org/repo', 'owner')).start()
        self.latest = patch.object(request, 'latest_backlog_pr', return_value=42).start()
        self.approved = patch.object(request, 'approved_pr', side_effect=lambda *a: self.pr).start()
        self.documents = patch.object(request, 'check_documents').start()
        patch.object(request, 'find_request', side_effect=lambda *a: self.existing).start()
        self.run = patch.object(request, 'run', return_value='77').start()
        self.validate = patch.object(request, 'validate').start()

    def main(self, *argv):
        return request.main([PATH, *argv], root=Path('.'))

    def test_posts_exact_comment_then_runs_start_gate(self):
        self.assertEqual(self.main(), 0)
        self.run.assert_called_once_with(Path('.'), 'gh', 'api', '-X', 'POST', 'repos/org/repo/issues/42/comments',
                                         '-f', f"body=implement {PATH} {'a' * 40}", '--jq', '.id')
        self.validate.assert_called_once_with(Path('.'), dict(backlog=PATH, approval_pr=42, request_comment=77))

    def test_checks_approval_and_documents_before_posting(self):
        self.documents.side_effect = ValueError('승인 문서가 변경되었습니다')
        with self.assertRaises(ValueError):
            self.main()
        self.run.assert_not_called()
        self.documents.side_effect = None
        self.approved.side_effect = ValueError('지정 승인자의 최신 head 승인 또는 직접 병합 필요')
        with self.assertRaises(ValueError):
            self.main()
        self.run.assert_not_called()

    def test_dry_run_and_existing_request_do_not_post(self):
        self.assertEqual(self.main('--dry-run'), 0)
        self.existing = 9
        self.assertEqual(self.main(), 0)
        self.run.assert_not_called()

    def test_rejected_comment_reported(self):
        self.validate.side_effect = ValueError('병합 후 저장소 참여자가 남긴 정확한 implement 요청 댓글 필요')
        with self.assertRaisesRegex(ValueError, 'ID 77'):
            self.main()

    def test_explicit_pr_skips_lookup(self):
        self.main('--pr', '40', '--dry-run')
        self.latest.assert_not_called()
        self.approved.assert_called_once_with(Path('.'), 'org/repo', 'owner', PATH, 40)


if __name__ == '__main__':
    unittest.main()

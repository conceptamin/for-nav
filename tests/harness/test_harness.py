import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('harness', Path(__file__).resolve().parents[2] / 'scripts/harness.py')
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)

DOCUMENT = '''# Phase

## 목표
권한 검사
## 범위
API
## 작업 체크리스트
- [ ] 구현
## 의존성
없음
## 완료 조건
- [ ] 비인가 요청 거부
## 검증 결과
미실행: 구현 후 실제 명령과 결과를 기록한다.
'''


class HarnessTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def write(self, path='backlog/backend/phase-01.md', text=DOCUMENT):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        return target

    def call(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(harness.main(list(args), root=self.root), 0)
        return output.getvalue()

    def test_no_phases_is_skip_and_json_is_ignored(self):
        self.write('backlog/backend.json', 'invalid JSON')
        self.write('backlog/backend/README.md', 'navigation')
        self.assertIn('SKIP', self.call('check'))

    def test_check_and_board_are_read_only(self):
        path = self.write(text=DOCUMENT.replace('- [ ] 구현', '- [x] 구현'))
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertIn('PASS', self.call('check'))
        self.assertIn('작업 1/1, 완료 조건 0/1', self.call('board'))
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(path.read_bytes(), before[path])

    def test_required_sections_and_checkboxes(self):
        for section in harness.SECTIONS:
            self.write(text=DOCUMENT.replace('## ' + section, '## 삭제'))
            with self.assertRaises(ValueError):
                harness.load(self.root)
        self.write(text=DOCUMENT.replace('- [ ] 구현', '구현'))
        with self.assertRaises(ValueError):
            harness.load(self.root)

    def test_comments_and_fenced_examples_do_not_supply_sections(self):
        for text in ('```md\n' + DOCUMENT + '```\n', '<!--\n' + DOCUMENT + '-->', '~~~~md\n' + DOCUMENT + '~~~~\n'):
            self.write(text=text)
            with self.assertRaises(ValueError):
                harness.load(self.root)

    def test_duplicate_and_empty_sections_rejected(self):
        for text in (DOCUMENT + '\n## 목표\n중복', DOCUMENT.replace('권한 검사', '<!-- empty -->')):
            self.write(text=text)
            with self.assertRaises(ValueError):
                harness.load(self.root)

    def test_cross_lane_dependency_and_cycle(self):
        self.write(text=DOCUMENT.replace('없음', '[선행](../frontend/phase-01.md)'))
        self.write('backlog/frontend/phase-01.md')
        selected, records = harness.load(self.root, lane='backend')
        self.assertEqual(len(selected), 1)
        self.assertEqual(len(records), 2)
        self.write('backlog/frontend/phase-01.md', DOCUMENT.replace('없음', '[선행](../backend/phase-01.md)'))
        with self.assertRaisesRegex(ValueError, '순환'):
            harness.load(self.root)

    def test_missing_and_pending_dependency(self):
        self.write(text=DOCUMENT.replace('없음', '[선행](phase-02.md)'))
        with self.assertRaises(ValueError):
            harness.load(self.root)
        self.write(text=DOCUMENT.replace('없음', '미정: [선행](phase-02.md)'))
        self.assertIn('WARN', self.call('check'))

    def test_dependency_cannot_escape_even_if_pending(self):
        for target in ('../../../outside.md', 'https://example.com/a.md', '/tmp/a.md', 'phase.json'):
            self.write(text=DOCUMENT.replace('없음', f'미정: [선행]({target})'))
            with self.assertRaises(ValueError):
                harness.load(self.root)

    def test_explicit_custom_path_and_missing_path(self):
        self.write('plans/custom.md')
        self.assertIn('PASS', self.call('check', 'plans/custom.md'))
        with self.assertRaises(ValueError):
            self.call('check', 'missing.md')

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'phase.md'
            target.write_text(DOCUMENT)
            link = self.root / 'phase.md'
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                harness.load(self.root, ['phase.md'])

    def test_old_mutating_commands_removed(self):
        for action in ('start', 'done', 'run', 'block', 'resume', 'next'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                harness.main([action], root=self.root)
            self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()

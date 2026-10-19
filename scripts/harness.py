#!/usr/bin/env python3
"""Read-only phase Markdown checks; implementation approval belongs to git_flow.py."""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LANES = ('frontend', 'backend', 'modeling')
SECTIONS = ('목표', '범위', '작업 체크리스트', '의존성', '완료 조건', '검증 결과')
CHECKBOX = re.compile(r'^\s*[-*+] \[([ xX])\] \S.*$', re.MULTILINE)
LINK = re.compile(r'(?<!!)\[[^\]]+\]\(([^\s)]+)\)')


def visible_text(text):
    """Ignore comments and fenced examples rather than interpreting them as evidence."""
    text = re.sub(r'<!--.*?(?:-->|\Z)', '', text, flags=re.DOTALL)
    result, fence = [], None
    for line in text.splitlines():
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})(.*)$', line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue
        if marker:
            fence = marker[1]
            continue
        result.append(line)
    return '\n'.join(result)


def local_markdown(root, path):
    path = path.resolve()
    if not path.is_relative_to(root.resolve()) or path.suffix != '.md' or not path.is_file():
        raise ValueError(f'저장소 내부 Markdown 파일이 필요합니다: {path}')
    return path


def parse(root, path):
    path = local_markdown(root, path)
    sections, current = {}, None
    for line in visible_text(path.read_text(encoding='utf-8')).splitlines():
        heading = re.match(r'^##\s+(.+?)(?:\s+#+)?\s*$', line)
        if heading:
            current = heading[1].strip()
            if current in sections:
                raise ValueError(f'{path.name}: 중복 섹션 {current}')
            sections[current] = []
        elif re.match(r'^#\s', line):
            current = None
        elif current:
            sections[current].append(line)
    sections = {key: '\n'.join(lines).strip() for key, lines in sections.items()}
    for name in SECTIONS:
        if not sections.get(name):
            raise ValueError(f'{path.name}: 내용이 있는 ## {name} 섹션 필요')
    counts = {}
    for name in ('작업 체크리스트', '완료 조건'):
        boxes = CHECKBOX.findall(sections[name])
        if not boxes:
            raise ValueError(f'{path.name}: {name}에 체크박스 필요')
        counts[name] = (sum(box.lower() == 'x' for box in boxes), len(boxes))
    dependencies, warnings = [], []
    for line in sections['의존성'].splitlines():
        pending = '미정' in line
        if pending:
            warnings.append(f'{path.relative_to(root)}: 미정 의존성: {line.strip()}')
        for target in LINK.findall(line):
            target = target.split('#', 1)[0]
            if not target or re.match(r'^[a-zA-Z][\w+.-]*:', target) or Path(target).is_absolute():
                raise ValueError(f'{path.name}: 의존성은 상대 Markdown 링크여야 합니다: {target}')
            dependency = (path.parent / target).resolve()
            # Pending links may be absent, but must never escape the repository.
            if not dependency.is_relative_to(root) or dependency.suffix != '.md':
                raise ValueError(f'{path.name}: 잘못된 의존성 경로: {target}')
            if pending and not dependency.exists():
                continue
            dependencies.append(local_markdown(root, dependency))
    return dict(path=path, counts=counts, dependencies=dependencies, warnings=warnings)


def load(root, paths=(), lane=None):
    root = root.resolve()
    selected = [local_markdown(root, root / path) for path in paths] if paths else [
        path.resolve() for area in ((lane,) if lane else LANES)
        for path in sorted((root / 'backlog' / area).glob('phase-*.md'))]
    records, visiting = {}, set()

    def visit(path):
        if path in visiting:
            raise ValueError(f'의존성 순환: {path.relative_to(root)}')
        if path in records:
            return
        visiting.add(path)
        record = parse(root, path)
        for dependency in record['dependencies']:
            visit(dependency)
        visiting.remove(path)
        records[path] = record

    for path in selected:
        visit(path)
    return list(dict.fromkeys(selected)), records


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'board'))
    parser.add_argument('paths', nargs='*', help='저장소 기준 phase Markdown 경로')
    parser.add_argument('--lane', choices=LANES)
    args = parser.parse_args(argv)
    if args.paths and args.lane:
        parser.error('명시 경로와 --lane은 함께 사용할 수 없습니다')
    selected, records = load(root, args.paths, args.lane)
    if not selected:
        print('SKIP: phase Markdown 문서가 없습니다. 제품 구현·완료를 의미하지 않습니다.')
        return 0
    for record in records.values():
        for warning in record['warnings']:
            print(f'WARN: {warning}')
    if args.action == 'board':
        for path in selected:
            record = records[path]
            work = record['counts']['작업 체크리스트']
            acceptance = record['counts']['완료 조건']
            print(f'{path.relative_to(root.resolve())}: 작업 {work[0]}/{work[1]}, 완료 조건 {acceptance[0]}/{acceptance[1]}, 의존 문서 {len(record["dependencies"])}')
    print(f'PASS: Markdown 구조 {len(records)}개 검사. 승인·제품 품질·병합 상태는 별도 확인이 필요합니다.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)

# schema.py가 백엔드 열거값·Intake 필드와 같은지 비교한다.
# 백엔드는 pydantic·fastapi를 쓰므로 import하지 않는다. vocab.py는 typing만 써서 파일로 직접 읽고, schemas.py는 AST로 Intake 정의만 꺼낸다.

import ast
import importlib.util
from pathlib import Path
from typing import get_args, get_type_hints

import pytest

from fornav_modeling import schema

BACKEND_APP = Path(__file__).resolve().parents[2] / "backend" / "app"


def load_backend_vocab():
    spec = importlib.util.spec_from_file_location("backend_vocab", BACKEND_APP / "vocab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def backend_intake_fields(vocab) -> dict[str, tuple[object, bool]]:
    """백엔드 Intake의 필드 이름 → (타입, 필수 여부). 기본값이 없는 필드가 필수다."""
    tree = ast.parse((BACKEND_APP / "schemas.py").read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Intake")
    fields = {}
    for node in cls.body:
        if isinstance(node, ast.AnnAssign):
            annotation = eval(ast.unparse(node.annotation), vars(vocab))
            fields[node.target.id] = (annotation, node.value is None)
    return fields


vocab = load_backend_vocab()


@pytest.mark.parametrize(
    "name",
    ["Lang", "BodyPart", "Symptom", "Department", "Onset", "Industry", "WorkType", "District", "YesNoUnknown", "AgeGroup", "Sex", "Mental"],
)
def test_enum_values_and_order_match_backend(name):
    # Literal끼리 ==는 순서를 무시하므로 값 튜플로 비교한다. 순서가 라벨 순서다.
    assert get_args(getattr(schema, name)) == get_args(getattr(vocab, name))


def test_enum_sizes():
    assert len(schema.DEPARTMENTS) == 10
    assert len(schema.BODY_PARTS) == 13
    assert len(schema.SYMPTOMS) == len(vocab.SYMPTOMS) == 15


def test_label_tuples_follow_backend_tables():
    assert list(schema.LANGS) == vocab.LANGS
    assert list(schema.BODY_PARTS) == list(vocab.BODY_PARTS)
    assert list(schema.SYMPTOMS) == list(vocab.SYMPTOMS)
    assert list(schema.DEPARTMENTS) == list(vocab.DEPARTMENTS)
    assert list(schema.ONSETS) == list(vocab.ONSETS)


def test_intake_fields_match_backend():
    backend = backend_intake_fields(vocab)
    hints = get_type_hints(schema.Intake)

    assert list(hints) == list(backend)
    for field, (annotation, required) in backend.items():
        assert hints[field] == annotation, field
        assert (field in schema.Intake.__required_keys__) == required, field

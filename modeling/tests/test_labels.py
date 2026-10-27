# KTAS → 응급도 3단계 변환.

import pytest

from fornav_modeling.labels.ktas import ACUITIES, ktas_to_acuity


def test_label_order_is_fixed():
    assert ACUITIES == ("emergency", "today", "outpatient")


@pytest.mark.parametrize(("ktas", "acuity"), [(1, "emergency"), (2, "emergency"), (3, "today"), (4, "outpatient"), (5, "outpatient")])
def test_ktas_to_acuity(ktas, acuity):
    assert ktas_to_acuity(ktas) == acuity


@pytest.mark.parametrize("ktas", [0, 6, -1, None, True, "1"])
def test_invalid_ktas_raises(ktas):
    with pytest.raises(ValueError):
        ktas_to_acuity(ktas)

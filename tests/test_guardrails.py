"""Unit tests for deterministic guardrail validation."""
import pytest

from app.core.exceptions import GuardrailError
from app.services.guardrails.validator import validate_directives, validate_one


class TestValidDirectives:
    def test_solar_reduction_ok(self):
        raw = {
            "note_index": 0,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [13, 14], "factor": 0.2},
            "explanation": "test",
        }
        out = validate_one(raw, 0)
        assert out["directive_type"] == "solar_reduction"
        assert out["applies"] is True
        assert out["structured_adjustment"]["hours"] == [13, 14]

    def test_no_op_ok(self):
        raw = {
            "note_index": 0,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "test",
        }
        out = validate_one(raw, 0)
        assert out["applies"] is False
        assert out["structured_adjustment"] is None

    def test_minimum_reserve_ok(self):
        raw = {
            "note_index": 0,
            "applies": True,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [18, 19], "minimum_energy_kwh": 100},
            "explanation": "test",
        }
        out = validate_one(raw, 0)
        assert out["structured_adjustment"]["minimum_energy_kwh"] == 100

    def test_no_charge_window_ok(self):
        raw = {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [2, 3, 4]},
            "explanation": "test",
        }
        out = validate_one(raw, 0)
        assert out["structured_adjustment"] == {"hours": [2, 3, 4]}

    def test_max_grid_window_ok(self):
        raw = {
            "note_index": 0,
            "applies": True,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [18, 19], "max_grid_kwh": 155},
            "explanation": "test",
        }
        out = validate_one(raw, 0)
        assert out["structured_adjustment"]["max_grid_kwh"] == 155


class TestInvalidDirectives:
    def test_unknown_type_rejected(self):
        raw = {
            "note_index": 0,
            "applies": True,
            "directive_type": "magic_directive",
            "structured_adjustment": {},
        }
        with pytest.raises(GuardrailError):
            validate_one(raw, 0)

    def test_no_op_with_applies_true_rejected(self):
        raw = {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_op",
            "structured_adjustment": None,
        }
        with pytest.raises(GuardrailError):
            validate_one(raw, 0)

    def test_no_op_with_non_null_adjustment_rejected(self):
        raw = {
            "note_index": 0,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": {"hours": [1]},
        }
        with pytest.raises(GuardrailError):
            validate_one(raw, 0)

    def test_solar_factor_out_of_range(self):
        raw = {
            "note_index": 0,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [10], "factor": 1.5},
        }
        with pytest.raises(GuardrailError):
            validate_one(raw, 0)

    def test_hours_not_ascending(self):
        raw = {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [5, 3, 4]},
        }
        with pytest.raises(GuardrailError):
            validate_one(raw, 0)

    def test_hours_duplicate(self):
        raw = {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [5, 5]},
        }
        with pytest.raises(GuardrailError):
            validate_one(raw, 0)

    def test_hours_out_of_range(self):
        raw = {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [25]},
        }
        with pytest.raises(GuardrailError):
            validate_one(raw, 0)

    def test_wrong_note_index(self):
        raw = {
            "note_index": 5,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [1]},
        }
        with pytest.raises(GuardrailError):
            validate_one(raw, 0)


class TestValidateFullList:
    def test_count_mismatch_rejected(self):
        with pytest.raises(GuardrailError):
            validate_directives([], expected_count=2)

    def test_order_preserved(self):
        raws = [
            {
                "note_index": 0,
                "applies": True,
                "directive_type": "no_charge_window",
                "structured_adjustment": {"hours": [1]},
            },
            {
                "note_index": 1,
                "applies": False,
                "directive_type": "no_op",
                "structured_adjustment": None,
            },
        ]
        out = validate_directives(raws, expected_count=2)
        assert [d["note_index"] for d in out] == [0, 1]
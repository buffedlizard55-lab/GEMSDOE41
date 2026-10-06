import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from experiment_h41e import apply_kinematic_screen


def _record(family, slip, eligible=True):
    return {
        "family": family,
        "eligible": eligible,
        "source_properties": {"SLIPSENSE": slip},
    }


def test_h41e_uses_only_exact_kinematic_codes_and_does_not_mutate_inputs():
    records = [
        _record(0, "RL"),       # mapped NW right-lateral donor
        _record(0, "N"),        # mapped NW normal fault, not a dextral donor
        _record(0, "LL"),       # mapped NW left-lateral fault, not a dextral donor
        _record(0, "SS"),       # no silent aliasing of generic strike-slip
        _record(1, "N"),        # mapped N/NNE normal receiver
        _record(1, "RL"),       # mapped N/NNE right-lateral fault, not a normal receiver
        _record(1, None),        # missing value is not imputed
        _record(1, "N", eligible=False),  # prior geometric eligibility remains required
    ]
    screened, counts = apply_kinematic_screen(records)

    assert [r["eligible"] for r in screened] == [True, False, False, False, True, False, False, False]
    assert [r["eligible"] for r in records] == [True, True, True, True, True, True, True, False]
    assert counts["eligible_after_family_0"] == 1
    assert counts["eligible_after_family_1"] == 1
    assert counts["family_0_slipsense_N"] == 1
    assert counts["family_1_slipsense_MISSING"] == 1


def test_h41e_does_not_create_eligibility_for_unclassified_family():
    record = _record(2, "N")
    try:
        apply_kinematic_screen([record])
    except ValueError as exc:
        assert "family" in str(exc).lower()
    else:
        raise AssertionError("invalid family should be rejected")

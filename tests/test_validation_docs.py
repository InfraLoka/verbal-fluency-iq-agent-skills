# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Process findings F-002 and F-027: the protocols exist and the code points at them."""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROTOCOL = ROOT / "docs" / "validation" / "validation-protocol.md"
NORMING = ROOT / "docs" / "validation" / "norming-plan.md"


def test_validation_protocol_names_criterion_sample_subgroups_and_thresholds():
    text = PROTOCOL.read_text(encoding="utf-8")
    for heading in (
        "## Criterion measures",
        "## Sample size",
        "## Subgroup analyses",
        "## Acceptance thresholds",
    ):
        assert heading in text, heading
    assert "WAIS-IV Full Scale IQ" in text
    assert "| Held-out evaluation | 360 |" in text
    assert "r ≥ 0.50" in text
    assert "SEE ≤ 12 IQ points" in text
    assert "PPV and NPV" in text
    assert "Status: not started" in text


def test_norming_plan_defines_population_age_bands_and_language_strata():
    text = NORMING.read_text(encoding="utf-8")
    for heading in (
        "## Reference population",
        "## Age bands",
        "## Language-background strata",
        "## Sample size",
        "## Norm computation",
    ):
        assert heading in text, heading
    for band in ("17 to 19", "55 to 64"):
        assert band in text
    for stratum in ("Javanese first", "Sundanese first", "English as first language"):
        assert stratum in text
    assert "never defaulted" in text


def test_code_and_config_reference_the_validation_protocol():
    policy_src = (ROOT / "mcp-server" / "tools" / "policy.py").read_text(
        encoding="utf-8"
    )
    assert "docs/validation/validation-protocol.md" in policy_src
    norms = (ROOT / "mcp-server" / "config" / "iq_norms.json").read_text(
        encoding="utf-8"
    )
    assert "docs/validation/validation-protocol.md" in norms


def test_protocol_states_secondary_subgroups_are_not_validated():
    text = PROTOCOL.read_text(encoding="utf-8")
    assert "must not be used to screen" in text
    assert "dyslexia" in text
    assert text.count("must not be used to screen") >= 2

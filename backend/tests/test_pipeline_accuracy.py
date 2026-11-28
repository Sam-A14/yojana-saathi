import copy
import json
from pathlib import Path
from typing import Any

import pytest

from app.db.seed import DEFAULT_DATA_DIR
from app.pipeline.accuracy import (
    AccuracyError,
    compare_rules,
    compare_to_ground_truth,
    describe,
    ground_truth_path,
    leaf_conditions,
    main,
    render_accuracy,
)


def rules(*nodes: dict[str, Any], fixable: list[str] | None = None) -> dict[str, Any]:
    return {"all": list(nodes), "fixable": fixable or []}


AGE = {"field": "age", "op": "gte", "value": 60}
CATEGORY = {"field": "category", "op": "in", "value": ["SC", "ST", "OBC"]}
NO_TAX = {"not": {"any_member": {"field": "paid_income_tax_last_year", "op": "is_true"}}}


def load_seed(slug: str) -> dict[str, Any]:
    return json.loads((DEFAULT_DATA_DIR / "ground_truth" / f"{slug}.json").read_text("utf-8"))


# --- equivalent shapes count as equal --------------------------------------------------------


def test_order_of_rules_is_irrelevant() -> None:
    result = compare_rules("x", rules(AGE, CATEGORY, NO_TAX), rules(NO_TAX, AGE, CATEGORY))
    assert result.missed == [] and result.extra == []


def test_order_inside_all_any_and_in_lists_is_irrelevant() -> None:
    in_one = {"field": "category", "op": "in", "value": ["SC", "ST"]}
    in_two = {"field": "category", "op": "in", "value": ["ST", "SC"]}
    one = rules({"any": [AGE, in_one]})
    two = rules({"any": [in_two, AGE]})
    result = compare_rules("x", one, two)
    assert result.missed == [] and result.extra == []


def test_duplicate_values_and_integral_floats_are_the_same() -> None:
    expected = rules({"field": "income_band_max", "op": "lte", "value": 200000})
    got = rules({"field": "income_band_max", "op": "lte", "value": 200000.0})
    assert compare_rules("x", expected, got).extra == []
    in_a = rules({"field": "category", "op": "in", "value": ["SC", "ST"]})
    in_b = rules({"field": "category", "op": "in", "value": ["ST", "SC", "SC"]})
    assert compare_rules("x", in_a, in_b).extra == []


def test_nested_all_single_child_groups_and_double_not_are_flattened() -> None:
    plain = rules(AGE, CATEGORY)
    nested = rules({"all": [AGE, {"all": [CATEGORY]}]})
    assert compare_rules("x", plain, nested).extra == []
    double_not = rules(AGE, {"not": {"not": CATEGORY}})
    assert compare_rules("x", plain, double_not).extra == []


# --- different meaning counts as different ---------------------------------------------------


def test_a_missing_exclusion_wrapper_is_a_miss_and_an_extra() -> None:
    wrong = rules(AGE, {"any_member": {"field": "paid_income_tax_last_year", "op": "is_true"}})
    result = compare_rules("x", rules(AGE, NO_TAX), wrong)
    assert [describe(leaf) for leaf in result.missed] == [
        "not > any_member > paid_income_tax_last_year is_true"
    ]
    assert [describe(leaf) for leaf in result.extra] == [
        "any_member > paid_income_tax_last_year is_true"
    ]


def test_all_and_any_over_the_same_leaves_are_different() -> None:
    result = compare_rules("x", rules({"all": [AGE, CATEGORY]}), rules({"any": [AGE, CATEGORY]}))
    assert len(result.missed) == 2 and len(result.extra) == 2


def test_one_person_with_both_differs_from_two_people_with_one_each() -> None:
    one_person = rules(
        {"any_member": {"all": [{"field": "is_student", "op": "is_true"}, AGE]}},
    )
    two_people = rules(
        {"any_member": {"field": "is_student", "op": "is_true"}}, {"any_member": AGE}
    )
    result = compare_rules("x", one_person, two_people)
    assert len(result.missed) == 2 and len(result.extra) == 2


# --- the numbers and the lists of what went wrong ---------------------------------------------


def test_precision_recall_and_the_missed_and_extra_lists() -> None:
    expected = rules(AGE, CATEGORY, NO_TAX)
    got = rules(AGE, {"field": "gender", "op": "eq", "value": "female"}, NO_TAX)
    result = compare_rules("test-scheme", expected, got)

    assert result.expected_count == 3 and result.extracted_count == 3
    text = render_accuracy([result])
    assert "exact:      precision 67% (2/3), recall 67% (2/3)" in text
    assert "test-scheme:" in text
    assert 'Missed (in the seed file, not extracted):\n    - category in ["OBC","SC","ST"]' in text
    # gender is a closed list, so the extra condition is canonicalised to "in" in the second score.
    assert '    - gender eq "female"' in text
    assert "Every condition matches." not in text


def test_a_perfect_match_says_so() -> None:
    text = render_accuracy([compare_rules("x", rules(AGE), rules(AGE))])
    assert "exact:      precision 100% (1/1), recall 100% (1/1)" in text
    assert "normalised: precision 100% (1/1), recall 100% (1/1)" in text
    assert "Every condition matches." in text


def test_fixable_differences_are_reported_separately() -> None:
    a = rules(AGE, fixable=["has_land_record"])
    b = rules(AGE, fixable=["has_ration_card"])
    result = compare_rules("x", a, b)
    assert result.fixable_missed == ["has_land_record"] and result.fixable_extra == [
        "has_ration_card"
    ]
    assert "'fixable' differs" in render_accuracy([result])


def test_overall_adds_up_counts_across_schemes() -> None:
    first = compare_rules("a", rules(AGE, CATEGORY), rules(AGE, CATEGORY))  # 2/2, 2/2
    second = compare_rules(
        "b", rules(AGE, CATEGORY, NO_TAX), rules(AGE)
    )  # 1/1, 1/3: overall 3/3 and 3/5
    text = render_accuracy([first, second])
    assert "OVERALL (2 schemes):" in text
    assert "exact:      precision 100% (3/3), recall 60% (3/5)" in text


def test_an_empty_extraction_has_no_precision_and_zero_recall() -> None:
    result = compare_rules("x", rules(AGE), {"all": []})
    assert "exact:      precision n/a, recall 0% (0/1)" in render_accuracy([result])


def test_unreadable_rules_raise_instead_of_scoring_zero() -> None:
    with pytest.raises(AccuracyError):
        leaf_conditions({"nope": 1})
    with pytest.raises(AccuracyError):
        leaf_conditions({"all": ["text"]})
    with pytest.raises(AccuracyError):
        leaf_conditions({"all": [{"mystery": 1}]})


# --- against the real seed files ----------------------------------------------------------------


@pytest.mark.parametrize("slug", ["pm-kisan", "ignwps"])
def test_a_seed_file_compared_with_a_reshuffled_copy_is_perfect(slug: str) -> None:
    scheme = copy.deepcopy(load_seed(slug))
    scheme["version"]["rules"]["all"].reverse()
    result = compare_to_ground_truth(slug, scheme)
    assert result is not None
    assert result.missed == [] and result.extra == [] and len(result.matched) > 0


def test_dropping_one_rule_from_a_seed_file_shows_up_as_a_miss() -> None:
    scheme = copy.deepcopy(load_seed("pm-kisan"))
    dropped = scheme["version"]["rules"]["all"].pop()
    result = compare_to_ground_truth("pm-kisan", scheme)
    assert result is not None
    assert result.extra == [] and len(result.missed) >= 1
    assert dropped  # the removed rule really existed


def test_no_seed_file_means_no_score(tmp_path: Path) -> None:
    assert compare_to_ground_truth("no-such-scheme", {"version": {"rules": rules(AGE)}}) is None
    assert compare_to_ground_truth("pm-kisan", {"version": {"rules": rules(AGE)}}, tmp_path) is None


def test_cli_prints_per_scheme_and_overall(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = []
    for slug in ("pm-kisan", "ignwps"):
        path = tmp_path / f"{slug}.json"
        path.write_text(json.dumps({"scheme": load_seed(slug)}), encoding="utf-8")
        files.append(str(path))

    assert main(files) == 0
    out = capsys.readouterr().out
    assert "pm-kisan:\n  exact:      precision 100%" in out
    assert "ignwps:\n  exact:      precision 100%" in out
    assert "OVERALL (2 schemes)" in out


def test_cli_fails_cleanly_without_a_ground_truth_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"scheme": {"slug": "zzz-unknown"}}), encoding="utf-8")
    assert main([str(path)]) == 1
    assert "no ground-truth file" in capsys.readouterr().err


# --- the ground truth is its own folder (decision 052) -----------------------------------------


def test_the_reference_is_the_ground_truth_folder_not_the_seed_folder() -> None:
    assert ground_truth_path("pm-kisan") == DEFAULT_DATA_DIR / "ground_truth" / "pm-kisan.json"


def test_a_scheme_with_a_seed_file_but_no_ground_truth_has_no_score() -> None:
    """pmay-g was written by the extractor: comparing the model with its own output would be a
    perfect score that means nothing."""
    assert (DEFAULT_DATA_DIR / "schemes_seed" / "pmay-g.json").is_file()
    assert not ground_truth_path("pmay-g").exists()
    seed = json.loads((DEFAULT_DATA_DIR / "schemes_seed" / "pmay-g.json").read_text("utf-8"))
    assert compare_to_ground_truth("pmay-g", seed) is None


def test_the_score_still_reads_the_ground_truth_when_the_seed_file_is_replaced(
    tmp_path: Path,
) -> None:
    """The point of the folder: the reference survives a bump_version replacement of the seed."""
    truth = load_seed("pm-kisan")
    (tmp_path / "ground_truth").mkdir()
    (tmp_path / "ground_truth" / "pm-kisan.json").write_text(json.dumps(truth), encoding="utf-8")
    (tmp_path / "schemes_seed").mkdir()
    replaced = copy.deepcopy(truth)
    replaced["version"]["rules"]["all"] = [AGE]  # a different, extractor-style seed
    (tmp_path / "schemes_seed" / "pm-kisan.json").write_text(json.dumps(replaced), encoding="utf-8")

    result = compare_to_ground_truth("pm-kisan", replaced, tmp_path)

    assert result is not None and len(result.missed) >= 1  # scored against the human file


def test_every_ground_truth_file_is_a_scheme_file_named_by_its_slug() -> None:
    files = sorted((DEFAULT_DATA_DIR / "ground_truth").glob("*.json"))
    assert {f.stem for f in files} >= {"pm-kisan", "ignwps"}
    for file in files:
        scheme = json.loads(file.read_text("utf-8"))
        assert scheme["slug"] == file.stem, file.name
        assert scheme["version"]["rules"]["all"], file.name


def test_the_seed_loader_never_reads_the_ground_truth_folder() -> None:
    from app.db.seed import read_seed_files

    seeded = {scheme["slug"] for scheme in read_seed_files().schemes}
    assert (DEFAULT_DATA_DIR / "ground_truth" / "pm-kisan.json").is_file()
    # Reading it by mistake would make every ground-truth slug appear twice.
    assert len(seeded) == len(list((DEFAULT_DATA_DIR / "schemes_seed").glob("*.json"))) - 1

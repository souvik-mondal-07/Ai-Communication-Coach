"""Step 17: pure engine logic (no DB, no AI)."""
import random

import pytest

from app.services.cybersecurity import practice_engine as e

CATALOG = [
    {"slug": f"{c.lower().replace(' ', '-')}-{i}", "title": f"{c} {i}", "category": c,
     "difficulty": "beginner", "description": "d", "learning_objectives": []}
    for c in ("Networking", "Linux", "Web Security", "SOC", "SIEM", "Incident Response", "Cryptography",
              "Threat Intelligence")
    for i in (1, 2)
]


def plan(**kw):
    base = dict(mode="topic", category="Linux", topic_slug=None, question_type="mixed", question_count=4,
                difficulty="beginner", catalog=CATALOG, personalization=None, recent_slugs=set(),
                recent_categories=[], rng=random.Random(1))
    base.update(kw)
    return e.plan_session(**base)


def test_hint_penalty_is_gentle_and_capped():
    assert [e.apply_hint_penalty(100, n) for n in range(4)] == [100, 95, 88, 80]
    assert e.apply_hint_penalty(100, 9) == 80


def test_overall_is_weighted_server_side():
    ev = e.validate_generated_evaluation({
        "technical_score": 80, "completeness_score": 60, "reasoning_score": 100, "practicality_score": 40,
        "feedback": "ok"})
    assert ev["dimension_scores"]["overall"] == round(80 * .35 + 60 * .25 + 100 * .25 + 40 * .15)
    assert ev["correct"] is True


def test_adaptive_never_jumps_on_one_answer():
    assert e.adjust_difficulty("beginner", [100]) == "beginner"
    assert e.adjust_difficulty("beginner", [0]) == "beginner"
    assert e.adjust_difficulty("beginner", [90, 95]) == "intermediate"
    assert e.adjust_difficulty("intermediate", [20, 30]) == "beginner"
    assert e.adjust_difficulty("advanced", [90, 95]) == "advanced"
    assert e.adjust_difficulty("beginner", [50, 65, 80]) == "intermediate"  # steady improvement, one level only
    assert e.adjust_difficulty("beginner", [90, 40]) == "beginner"


def test_topic_plan_requires_category():
    with pytest.raises(e.PlanError):
        plan(category=None)


def test_min_two_questions_per_category_when_spreading():
    pers = {"weaknesses": [{"topic": c, "average_score": 40} for c in ("SOC", "SIEM", "Linux")],
            "recommended_topics": [], "interests": [], "topic_performance": []}
    p = plan(mode="weakness", category=None, personalization=pers, question_count=5)
    counts = {c: [s["category"] for s in p.slots].count(c) for c in p.categories}
    assert len(p.categories) == 2 and min(counts.values()) >= 2


def test_weakness_without_data_falls_back_with_note():
    p = plan(mode="weakness", category=None, personalization={"weaknesses": [], "recommended_topics": [],
                                                              "interests": [], "topic_performance": []})
    assert p.note and p.effective_mode == "personalized"


def test_scenario_and_troubleshooting_modes_fix_the_type():
    assert {s["type"] for s in plan(mode="scenario", category="SOC").slots} == {"scenario"}
    assert {s["type"] for s in plan(mode="troubleshooting", category="Linux").slots} == {"troubleshooting"}
    with pytest.raises(e.PlanError):
        plan(mode="troubleshooting", category="Threat Intelligence")


def test_command_only_for_supported_categories():
    with pytest.raises(e.PlanError):
        plan(category="Cryptography", question_type="command")
    assert {s["type"] for s in plan(category="Linux", question_type="command").slots} == {"command"}
    mixed = plan(category="Cryptography", question_count=5).slots
    assert "command" not in {s["type"] for s in mixed}


def test_random_avoids_recent_categories_and_recent_topics():
    p = plan(mode="random", category=None, question_count=4, recent_categories=["Linux", "SOC", "SIEM"],
             rng=random.Random(3))
    assert p.categories[0] not in ("Linux", "SOC", "SIEM")
    p2 = plan(category="Linux", question_count=2, recent_slugs={"linux-1"})
    assert [s["topic_slug"] for s in p2.slots] == ["linux-2", "linux-1"]


def test_limits_enforced():
    for n in (0, 11):
        with pytest.raises(e.PlanError):
            plan(question_count=n)


def test_generated_question_validation():
    good = {"question": "Q?", "type": "scenario", "ideal_steps": ["a", "b", "c"], "expected_concepts": ["x"],
            "explanation": "e", "hints": ["1", "2", "3"]}
    assert e.validate_generated_question(good, expected_type="scenario")["ideal_answer"].startswith("1. a")
    for bad in ({**good, "hints": ["1"]}, {**good, "ideal_steps": ["a"]}, {**good, "type": "short_answer"}):
        with pytest.raises(ValueError):
            e.validate_generated_question(bad, expected_type="scenario")

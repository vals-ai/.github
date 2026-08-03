from pathlib import Path


def test_retry_eval_workflows_require_a_fresh_single_task_ci_run() -> None:
    """Keep retry evaluation on the merged action and reject unsafe source runs.

    Test cases:
    - Both workflows use the merged local-service action.
    - Smoke verifies the valkyrie-ci organization.
    - Retry defaults to Valkyrie dev and requires one clean perfect task.
    - Postflight requires one clean result and preserves agent duration.
    """
    workflows = Path(__file__).parents[1] / "workflows"
    smoke = (workflows / "benchmark-service-smoke.yaml").read_text()
    retry = (workflows / "retry-eval.yaml").read_text()

    merged_action = "vals-ai/.github/.github/actions/start-benchmark-service@main"
    assert merged_action in smoke
    assert merged_action in retry
    assert "EXPECTED_ORG_NAME: valkyrie-ci" in smoke
    assert 'payload.get("org_name") != os.environ["EXPECTED_ORG_NAME"]' in smoke
    assert "default: dev" in retry

    preflight = retry.split("- name: Validate completed run", maxsplit=1)[1].split(
        "- name: Retry evaluation", maxsplit=1
    )[0]
    postflight = retry.split("- name: Verify retried results", maxsplit=1)[1].split(
        "- name: Dump benchmark service logs", maxsplit=1
    )[0]
    for section in (preflight, postflight):
        for required_gate in (
            '.status == "FINISHED"',
            '((.benchmark_arguments.task_ids // []) | length) == 1',
            '((.evaluation_results // {}) | length) == 1',
            '((.task_errors // {}) | length) == 0',
            '((.tasks_stopped // []) | length) == 0',
            '.final_evaluation != null',
            '.final_evaluation.final_score == 100',
        ):
            assert required_gate in section

    assert "agent_run_duration" in postflight
    assert "Selected passing task" in preflight

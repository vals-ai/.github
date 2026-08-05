from pathlib import Path


def test_retry_eval_workflows_require_a_fresh_single_task_ci_run() -> None:
    """Keep retry evaluation on the merged action and reject unsafe source runs.

    Test cases:
    - Both workflows use the merged local-service action.
    - Smoke verifies the valkyrie-ci organization.
    - Smoke keeps a 45-minute default wait that callers can extend.
    - Retry defaults to Valkyrie dev and requires one clean positive-scoring task.
    - Postflight accepts a changed positive score and preserves agent duration.
    """
    workflows = Path(__file__).parents[1] / "workflows"
    smoke = (workflows / "benchmark-service-smoke.yaml").read_text()
    retry = (workflows / "retry-eval.yaml").read_text()

    merged_action = "vals-ai/.github/.github/actions/start-benchmark-service@main"
    assert merged_action in smoke
    assert merged_action in retry
    assert "EXPECTED_ORG_NAME: valkyrie-ci" in smoke
    assert 'payload.get("org_name") != os.environ["EXPECTED_ORG_NAME"]' in smoke
    assert "smoke_wait_timeout_minutes:" in smoke
    assert "SMOKE_WAIT_TIMEOUT_MINUTES: ${{ inputs.smoke_wait_timeout_minutes }}" in smoke
    assert 'wait_timeout_minutes = int(os.environ["SMOKE_WAIT_TIMEOUT_MINUTES"])' in smoke
    assert "wait_attempts = wait_timeout_minutes * 2" in smoke
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
            '((.final_evaluation.final_score | type) == "number")',
            '.final_evaluation.final_score > 0',
        ):
            assert required_gate in section

    assert "def task_positive($task_id):" in preflight
    assert "($task_result.result // {}) as $nested_result" in preflight
    assert "positive($nested_result.pass_percentage // null)" in preflight
    assert "or task_positive($task_id)" in preflight
    assert "def task_positive($task_id):" in postflight
    assert "($task_result.result // {}) as $nested_result" in postflight
    assert "positive($nested_result.pass_percentage // null)" in postflight
    assert "or task_positive($task_id)" in postflight

    assert '.final_evaluation.final_score == 100' not in retry
    assert "agent_run_duration" in postflight
    assert "client.benchmarks.tasks(run_id)" in retry
    assert "Initial score: $before_score" in preflight
    assert "Retried score: $after_score" in postflight
    assert "Selected passing task" in preflight

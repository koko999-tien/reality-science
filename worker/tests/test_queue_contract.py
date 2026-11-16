import pytest
from worker.tasks import compute_tasks
from shared.schemas.job_bundle import JobBundle


def bundle():
    return JobBundle(job_id="job-test",version_id="v1",target_entity_type="EQUATION",target_entity_id="e1",
                     expression_ast={"node_type":"constant","value":2})


def test_worker_returns_exact_input_provenance():
    job=bundle()
    result=compute_tasks.verify_equation_ast.run(job.model_dump(mode="json"))
    assert result["job_id"]==job.job_id
    assert result["version_id"]==job.version_id
    assert result["target_entity_id"]==job.target_entity_id
    assert result["bundle_sha256"]==job.fingerprint()
    assert result["state"]=="PASS"


def test_worker_rejects_task_id_mismatch_before_math(monkeypatch):
    job=bundle()
    def forbidden(*args): pytest.fail("must reject before math")
    monkeypatch.setattr(compute_tasks,"_verify_equation_ast",forbidden)
    task=compute_tasks.verify_equation_ast
    task.push_request(id="other",is_eager=False)
    try:
        with pytest.raises(ValueError,match="task ID"): task.run(job.model_dump())
    finally: task.pop_request()


def test_unexpected_engine_failure_is_not_a_scientific_finding(monkeypatch):
    def fail(*args): raise RuntimeError("synthetic engine error")
    monkeypatch.setattr(compute_tasks,"validate_ast_semantics",fail)
    with pytest.raises(RuntimeError,match="compute execution failed"):
        compute_tasks.verify_equation_ast.run(bundle().model_dump())

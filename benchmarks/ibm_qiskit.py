"""
IBM Quantum benchmark via Qiskit Runtime SamplerV2.

Authentication (IBM Cloud channel):
  IBM_QUANTUM_TOKEN    — IBM Cloud API key
  IBM_QUANTUM_INSTANCE — service instance CRN
    (crn:v1:bluemix:public:quantum-computing:us-east:a/<account>:<instance>::)

Backend: IBM_BACKEND environment variable (default: ibm_brisbane).
SDK: qiskit, qiskit-ibm-runtime

Note: Qiskit measurement bitstrings are in reversed qubit order relative to this
project's convention. Counts keys are flipped with [::-1] before comparing to
REFERENCE_TABLE.

Dry-run mode uses qiskit.primitives.StatevectorSampler — no IBM credentials needed.
"""

import importlib.metadata
import json
import os
from datetime import UTC, date, datetime

from benchmarks.circuits import REFERENCE_TABLE, build_circuit_qiskit, sample_circuits

PLATFORM = "ibm"
DRY_RUN_BACKEND = "StatevectorSimulator"

_TERMINAL_STATUSES = {"DONE", "ERROR", "CANCELLED"}


def _sdk_version() -> str:
    try:
        return importlib.metadata.version("qiskit-ibm-runtime")
    except importlib.metadata.PackageNotFoundError:
        return importlib.metadata.version("qiskit")


def submit(
    n_circuits: int = 10, shots: int = 100, dry_run: bool = False, use_simulator: bool = False
) -> dict:
    """Submit circuits and return a pending dict."""
    sampled_keys = sample_circuits(n_circuits)
    circuits = []
    for input_bits, length in sampled_keys:
        qc = build_circuit_qiskit(input_bits, length)
        qc.measure_all()
        circuits.append(qc)

    sdk_ver = _sdk_version()

    if dry_run:
        backend_label = DRY_RUN_BACKEND
        jobs = _run_local(circuits, shots)
    else:
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService
        from qiskit_ibm_runtime import SamplerV2 as Sampler

        token = os.environ.get("IBM_QUANTUM_TOKEN", "")
        instance = os.environ.get("IBM_QUANTUM_INSTANCE", "")
        service = QiskitRuntimeService(channel="ibm_cloud", token=token, instance=instance)
        explicit = os.environ.get("IBM_BACKEND", "")
        if explicit:
            backend = service.backend(explicit)
        else:
            backend = service.least_busy(operational=True, simulator=False)
            print(f"  Selected backend via least_busy: {backend.name}")
        backend_label = backend.name
        # translation_method="translator" bypasses the ibm_dynamic_circuits
        # plugin which is advertised by IBM backends but not loadable in this env.
        pm = generate_preset_pass_manager(
            backend=backend, optimization_level=1, translation_method="translator"
        )
        transpiled = pm.run(circuits)
        sampler = Sampler(backend)
        jobs = [sampler.run([qc], shots=shots) for qc in transpiled]

    pending = {
        "run_date": date.today().isoformat(),
        "platform": PLATFORM,
        "backend": backend_label,
        "sdk_version": sdk_ver,
        "shots": shots,
        "submitted_at": datetime.now(UTC).isoformat(),
        "dry_run": dry_run,
        "use_simulator": use_simulator,
        "jobs": [
            {"job_id": _job_id(job), "input_bits": ib, "circuit_length": cl}
            for job, (ib, cl) in zip(jobs, sampled_keys)
        ],
    }

    if dry_run:
        pending["_dry_run_results"] = _extract_results(pending, jobs)

    return pending


def _run_local(circuits: list, shots: int) -> list:
    """Run circuits with StatevectorSampler — no IBM credentials required."""
    from qiskit.primitives import StatevectorSampler

    sampler = StatevectorSampler()
    return [sampler.run([qc], shots=shots) for qc in circuits]


def _job_id(job) -> str:
    jid = job.job_id()
    return jid() if callable(jid) else jid


def _counts_from_result(pub_result) -> dict[str, int]:
    """Extract counts from a PrimitiveResult pub, reversing Qiskit's bit order."""
    bit_array = pub_result.data.meas
    return {bs[::-1]: cnt for bs, cnt in bit_array.get_counts().items()}


def _extract_results(pending: dict, jobs: list) -> list[dict]:
    results = []
    for job_meta, job in zip(pending["jobs"], jobs):
        pub_result = job.result()[0]
        counts = _counts_from_result(pub_result)

        correct = REFERENCE_TABLE[(job_meta["input_bits"], job_meta["circuit_length"])]
        success_prob = counts.get(correct, 0) / pending["shots"]

        results.append({
            "run_date": pending["run_date"],
            "platform": pending["platform"],
            "backend": pending["backend"],
            "input_bits": job_meta["input_bits"],
            "circuit_length": job_meta["circuit_length"],
            "shots": pending["shots"],
            "counts_json": json.dumps(counts),
            "success_probability": round(success_prob, 4),
            "job_id": job_meta["job_id"],
            "job_start_time": None,
            "job_end_time": None,
            "sdk_version": pending["sdk_version"],
            "notes": _notes(pending),
        })
    return results


def _notes(pending: dict) -> str:
    if pending.get("dry_run"):
        return "dry_run"
    if pending.get("use_simulator"):
        return "simulator"
    return ""


def collect(pending: dict) -> list[dict] | None:
    """
    Check job status. Returns list of result dicts if all jobs complete,
    None if still waiting, raises RuntimeError on failure.
    """
    if "_dry_run_results" in pending:
        return pending["_dry_run_results"]

    from qiskit_ibm_runtime import QiskitRuntimeService

    token = os.environ.get("IBM_QUANTUM_TOKEN", "")
    instance = os.environ.get("IBM_QUANTUM_INSTANCE", "")
    service = QiskitRuntimeService(channel="ibm_cloud", token=token, instance=instance)

    retrieved = [service.job(j["job_id"]) for j in pending["jobs"]]
    statuses = [str(job.status()) for job in retrieved]

    failed = [
        jmeta["job_id"]
        for jmeta, status in zip(pending["jobs"], statuses)
        if status in ("ERROR", "CANCELLED")
    ]
    if failed:
        raise RuntimeError(f"IBM jobs failed/cancelled: {failed}")

    still_pending = [
        jmeta["job_id"]
        for jmeta, status in zip(pending["jobs"], statuses)
        if status not in _TERMINAL_STATUSES
    ]
    if still_pending:
        print(f"  {len(still_pending)}/{len(pending['jobs'])} jobs still pending.")
        return None

    print(f"  All {len(retrieved)} jobs complete. Collecting results...")
    results = []
    for job_meta, job in zip(pending["jobs"], retrieved):
        pub_result = job.result()[0]
        counts = _counts_from_result(pub_result)

        correct = REFERENCE_TABLE[(job_meta["input_bits"], job_meta["circuit_length"])]
        success_prob = counts.get(correct, 0) / pending["shots"]

        results.append({
            "run_date": pending["run_date"],
            "platform": pending["platform"],
            "backend": pending["backend"],
            "input_bits": job_meta["input_bits"],
            "circuit_length": job_meta["circuit_length"],
            "shots": pending["shots"],
            "counts_json": json.dumps(counts),
            "success_probability": round(success_prob, 4),
            "job_id": job_meta["job_id"],
            "job_start_time": None,
            "job_end_time": None,
            "sdk_version": pending["sdk_version"],
            "notes": _notes(pending),
        })
    return results

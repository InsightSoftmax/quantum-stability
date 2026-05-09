"""
IBM Pittsburgh (Heron r3, 156 qubits) via Qiskit Runtime.
Instance: pay-as-you-go (us-east). Credentials via IBM_QUANTUM_INSTANCE_PAYG env var.
"""
import os
import benchmarks.ibm_qiskit as _base

PLATFORM = "ibm_pittsburgh"
_BACKEND = "ibm_pittsburgh"
_INSTANCE_ENV = "IBM_QUANTUM_INSTANCE_PAYG"


def _setup():
    os.environ.setdefault("IBM_BACKEND", _BACKEND)
    instance = os.environ.get(_INSTANCE_ENV, "")
    if instance:
        os.environ["IBM_QUANTUM_INSTANCE"] = instance


def _patch(data):
    if isinstance(data, dict):
        data["platform"] = PLATFORM
    elif isinstance(data, list):
        for r in data:
            r["platform"] = PLATFORM
    return data


def submit(n_circuits=10, shots=100, dry_run=False, use_simulator=False):
    _setup()
    return _patch(_base.submit(n_circuits, shots, dry_run, use_simulator))


def collect(pending):
    _setup()
    results = _base.collect(pending)
    return _patch(results) if results is not None else None

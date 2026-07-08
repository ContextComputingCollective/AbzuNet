#!/usr/bin/env python3
"""Compile the HHL OpenQASM 3 circuit and run it on IBM Qiskit Aer."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from importlib import metadata
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QASM = PROJECT_ROOT / "circuits" / "hhl_sparse_hermitian_decomposition.qasm"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "hhl_ibm_aer_result.json"
DEFAULT_COMPILED_QASM = PROJECT_ROOT / "outputs" / "hhl_ibm_aer_transpiled.qasm"


def package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not-installed"


def rounded_probabilities(probabilities: Mapping[str, float]) -> dict[str, float]:
    return {
        bitstring: round(probability, 12)
        for bitstring, probability in sorted(probabilities.items())
        if probability > 1e-12
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile the OpenQASM 3.0 HHL sparse Hermitian decomposition "
            "circuit and submit it to the IBM Qiskit Aer simulator."
        )
    )
    parser.add_argument("--qasm", type=Path, default=DEFAULT_QASM)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--compiled-qasm", type=Path, default=DEFAULT_COMPILED_QASM)
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=7331)
    return parser.parse_args()


def postselect_one_count(counts: Mapping[str, int]) -> int:
    return sum(count for bitstring, count in counts.items() if bitstring.replace(" ", "") == "1")


def main() -> None:
    args = parse_args()
    qasm_path = args.qasm.resolve()
    output_path = args.output.resolve()
    compiled_qasm_path = args.compiled_qasm.resolve()

    try:
        from qiskit import qasm3, transpile
        from qiskit_aer import AerSimulator
    except ImportError as exc:
        raise SystemExit(
            "Missing IBM simulator dependencies. Install them with:\n"
            "  python -m pip install -r requirements.txt"
        ) from exc

    qasm_source = qasm_path.read_text(encoding="utf-8")
    circuit = qasm3.loads(qasm_source)

    unitary_circuit = circuit.remove_final_measurements(inplace=False)
    state_backend = AerSimulator(method="statevector", seed_simulator=args.seed)
    compiled_unitary_circuit = transpile(
        unitary_circuit,
        backend=state_backend,
        optimization_level=2,
        seed_transpiler=args.seed,
    )
    statevector_job_circuit = compiled_unitary_circuit.copy()
    statevector_job_circuit.save_statevector()
    state_result = state_backend.run(statevector_job_circuit).result()
    statevector = state_result.get_statevector(statevector_job_circuit)
    probabilities = statevector.probabilities_dict()

    shot_backend = AerSimulator(seed_simulator=args.seed)
    compiled_measurement_circuit = transpile(
        circuit,
        backend=shot_backend,
        optimization_level=2,
        seed_transpiler=args.seed,
    )
    shot_result = shot_backend.run(compiled_measurement_circuit, shots=args.shots).result()
    counts = dict(sorted(shot_result.get_counts(compiled_measurement_circuit).items()))
    ancilla_one_count = postselect_one_count(counts)
    ancilla_one_probability = ancilla_one_count / args.shots if args.shots else 0.0

    payload: dict[str, Any] = {
        "provider": "IBM Quantum / Qiskit",
        "simulator": "qiskit-aer AerSimulator",
        "algorithm": "HHL sparse Hermitian matrix decomposition",
        "system": {
            "matrix": "diag(1, 2)",
            "right_hand_side": "|0>",
            "post_selection": "ancilla c[0] == 1",
        },
        "qasm_source": str(qasm_path),
        "shots": args.shots,
        "seed": args.seed,
        "versions": {
            "qiskit": package_version("qiskit"),
            "qiskit-aer": package_version("qiskit-aer"),
            "qiskit-qasm3-import": package_version("qiskit-qasm3-import"),
        },
        "source_circuit": {
            "qubits": circuit.num_qubits,
            "classical_bits": circuit.num_clbits,
            "depth": circuit.depth(),
            "operations": dict(circuit.count_ops()),
        },
        "compiled_unitary_circuit": {
            "backend": state_backend.name,
            "depth": compiled_unitary_circuit.depth(),
            "operations": dict(compiled_unitary_circuit.count_ops()),
            "qasm3_output": str(compiled_qasm_path),
        },
        "statevector_job_circuit": {
            "backend": state_backend.name,
            "depth": statevector_job_circuit.depth(),
            "operations": dict(statevector_job_circuit.count_ops()),
        },
        "compiled_measurement_circuit": {
            "backend": shot_backend.name,
            "depth": compiled_measurement_circuit.depth(),
            "operations": dict(compiled_measurement_circuit.count_ops()),
        },
        "statevector_probabilities_before_measurement": rounded_probabilities(probabilities),
        "measurement_counts": counts,
        "post_selection": {
            "classical_condition": "c[0] == 1",
            "ancilla_one_count": ancilla_one_count,
            "ancilla_one_probability": round(ancilla_one_probability, 12),
        },
    }

    compiled_qasm_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_qasm_path.write_text(qasm3.dumps(compiled_unitary_circuit), encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("QASM 3.0 source compiled successfully.")
    print(f"Submitted to {payload['simulator']} ({payload['provider']}).")
    print(f"Source depth: {payload['source_circuit']['depth']}")
    print(f"Compiled unitary depth: {payload['compiled_unitary_circuit']['depth']}")
    print(f"Compiled measurement depth: {payload['compiled_measurement_circuit']['depth']}")
    print("Statevector probabilities before ancilla measurement:")
    for bitstring, probability in payload["statevector_probabilities_before_measurement"].items():
        print(f"  {bitstring}: {probability:.12f}")
    print(f"Shot counts ({args.shots} shots):")
    for bitstring, count in counts.items():
        print(f"  {bitstring}: {count}")
    print(
        "Post-selection P(c[0] == 1): "
        f"{payload['post_selection']['ancilla_one_probability']:.12f}"
    )
    print(f"Wrote compiled QASM 3.0: {compiled_qasm_path}")
    print(f"Wrote run artifact: {output_path}")


if __name__ == "__main__":
    main()

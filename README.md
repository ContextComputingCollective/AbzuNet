# AbzuNet
HHL Algorithm based Hermitian Matrix Decomposition

## HHL OpenQASM 3 simulation

This checkout includes an OpenQASM 3.0 HHL circuit for a 2x2 sparse Hermitian
system, `A = diag(1, 2)` with `b = |0>`, plus a runner that compiles the circuit
with IBM Qiskit, transpiles it for Qiskit Aer, and submits it to the local Aer
simulator.

```bash
/Users/gokulalex/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/run_hhl_ibm_aer.py
```

The default run writes:

- `outputs/hhl_ibm_aer_transpiled.qasm` with the OpenQASM 3.0 circuit emitted
  after Qiskit transpilation of the pre-measurement unitary circuit.
- `outputs/hhl_ibm_aer_result.json` with source circuit metrics, compiled
  simulator metrics, statevector probabilities before ancilla measurement,
  sampled ancilla shot counts, and the post-selection probability for
  `c[0] == 1`.

OPENQASM 3.0;
include "stdgates.inc";

// HHL Algorithm Circuit for Sparse Hermitian Matrix Decomposition
// Solves A|x> = |b> where A is a Hermitian matrix
// For a 2x2 system A = diag(1, 2) with eigenvalues 1 and 2, b = |0>

// ============================================================
// Gate Definitions
// ============================================================

// Controlled rotation for eigenvalue inversion
gate crz_conditional(theta) control, target {
    cry(theta) control, target;
}

// ============================================================
// Main Circuit
// ============================================================

qubit[2] clk;      // Clock register for Quantum Phase Estimation (2 qubits)
qubit[1] sys;      // System register for vector b (1 qubit)
qubit[1] anc;      // Ancilla qubit for conditional rotation
bit[1] c;          // Classical register for measurement

// ============================================================
// STEP 2: Quantum Phase Estimation (QPE)
// ============================================================
h clk[0];
h clk[1];

// Controlled-U operations: A = diag(1, 2)
cu(0.5, 1, 0, 0) clk[1], sys[0];    // most significant qubit
cu(0.25, 1, 0, 0) clk[0], sys[0];   // least significant qubit

// Inverse Quantum Fourier Transform on clock register
h clk[0];
cphase(-0.25) clk[1], clk[0];
h clk[1];

// ============================================================
// STEP 3: Conditional Rotation (Eigenvalue Inversion)
// ============================================================

// Rotation for eigenvalue lambda=1
x clk[0];
cry(pi) clk[0], anc[0];
x clk[0];

// Rotation for eigenvalue lambda=2
cry(pi/2) clk[1], anc[0];

// ============================================================
// STEP 4: Inverse Quantum Phase Estimation (Uncompute)
// ============================================================
h clk[1];
cphase(0.25) clk[1], clk[0];
h clk[0];

// Uncompute controlled-U operations
cu(-0.5, 1, 0, 0) clk[1], sys[0];
cu(-0.25, 1, 0, 0) clk[0], sys[0];

// ============================================================
// STEP 5: Measurement and Post-Selection
// ============================================================
c[0] = measure anc[0];

"""
Hopfield Network — training and dynamics.

Switch learning rule:   change RULE (line 14)
Switch update mode:     change UPDATE_MODE (line 15)
"""

import numpy as np

# ── learning rules ────────────────────────────────────────────────────────────
STORKEY  = 'storkey'   # default — better quality near capacity
HEBBIAN  = 'hebbian'   # simpler, classical

# ── update modes ──────────────────────────────────────────────────────────────
ASYNC_CYCLIC = 1   # sequential cyclic 1→2→…→N→1  ← recommended (hardware-aligned)
ASYNC_RANDOM = 2   # sequential random permutation each sweep
SYNC         = 3   # fully synchronous — risk of 2-cycles, do NOT use for hardware

# ── top-level defaults (change these one lines to switch globally) ─────────────
RULE        = STORKEY
UPDATE_MODE = ASYNC_CYCLIC


class HopfieldNetwork:
    """
    Classical Hopfield network with bipolar {-1, +1} neurons.

    Parameters
    ----------
    N           : number of neurons
    rule        : STORKEY or HEBBIAN
    update_mode : ASYNC_CYCLIC, ASYNC_RANDOM, or SYNC
    """

    def __init__(self, N: int, rule: str = RULE, update_mode: int = UPDATE_MODE):
        self.N = N
        self.rule = rule
        self.update_mode = update_mode
        self.W = np.zeros((N, N))
        self.patterns_: np.ndarray | None = None

    # ── training ──────────────────────────────────────────────────────────────

    def train(self, patterns: np.ndarray) -> None:
        """
        Store patterns in the weight matrix.

        Parameters
        ----------
        patterns : (M, N) array with values in {-1, +1}
        """
        patterns = np.asarray(patterns, dtype=float)
        assert patterns.ndim == 2 and patterns.shape[1] == self.N
        self.patterns_ = patterns
        if self.rule == STORKEY:
            self._train_storkey(patterns)
        else:
            self._train_hebbian(patterns)

    def _train_hebbian(self, patterns: np.ndarray) -> None:
        W = sum(np.outer(p, p) for p in patterns) / self.N
        np.fill_diagonal(W, 0)
        self.W = W

    def _train_storkey(self, patterns: np.ndarray) -> None:
        N = self.N
        W = np.zeros((N, N))
        for p in patterns:
            # h_i = Σ_{j≠i} W_ij p_j  (diagonal already 0, so W @ p is exact)
            h = W @ p
            W += (np.outer(p, p) - np.outer(h, p) - np.outer(p, h)) / N
            np.fill_diagonal(W, 0)
        self.W = W

    # ── dynamics ──────────────────────────────────────────────────────────────

    def run(
        self,
        s_init: np.ndarray,
        max_sweeps: int = 20,
        rng: np.random.Generator | None = None,
    ) -> tuple[np.ndarray, int, bool]:
        """
        Run network from s_init until convergence or max_sweeps full sweeps.

        Returns
        -------
        s          : final state  {-1, +1}^N
        n_sweeps   : number of sweeps taken
        converged  : True if a fixed point was reached
        """
        s = np.array(s_init, dtype=float)
        N = self.N
        if rng is None:
            rng = np.random.default_rng()

        for sweep in range(max_sweeps):
            s_prev = s.copy()

            if self.update_mode == SYNC:
                s_new = np.sign(self.W @ s)
                # tie-break at h_i == 0: hold current state
                s_new[s_new == 0] = s_prev[s_new == 0]
                s = s_new
            else:
                order = (
                    np.arange(N)
                    if self.update_mode == ASYNC_CYCLIC
                    else rng.permutation(N)
                )
                for i in order:
                    h_i = float(self.W[i] @ s)
                    if h_i > 0:
                        s[i] = 1.0
                    elif h_i < 0:
                        s[i] = -1.0
                    # h_i == 0: hold current state (no change)

            if np.array_equal(s, s_prev):
                return s, sweep + 1, True

        return s, max_sweeps, False

    # ── utilities ─────────────────────────────────────────────────────────────

    def energy(self, s: np.ndarray) -> float:
        """Hopfield energy E = -½ sᵀWs (lower is more stable)."""
        return -0.5 * float(s @ self.W @ s)

    def is_fixed_point(self, s: np.ndarray) -> bool:
        """True if s is a fixed point of the network under the current update rule."""
        for i in range(self.N):
            h_i = float(self.W[i] @ s)
            expected = 1.0 if h_i >= 0 else -1.0
            if s[i] != expected:
                return False
        return True

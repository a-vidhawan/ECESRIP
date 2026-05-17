/**
 * hopfield.h
 * ==========
 * Shared types, constants, and API declarations for the Hopfield network
 * C simulation layer.
 *
 * Neuron convention
 * -----------------
 * Neurons use BIPOLAR states:  s ∈ {-1, +1}.
 * The weight matrix W is (N×N), stored row-major, with zero diagonal.
 *
 * Memory layout
 * -------------
 * All arrays are heap-allocated.  Use hopfield_net_create() / hopfield_net_free().
 *
 * Thread safety
 * -------------
 * These functions are NOT thread-safe.  If you parallelize the simulation,
 * provide external synchronization.
 */

#pragma once

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* -------------------------------------------------------------------------
 * Types
 * ---------------------------------------------------------------------- */

/** Neuron state: bipolar ∈ {-1, +1}.  Stored as int8_t for cache efficiency. */
typedef int8_t  hop_state_t;

/** Weight type: floating-point for maximum precision during training. */
typedef double  hop_weight_t;

/** Bitmask pattern (for N ≤ 64 fast path). */
typedef uint64_t hop_mask_t;

/**
 * HopfieldNet — the main network structure.
 *
 * Members should be treated as opaque outside this header.
 * Use the accessor macros / functions below.
 */
typedef struct {
    int            N;          /**< Number of neurons.                      */
    hop_weight_t  *W;          /**< Weight matrix, row-major, size N×N.     */
    hop_state_t   *state;      /**< Current state vector, length N.         */
    int            n_patterns; /**< Number of stored patterns.              */
    hop_state_t  **patterns;   /**< Array of stored patterns (for recall diagnostics). */
} HopfieldNet;


/* -------------------------------------------------------------------------
 * Lifecycle
 * ---------------------------------------------------------------------- */

/**
 * Allocate and initialise a zeroed HopfieldNet with N neurons.
 * Returns NULL on allocation failure.
 */
HopfieldNet *hopfield_net_create(int N);

/**
 * Free all memory owned by net.
 */
void hopfield_net_free(HopfieldNet *net);


/* -------------------------------------------------------------------------
 * Weight access macros
 * ---------------------------------------------------------------------- */

/** Read weight W[i][j]. */
#define HOP_W(net, i, j)   ((net)->W[(i) * (net)->N + (j)])


/* -------------------------------------------------------------------------
 * Training
 * ---------------------------------------------------------------------- */

/**
 * Hebbian (outer-product) learning.
 *
 *   W ← (1/N) Σ_μ  ξ^μ (ξ^μ)ᵀ    (diagonal zeroed)
 *
 * @param net       Network to train.
 * @param patterns  Array of P patterns, each of length N, entries ±1.
 * @param P         Number of patterns.
 */
void hopfield_train_hebbian(HopfieldNet *net,
                            const hop_state_t *const *patterns,
                            int P);

/**
 * Storkey learning rule (higher capacity, iterative update).
 *
 * @param net       Network to train.
 * @param patterns  Array of P patterns.
 * @param P         Number of patterns.
 */
void hopfield_train_storkey(HopfieldNet *net,
                            const hop_state_t *const *patterns,
                            int P);

/**
 * Save the weight matrix to a plain-text file (CSV, double precision).
 * Returns 0 on success, non-zero on error.
 */
int hopfield_weights_save(const HopfieldNet *net, const char *path);

/**
 * Load weights from a file previously saved by hopfield_weights_save().
 * Returns 0 on success, non-zero on error.
 */
int hopfield_weights_load(HopfieldNet *net, const char *path);


/* -------------------------------------------------------------------------
 * Update rules
 * ---------------------------------------------------------------------- */

/**
 * Apply one asynchronous update step to neuron i.
 * Updates net->state[i] in place.
 */
void hopfield_update_neuron(HopfieldNet *net, int i);

/**
 * Run async updates for `steps` total neuron selections (random order).
 * Uses a simple LCG RNG seeded with `seed`.
 */
void hopfield_run_async(HopfieldNet *net, int steps, uint32_t seed);

/**
 * Apply one full synchronous update: all neurons updated simultaneously
 * from the current state.
 * Returns 1 if the state changed, 0 if it was already a fixed point.
 */
int hopfield_run_sync_step(HopfieldNet *net);

/**
 * Run synchronous updates until a fixed point or max_iters is reached.
 * Returns the number of iterations executed.
 */
int hopfield_run_sync(HopfieldNet *net, int max_iters);


/* -------------------------------------------------------------------------
 * Diagnostics
 * ---------------------------------------------------------------------- */

/**
 * Lyapunov energy  E = -½ sᵀ W s.
 * Guaranteed non-increasing under asynchronous updates.
 */
double hopfield_energy(const HopfieldNet *net);

/**
 * Overlap  m_μ = (1/N) ξ^μ · s  for stored pattern μ.
 * Values close to ±1 indicate (non-)recall.
 */
double hopfield_overlap(const HopfieldNet *net, int mu);

/**
 * Print state and energy to stdout.
 */
void hopfield_print_state(const HopfieldNet *net);


/* -------------------------------------------------------------------------
 * Utility
 * ---------------------------------------------------------------------- */

/**
 * Allocate a single pattern array (length N, entries ±1).
 * Caller must free() the result.
 */
hop_state_t *hopfield_pattern_alloc(int N);

/**
 * Generate P random bipolar patterns.
 * Returns a heap-allocated array of P pointers; each pointer owns N bytes.
 * Caller must free each pattern and then the array.
 */
hop_state_t **hopfield_patterns_random(int N, int P, uint32_t seed);

/**
 * Free the pattern array returned by hopfield_patterns_random().
 */
void hopfield_patterns_free(hop_state_t **patterns, int P);

/**
 * Copy pattern src (length N) into dst, then flip `n_flips` random bits.
 * Used to generate noisy probes for recall testing.
 */
void hopfield_pattern_corrupt(hop_state_t *dst,
                               const hop_state_t *src,
                               int N,
                               int n_flips,
                               uint32_t seed);

#ifdef __cplusplus
}
#endif

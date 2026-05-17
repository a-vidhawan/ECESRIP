/**
 * hopfield_sim.c
 * ==============
 * Network simulation (update rules, energy, diagnostics) and main() demo.
 *
 * Build:  make  (see Makefile)
 * Run:    ./hopfield_sim [--N 8] [--P 3] [--rule hebbian|storkey] [--seed 42]
 */

#include "hopfield.h"

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


/* =========================================================================
 * Update rules
 * ====================================================================== */

void hopfield_update_neuron(HopfieldNet *net, int i)
{
    int N = net->N;
    double h = 0.0;
    for (int j = 0; j < N; j++)
        h += HOP_W(net, i, j) * (double)net->state[j];
    net->state[i] = (h >= 0.0) ? 1 : -1;
}

void hopfield_run_async(HopfieldNet *net, int steps, uint32_t seed)
{
    uint32_t rng = seed ? seed : 1u;
    int N = net->N;

    for (int t = 0; t < steps; t++) {
        /* Random neuron index via LCG */
        rng = rng * 1664525u + 1013904223u;
        int i = (int)(rng % (uint32_t)N);
        hopfield_update_neuron(net, i);
    }
}

int hopfield_run_sync_step(HopfieldNet *net)
{
    int N = net->N;
    hop_state_t *new_state = (hop_state_t *)malloc((size_t)N * sizeof(hop_state_t));
    assert(new_state);

    for (int i = 0; i < N; i++) {
        double h = 0.0;
        for (int j = 0; j < N; j++)
            h += HOP_W(net, i, j) * (double)net->state[j];
        new_state[i] = (h >= 0.0) ? 1 : -1;
    }

    int changed = (memcmp(net->state, new_state, (size_t)N) != 0);
    memcpy(net->state, new_state, (size_t)N * sizeof(hop_state_t));
    free(new_state);
    return changed;
}

int hopfield_run_sync(HopfieldNet *net, int max_iters)
{
    for (int t = 0; t < max_iters; t++) {
        if (!hopfield_run_sync_step(net))
            return t + 1;   /* converged at iteration t+1 */
    }
    return max_iters;       /* did not converge */
}


/* =========================================================================
 * Diagnostics
 * ====================================================================== */

double hopfield_energy(const HopfieldNet *net)
{
    int N = net->N;
    double E = 0.0;
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++)
            E -= HOP_W(net, i, j)
                 * (double)net->state[i]
                 * (double)net->state[j];
    return 0.5 * E;
}

double hopfield_overlap(const HopfieldNet *net, int mu)
{
    assert(mu >= 0 && mu < net->n_patterns);
    int N = net->N;
    double m = 0.0;
    for (int i = 0; i < N; i++)
        m += (double)net->patterns[mu][i] * (double)net->state[i];
    return m / N;
}

void hopfield_print_state(const HopfieldNet *net)
{
    int N = net->N;
    printf("State: [");
    for (int i = 0; i < N; i++)
        printf("%s%+d", (i ? " " : ""), (int)net->state[i]);
    printf("]  E=%.4f\n", hopfield_energy(net));

    for (int mu = 0; mu < net->n_patterns; mu++)
        printf("  overlap[%d] = %+.4f\n", mu, hopfield_overlap(net, mu));
}


/* =========================================================================
 * main() — demonstration / smoke test
 * ====================================================================== */

static void parse_args(int argc, char **argv,
                       int *N, int *P,
                       char rule[32], uint32_t *seed)
{
    *N = 8; *P = 3; *seed = 42;
    strcpy(rule, "hebbian");
    for (int i = 1; i < argc - 1; i++) {
        if (!strcmp(argv[i], "--N"))    *N    = atoi(argv[i+1]);
        if (!strcmp(argv[i], "--P"))    *P    = atoi(argv[i+1]);
        if (!strcmp(argv[i], "--seed")) *seed = (uint32_t)atol(argv[i+1]);
        if (!strcmp(argv[i], "--rule")) {
            strncpy(rule, argv[i+1], 31);
            rule[31] = '\0';
        }
    }
}

int main(int argc, char **argv)
{
    int N, P;
    char rule[32];
    uint32_t seed;
    parse_args(argc, argv, &N, &P, rule, &seed);

    printf("=== Hopfield Network Simulation ===\n");
    printf("  N=%d  P=%d  rule=%s  seed=%u\n\n", N, P, rule, seed);

    /* Generate patterns */
    hop_state_t **patterns = hopfield_patterns_random(N, P, seed);

    /* Train */
    HopfieldNet *net = hopfield_net_create(N);
    if (!strcmp(rule, "storkey"))
        hopfield_train_storkey(net, (const hop_state_t *const *)patterns, P);
    else
        hopfield_train_hebbian(net, (const hop_state_t *const *)patterns, P);

    /* Test recall: corrupt each pattern by 1 bit and try to recover */
    hop_state_t *probe = hopfield_pattern_alloc(N);
    for (int mu = 0; mu < P; mu++) {
        hopfield_pattern_corrupt(probe, patterns[mu], N, 1, seed + mu + 1);

        /* Load probe as initial state */
        memcpy(net->state, probe, (size_t)N * sizeof(hop_state_t));

        /* Run synchronous updates */
        int iters = hopfield_run_sync(net, 20 * N);

        /* Check match */
        int match = (memcmp(net->state, patterns[mu],
                            (size_t)N * sizeof(hop_state_t)) == 0);
        printf("Pattern %d: converged in %d iter(s)  %s  overlap=%.4f\n",
               mu, iters,
               match ? "RECALL OK" : "MISS",
               hopfield_overlap(net, mu));
    }

    free(probe);

    /* Demonstrate async update on pattern 0 with 2 flipped bits */
    printf("\n--- Async update (pattern 0, 2 flips) ---\n");
    hopfield_pattern_corrupt(net->state, patterns[0], N, 2, seed + 100);
    printf("Initial: ");
    hopfield_print_state(net);
    hopfield_run_async(net, 20 * N, seed + 200);
    printf("After %d async steps:\n", 20 * N);
    hopfield_print_state(net);

    hopfield_net_free(net);
    hopfield_patterns_free(patterns, P);
    return 0;
}

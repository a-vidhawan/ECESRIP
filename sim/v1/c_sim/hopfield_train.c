/**
 * hopfield_train.c
 * ================
 * Weight learning implementations for the Hopfield associative memory.
 *
 * See hopfield.h for the full API documentation.
 */

/* hopfield_train.c */
#include "hopfield.h"

/* Forward declaration */
static void _store_patterns(HopfieldNet *net, const hop_state_t *const *patterns, int P);

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


/* =========================================================================
 * Lifecycle
 * ====================================================================== */

HopfieldNet *hopfield_net_create(int N)
{
    assert(N >= 2);

    HopfieldNet *net = (HopfieldNet *)calloc(1, sizeof(HopfieldNet));
    if (!net) return NULL;

    net->N = N;
    net->W = (hop_weight_t *)calloc((size_t)N * N, sizeof(hop_weight_t));
    net->state = (hop_state_t *)calloc((size_t)N, sizeof(hop_state_t));

    if (!net->W || !net->state) {
        hopfield_net_free(net);
        return NULL;
    }

    /* Default initial state: all +1 */
    for (int i = 0; i < N; i++) net->state[i] = 1;

    net->n_patterns = 0;
    net->patterns   = NULL;

    return net;
}

void hopfield_net_free(HopfieldNet *net)
{
    if (!net) return;
    free(net->W);
    free(net->state);
    if (net->patterns) {
        hopfield_patterns_free(net->patterns, net->n_patterns);
    }
    free(net);
}


/* =========================================================================
 * Hebbian learning
 * ====================================================================== */

void hopfield_train_hebbian(HopfieldNet *net,
                            const hop_state_t *const *patterns,
                            int P)
{
    int N = net->N;

    /* Zero weight matrix */
    memset(net->W, 0, (size_t)N * N * sizeof(hop_weight_t));

    /* W += (1/N) * xi * xi^T for each pattern xi */
    for (int mu = 0; mu < P; mu++) {
        const hop_state_t *xi = patterns[mu];
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                HOP_W(net, i, j) +=
                    (hop_weight_t)xi[i] * (hop_weight_t)xi[j];
            }
        }
    }

    /* Scale and zero diagonal */
    double scale = 1.0 / N;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            HOP_W(net, i, j) *= scale;
        }
        HOP_W(net, i, i) = 0.0;
    }

    /* Store pattern pointers for diagnostics */
    _store_patterns(net, patterns, P);
}


/* =========================================================================
 * Storkey learning
 * ====================================================================== */

void hopfield_train_storkey(HopfieldNet *net,
                             const hop_state_t *const *patterns,
                             int P)
{
    int N = net->N;
    memset(net->W, 0, (size_t)N * N * sizeof(hop_weight_t));

    /* Temporary vector for local field h */
    double *h = (double *)malloc((size_t)N * sizeof(double));
    assert(h);

    for (int mu = 0; mu < P; mu++) {
        const hop_state_t *xi = patterns[mu];

        /* h_i = sum_{k≠i} W_ik * xi_k */
        for (int i = 0; i < N; i++) {
            double acc = 0.0;
            for (int k = 0; k < N; k++) {
                if (k != i)
                    acc += HOP_W(net, i, k) * (double)xi[k];
            }
            h[i] = acc;
        }

        /* dW_ij = (1/N)*(xi_i*xi_j - h_i*xi_j - xi_i*h_j) */
        double inv_N = 1.0 / N;
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                double dW = ((double)xi[i] * (double)xi[j]
                             - h[i] * (double)xi[j]
                             - (double)xi[i] * h[j]) * inv_N;
                HOP_W(net, i, j) += dW;
            }
        }
        /* Zero diagonal */
        for (int i = 0; i < N; i++)
            HOP_W(net, i, i) = 0.0;
    }

    free(h);
    _store_patterns(net, patterns, P);
}


/* =========================================================================
 * Weight I/O
 * ====================================================================== */

int hopfield_weights_save(const HopfieldNet *net, const char *path)
{
    FILE *fp = fopen(path, "w");
    if (!fp) return -1;

    int N = net->N;
    fprintf(fp, "# HopfieldNet weights  N=%d\n", N);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            fprintf(fp, "%.17g", HOP_W(net, i, j));
            if (j < N - 1) fputc(',', fp);
        }
        fputc('\n', fp);
    }
    fclose(fp);
    return 0;
}

int hopfield_weights_load(HopfieldNet *net, const char *path)
{
    FILE *fp = fopen(path, "r");
    if (!fp) return -1;

    int N = net->N;
    char line[4096];
    int row = 0;

    while (fgets(line, sizeof(line), fp) && row < N) {
        if (line[0] == '#') continue;
        char *p = line;
        for (int j = 0; j < N; j++) {
            HOP_W(net, row, j) = strtod(p, &p);
            if (*p == ',') p++;
        }
        row++;
    }
    fclose(fp);
    return (row == N) ? 0 : -1;
}


/* =========================================================================
 * Utility (internal + public)
 * ====================================================================== */

/* Internal helper: copy pattern pointers into net->patterns */
static void _store_patterns(HopfieldNet *net,
                     const hop_state_t *const *patterns,
                     int P)
{
    if (net->patterns) {
        hopfield_patterns_free(net->patterns, net->n_patterns);
    }
    net->n_patterns = P;
    net->patterns = (hop_state_t **)malloc((size_t)P * sizeof(hop_state_t *));
    assert(net->patterns);

    for (int mu = 0; mu < P; mu++) {
        net->patterns[mu] = (hop_state_t *)malloc((size_t)net->N);
        assert(net->patterns[mu]);
        memcpy(net->patterns[mu], patterns[mu], (size_t)net->N);
    }
}

hop_state_t *hopfield_pattern_alloc(int N)
{
    return (hop_state_t *)malloc((size_t)N * sizeof(hop_state_t));
}

/* Simple LCG for reproducible random patterns */
static uint32_t lcg_next(uint32_t *state)
{
    *state = *state * 1664525u + 1013904223u;
    return *state;
}

hop_state_t **hopfield_patterns_random(int N, int P, uint32_t seed)
{
    hop_state_t **pats = (hop_state_t **)malloc((size_t)P * sizeof(hop_state_t *));
    assert(pats);
    uint32_t rng = seed ? seed : 1u;

    for (int mu = 0; mu < P; mu++) {
        pats[mu] = (hop_state_t *)malloc((size_t)N * sizeof(hop_state_t));
        assert(pats[mu]);
        for (int i = 0; i < N; i++) {
            pats[mu][i] = (lcg_next(&rng) & 1u) ? 1 : -1;
        }
    }
    return pats;
}

void hopfield_patterns_free(hop_state_t **patterns, int P)
{
    if (!patterns) return;
    for (int mu = 0; mu < P; mu++) free(patterns[mu]);
    free(patterns);
}

void hopfield_pattern_corrupt(hop_state_t *dst,
                               const hop_state_t *src,
                               int N,
                               int n_flips,
                               uint32_t seed)
{
    memcpy(dst, src, (size_t)N * sizeof(hop_state_t));
    uint32_t rng = seed ? seed : 1u;

    /* Fisher-Yates partial shuffle to pick n_flips distinct indices */
    int *idx = (int *)malloc((size_t)N * sizeof(int));
    assert(idx);
    for (int i = 0; i < N; i++) idx[i] = i;

    int flips = (n_flips < N) ? n_flips : N;
    for (int k = 0; k < flips; k++) {
        int j = k + (int)(lcg_next(&rng) % (uint32_t)(N - k));
        int tmp = idx[k]; idx[k] = idx[j]; idx[j] = tmp;
        dst[idx[k]] = -dst[idx[k]];
    }
    free(idx);
}

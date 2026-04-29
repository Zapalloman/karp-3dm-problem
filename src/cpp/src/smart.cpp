// smart.cpp — SMART backtracking algorithm for 3DM.
//
// Implements exactly the pseudocode in docs/ALGORITHMS.md (solveSmart / recur)
// with MRV + bitmask forward-checking + upper-bound pruning + discarded tracking.
//
// Key decisions (hand-off from Phase 4, replicated literally):
//   - nodes++ is the FIRST instruction of recur().
//   - Four bitmasks per dimension: usedX/Y/Z and discX/Y/Z.
//     "Free and not discarded" = ~(used | disc) & mask_n.
//   - MRV iterates 3 dimensions in 3 separate loops (not interleaved).
//   - Upper-bound check: |chosen| + min(freeX, freeY, freeZ) <= |best| → prune.
//     (strictly <=, not <; we prune even ties because we want STRICTLY better.)
//   - XOR to undo bit-setting on backtrack.

#include "smart.hpp"
#include "bitmask.hpp"

#include <algorithm>
#include <atomic>
#include <vector>
#include <climits>

namespace tdm {

// ------------------------------------------------------------------
// Build index: inX[x] = list of triple indices containing element x in X.
// ------------------------------------------------------------------
static void build_index(const Instance& inst,
                         std::vector<std::vector<int>>& in_x,
                         std::vector<std::vector<int>>& in_y,
                         std::vector<std::vector<int>>& in_z)
{
    int n = inst.n;
    in_x.assign(n, {});
    in_y.assign(n, {});
    in_z.assign(n, {});
    for (int i = 0; i < inst.m; ++i) {
        const Triple& t = inst.triples[i];
        in_x[t.x].push_back(i);
        in_y[t.y].push_back(i);
        in_z[t.z].push_back(i);
    }
}

// ------------------------------------------------------------------
// SmartState
// ------------------------------------------------------------------
struct SmartState {
    const Instance* inst;
    std::atomic<bool>* aborted;
    long long* nodes;

    const std::vector<std::vector<int>>* in_x;
    const std::vector<std::vector<int>>* in_y;
    const std::vector<std::vector<int>>* in_z;

    Bitmask used_x, used_y, used_z;
    Bitmask disc_x, disc_y, disc_z;

    std::vector<int> chosen;
    std::vector<int> best;
};

// ------------------------------------------------------------------
// triple_available: all three elements are NOT used (disc doesn't block usage).
// ------------------------------------------------------------------
static inline bool triple_available(const SmartState& st, int i)
{
    const Triple& t = st.inst->triples[i];
    return !st.used_x.test(t.x) && !st.used_y.test(t.y) && !st.used_z.test(t.z);
}

// ------------------------------------------------------------------
// pickMRV: iterate all 3 dimensions and find the free element with the
// fewest available triples.
//
// Returns: dim (0/1/2), elem index, count, candidates vector.
// If no free element exists, returns dim = -1.
// ------------------------------------------------------------------
static void pick_mrv(const SmartState& st,
                     int& out_dim,
                     int& out_elem,
                     int& out_count,
                     std::vector<int>& out_candidates)
{
    int n = st.inst->n;
    out_dim   = -1;
    out_elem  = -1;
    out_count = INT_MAX;
    out_candidates.clear();

    // Dimension 0 (X)
    for (int e = 0; e < n; ++e) {
        if (st.used_x.test(e) || st.disc_x.test(e)) continue; // not free
        int cnt = 0;
        for (int i : (*st.in_x)[e]) {
            if (triple_available(st, i)) ++cnt;
        }
        if (cnt < out_count) {
            out_count = cnt;
            out_dim   = 0;
            out_elem  = e;
        }
    }

    // Dimension 1 (Y)
    for (int e = 0; e < n; ++e) {
        if (st.used_y.test(e) || st.disc_y.test(e)) continue;
        int cnt = 0;
        for (int i : (*st.in_y)[e]) {
            if (triple_available(st, i)) ++cnt;
        }
        if (cnt < out_count) {
            out_count = cnt;
            out_dim   = 1;
            out_elem  = e;
        }
    }

    // Dimension 2 (Z)
    for (int e = 0; e < n; ++e) {
        if (st.used_z.test(e) || st.disc_z.test(e)) continue;
        int cnt = 0;
        for (int i : (*st.in_z)[e]) {
            if (triple_available(st, i)) ++cnt;
        }
        if (cnt < out_count) {
            out_count = cnt;
            out_dim   = 2;
            out_elem  = e;
        }
    }

    if (out_dim == -1) return; // no free elements

    // Build candidates list for the chosen (dim, elem).
    if (out_dim == 0) {
        for (int i : (*st.in_x)[out_elem]) {
            if (triple_available(st, i)) out_candidates.push_back(i);
        }
    } else if (out_dim == 1) {
        for (int i : (*st.in_y)[out_elem]) {
            if (triple_available(st, i)) out_candidates.push_back(i);
        }
    } else {
        for (int i : (*st.in_z)[out_elem]) {
            if (triple_available(st, i)) out_candidates.push_back(i);
        }
    }
}

// ------------------------------------------------------------------
// Core recursive function — maps 1-to-1 to the pseudocode.
// ------------------------------------------------------------------
static void recur_smart(SmartState& st)
{
    // nodes++ is FIRST (see hand-off).
    ++(*st.nodes);

    if (st.aborted->load(std::memory_order_relaxed)) return;

    // --- 1) Upper-bound pruning ---
    // free = not used AND not discarded
    int free_x = st.used_x.free_count_combined(st.disc_x);
    int free_y = st.used_y.free_count_combined(st.disc_y);
    int free_z = st.used_z.free_count_combined(st.disc_z);
    int upper  = (int)st.chosen.size() + std::min({free_x, free_y, free_z});
    if (upper <= (int)st.best.size()) return;

    // --- 2) MRV ---
    int  mrv_dim, mrv_elem, mrv_count;
    std::vector<int> candidates;
    pick_mrv(st, mrv_dim, mrv_elem, mrv_count, candidates);

    // No free element → current partial is maximal locally.
    if (mrv_dim == -1) {
        if ((int)st.chosen.size() > (int)st.best.size()) {
            st.best = st.chosen;
        }
        return;
    }

    int e = mrv_elem;

    // --- 3) MRV element has 0 available triples: discard it ---
    if (mrv_count == 0) {
        if (mrv_dim == 0) {
            st.disc_x.set(e);
            recur_smart(st);
            st.disc_x.xor_bit(e);
        } else if (mrv_dim == 1) {
            st.disc_y.set(e);
            recur_smart(st);
            st.disc_y.xor_bit(e);
        } else {
            st.disc_z.set(e);
            recur_smart(st);
            st.disc_z.xor_bit(e);
        }
        return;
    }

    // --- 4) Try each available triple for (mrv_dim, e) ---
    for (int i : candidates) {
        if (st.aborted->load(std::memory_order_relaxed)) return;
        const Triple& t = st.inst->triples[i];
        st.used_x.set(t.x);
        st.used_y.set(t.y);
        st.used_z.set(t.z);
        st.chosen.push_back(i);

        recur_smart(st);

        st.chosen.pop_back();
        st.used_x.xor_bit(t.x);
        st.used_y.xor_bit(t.y);
        st.used_z.xor_bit(t.z);
    }

    // --- 5) "Do not match e": discard e in its dimension ---
    if (mrv_dim == 0) {
        st.disc_x.set(e);
        recur_smart(st);
        st.disc_x.xor_bit(e);
    } else if (mrv_dim == 1) {
        st.disc_y.set(e);
        recur_smart(st);
        st.disc_y.xor_bit(e);
    } else {
        st.disc_z.set(e);
        recur_smart(st);
        st.disc_z.xor_bit(e);
    }
}

// ------------------------------------------------------------------
// Public entry point
// ------------------------------------------------------------------
Matching solve_smart(const Instance& inst,
                     std::atomic<bool>& aborted,
                     long long& nodes_out)
{
    std::vector<std::vector<int>> in_x, in_y, in_z;
    build_index(inst, in_x, in_y, in_z);

    SmartState st;
    st.inst    = &inst;
    st.aborted = &aborted;
    st.nodes   = &nodes_out;
    st.in_x    = &in_x;
    st.in_y    = &in_y;
    st.in_z    = &in_z;
    st.used_x  = Bitmask(inst.n);
    st.used_y  = Bitmask(inst.n);
    st.used_z  = Bitmask(inst.n);
    st.disc_x  = Bitmask(inst.n);
    st.disc_y  = Bitmask(inst.n);
    st.disc_z  = Bitmask(inst.n);
    nodes_out  = 0;

    recur_smart(st);

    Matching result;
    result.indices = st.best;
    return result;
}

} // namespace tdm

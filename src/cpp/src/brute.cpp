// brute.cpp — BASE backtracking algorithm for 3DM.
//
// Implements exactly the pseudocode in docs/ALGORITHMS.md (solveBrute / recur).
// No heuristics. Complexity O(2^m).
//
// Key decisions (hand-off from Phase 4, replicated literally):
//   - nodes++ is the FIRST instruction of recur(), before the aborted check,
//     so the root node is always counted.
//   - XOR (^=) to undo bit-setting on backtrack (not AND-NOT).
//   - Bitmasks are 64-bit integers (uint64_t) for n <= 64.

#include "brute.hpp"
#include "bitmask.hpp"

#include <vector>
#include <atomic>

namespace tdm {

// ------------------------------------------------------------------
// Internal solver state (lives on the stack of solve_brute; passed by
// pointer to the nested recur function which is a plain static function).
// ------------------------------------------------------------------
struct BruteState {
    const Instance* inst;
    std::atomic<bool>* aborted;
    long long* nodes;

    // Bitmasks (one uint64_t each for n <= 64; Bitmask handles large n too).
    Bitmask used_x;
    Bitmask used_y;
    Bitmask used_z;

    std::vector<int> chosen;
    std::vector<int> best;
};

static void recur_brute(BruteState& st, int i)
{
    // nodes++ is FIRST, before the aborted check (see hand-off).
    ++(*st.nodes);

    if (st.aborted->load(std::memory_order_relaxed)) return;

    const int m = st.inst->m;

    // Base case: exhausted all triples.
    if (i == m) {
        if ((int)st.chosen.size() > (int)st.best.size()) {
            st.best = st.chosen;
        }
        return;
    }

    const Triple& t = st.inst->triples[i];

    // Branch 1: take triple i if available (all three bits are 0).
    if (!st.used_x.test(t.x) && !st.used_y.test(t.y) && !st.used_z.test(t.z)) {
        st.used_x.set(t.x);
        st.used_y.set(t.y);
        st.used_z.set(t.z);
        st.chosen.push_back(i);

        recur_brute(st, i + 1);

        st.chosen.pop_back();
        // XOR to undo (equivalent to AND-NOT since we set exactly one bit).
        st.used_x.xor_bit(t.x);
        st.used_y.xor_bit(t.y);
        st.used_z.xor_bit(t.z);
    }

    // Branch 2: skip triple i.
    recur_brute(st, i + 1);
}

Matching solve_brute(const Instance& inst,
                     std::atomic<bool>& aborted,
                     long long& nodes_out)
{
    BruteState st;
    st.inst    = &inst;
    st.aborted = &aborted;
    st.nodes   = &nodes_out;
    st.used_x  = Bitmask(inst.n);
    st.used_y  = Bitmask(inst.n);
    st.used_z  = Bitmask(inst.n);
    nodes_out  = 0;

    recur_brute(st, 0);

    Matching result;
    result.indices = st.best;
    return result;
}

} // namespace tdm

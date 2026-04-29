package com.threedm;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Brute.java — BASE backtracking algorithm for 3DM.
 *
 * Implements exactly the pseudocode in docs/ALGORITHMS.md (solveBrute / recur).
 * No heuristics. Complexity O(2^m).
 *
 * Key decisions (hand-off from Phases 4 and 5, replicated literally):
 *   - nodes is incremented as the FIRST instruction of recur(), before the
 *     aborted check, so the root node is always counted.
 *   - XOR (xorBit) to undo bit-setting on backtrack.
 *   - Bitmasks use Bitmask class (long for n<=64, long[] for n>64).
 */
public final class Brute {

    // Prevent instantiation — this is a utility class.
    private Brute() {}

    /**
     * Run the BASE backtracking algorithm.
     *
     * @param inst      the 3DM instance
     * @param aborted   flag set by timer thread to abort early
     * @param nodesOut  single-element array; nodes[0] will hold the node count
     * @return Matching with the best solution found
     */
    public static Matching solve(Instance inst, AtomicBoolean aborted, long[] nodesOut) {
        State st = new State(inst, aborted, nodesOut);
        nodesOut[0] = 0L;
        recur(st, 0);
        return new Matching(st.best.stream().mapToInt(Integer::intValue).toArray());
    }

    // ------------------------------------------------------------------
    // Internal solver state
    // ------------------------------------------------------------------
    private static final class State {
        final Instance inst;
        final AtomicBoolean aborted;
        final long[] nodes;

        final Bitmask usedX;
        final Bitmask usedY;
        final Bitmask usedZ;

        final List<Integer> chosen = new ArrayList<>();
        List<Integer> best = new ArrayList<>();

        State(Instance inst, AtomicBoolean aborted, long[] nodes) {
            this.inst    = inst;
            this.aborted = aborted;
            this.nodes   = nodes;
            this.usedX   = new Bitmask(inst.n);
            this.usedY   = new Bitmask(inst.n);
            this.usedZ   = new Bitmask(inst.n);
        }
    }

    // ------------------------------------------------------------------
    // Core recursive function — maps 1-to-1 to the pseudocode.
    // ------------------------------------------------------------------
    private static void recur(State st, int i) {
        // nodes++ is FIRST, before the aborted check (see hand-off from Phase 4/5).
        st.nodes[0]++;

        if (st.aborted.get()) return;

        // Base case: exhausted all triples.
        if (i == st.inst.m) {
            if (st.chosen.size() > st.best.size()) {
                st.best = new ArrayList<>(st.chosen);
            }
            return;
        }

        int x = st.inst.triples[i][0];
        int y = st.inst.triples[i][1];
        int z = st.inst.triples[i][2];

        // Branch 1: take triple i if available (all three bits are 0).
        if (!st.usedX.test(x) && !st.usedY.test(y) && !st.usedZ.test(z)) {
            st.usedX.set(x);
            st.usedY.set(y);
            st.usedZ.set(z);
            st.chosen.add(i);

            recur(st, i + 1);

            st.chosen.remove(st.chosen.size() - 1);
            // XOR to undo (equivalent to clear since we set exactly one bit).
            st.usedX.xorBit(x);
            st.usedY.xorBit(y);
            st.usedZ.xorBit(z);
        }

        // Branch 2: skip triple i.
        recur(st, i + 1);
    }
}

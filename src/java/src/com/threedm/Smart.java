package com.threedm;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Smart.java — SMART backtracking algorithm for 3DM.
 *
 * Implements exactly the pseudocode in docs/ALGORITHMS.md (solveSmart / recur)
 * with MRV + bitmask forward-checking + upper-bound pruning + discarded tracking.
 *
 * Key decisions (hand-off from Phases 4 and 5, replicated literally):
 *   - nodes is incremented as the FIRST instruction of recur().
 *   - Four bitmasks per dimension: usedX/Y/Z and discX/Y/Z.
 *     "Free and not discarded" = freeCountCombined(used, disc) in Bitmask.
 *   - MRV iterates 3 dimensions in 3 separate loops (not interleaved).
 *   - Upper-bound check: |chosen| + min(freeX, freeY, freeZ) <= |best| → prune.
 *     (strictly <=: prune ties because we want strictly better.)
 *   - XOR (xorBit) to undo bit-setting on backtrack.
 *   - tripleAvailable: only checks usedX/Y/Z (not disc); disc just excludes
 *     elements from the MRV free-element search.
 */
public final class Smart {

    private Smart() {}

    /**
     * Run the SMART backtracking algorithm.
     *
     * @param inst      the 3DM instance
     * @param aborted   flag set by timer thread to abort early
     * @param nodesOut  single-element array; nodesOut[0] will hold the node count
     * @return Matching with the best solution found
     */
    public static Matching solve(Instance inst, AtomicBoolean aborted, long[] nodesOut) {
        // Build index: inX[x] = list of triple indices containing x in dimension X.
        int[][] inX = new int[inst.n][];
        int[][] inY = new int[inst.n][];
        int[][] inZ = new int[inst.n][];
        buildIndex(inst, inX, inY, inZ);

        State st = new State(inst, aborted, nodesOut, inX, inY, inZ);
        nodesOut[0] = 0L;
        recur(st);
        return new Matching(st.best.stream().mapToInt(Integer::intValue).toArray());
    }

    // ------------------------------------------------------------------
    // Build inverted index
    // ------------------------------------------------------------------
    private static void buildIndex(Instance inst,
                                   int[][] inX, int[][] inY, int[][] inZ) {
        // Count occurrences per element per dimension
        int[] cntX = new int[inst.n];
        int[] cntY = new int[inst.n];
        int[] cntZ = new int[inst.n];
        for (int i = 0; i < inst.m; i++) {
            cntX[inst.triples[i][0]]++;
            cntY[inst.triples[i][1]]++;
            cntZ[inst.triples[i][2]]++;
        }
        // Allocate
        for (int e = 0; e < inst.n; e++) {
            inX[e] = new int[cntX[e]];
            inY[e] = new int[cntY[e]];
            inZ[e] = new int[cntZ[e]];
            cntX[e] = 0; cntY[e] = 0; cntZ[e] = 0;  // reuse as fill pointers
        }
        // Fill
        for (int i = 0; i < inst.m; i++) {
            int x = inst.triples[i][0];
            int y = inst.triples[i][1];
            int z = inst.triples[i][2];
            inX[x][cntX[x]++] = i;
            inY[y][cntY[y]++] = i;
            inZ[z][cntZ[z]++] = i;
        }
    }

    // ------------------------------------------------------------------
    // Internal solver state
    // ------------------------------------------------------------------
    private static final class State {
        final Instance inst;
        final AtomicBoolean aborted;
        final long[] nodes;

        final int[][] inX;
        final int[][] inY;
        final int[][] inZ;

        final Bitmask usedX, usedY, usedZ;
        final Bitmask discX, discY, discZ;

        final List<Integer> chosen = new ArrayList<>();
        List<Integer> best = new ArrayList<>();

        State(Instance inst, AtomicBoolean aborted, long[] nodes,
              int[][] inX, int[][] inY, int[][] inZ) {
            this.inst    = inst;
            this.aborted = aborted;
            this.nodes   = nodes;
            this.inX     = inX;
            this.inY     = inY;
            this.inZ     = inZ;
            this.usedX   = new Bitmask(inst.n);
            this.usedY   = new Bitmask(inst.n);
            this.usedZ   = new Bitmask(inst.n);
            this.discX   = new Bitmask(inst.n);
            this.discY   = new Bitmask(inst.n);
            this.discZ   = new Bitmask(inst.n);
        }
    }

    // ------------------------------------------------------------------
    // tripleAvailable: all three elements are NOT used (disc does not block
    // choosing a triple — disc only excludes elements from MRV selection).
    // ------------------------------------------------------------------
    private static boolean tripleAvailable(State st, int i) {
        int x = st.inst.triples[i][0];
        int y = st.inst.triples[i][1];
        int z = st.inst.triples[i][2];
        return !st.usedX.test(x) && !st.usedY.test(y) && !st.usedZ.test(z);
    }

    // ------------------------------------------------------------------
    // MRV result record (simple holder — avoids allocating a separate class)
    // ------------------------------------------------------------------
    // dim: 0=X, 1=Y, 2=Z; -1 = no free element found
    // elem: free element index
    // count: number of available triples for (dim, elem)
    // candidates: list of available triple indices for (dim, elem)
    private static int mrvDim;
    private static int mrvElem;
    private static int mrvCount;

    /**
     * Find the free element (not used, not discarded) with the fewest
     * available triples.  Store result in the static mrvDim/mrvElem/mrvCount
     * fields and return the candidates list.
     *
     * Note: Static fields are used to avoid object allocation on the hot path,
     * but this makes the method non-reentrant. That is fine because the Java
     * recursion is single-threaded.
     */
    private static List<Integer> pickMrv(State st) {
        mrvDim   = -1;
        mrvElem  = -1;
        mrvCount = Integer.MAX_VALUE;

        int n = st.inst.n;

        // Dimension 0 (X)
        for (int e = 0; e < n; e++) {
            if (st.usedX.test(e) || st.discX.test(e)) continue;
            int cnt = 0;
            for (int i : st.inX[e]) {
                if (tripleAvailable(st, i)) cnt++;
            }
            if (cnt < mrvCount) {
                mrvCount = cnt;
                mrvDim   = 0;
                mrvElem  = e;
            }
        }

        // Dimension 1 (Y)
        for (int e = 0; e < n; e++) {
            if (st.usedY.test(e) || st.discY.test(e)) continue;
            int cnt = 0;
            for (int i : st.inY[e]) {
                if (tripleAvailable(st, i)) cnt++;
            }
            if (cnt < mrvCount) {
                mrvCount = cnt;
                mrvDim   = 1;
                mrvElem  = e;
            }
        }

        // Dimension 2 (Z)
        for (int e = 0; e < n; e++) {
            if (st.usedZ.test(e) || st.discZ.test(e)) continue;
            int cnt = 0;
            for (int i : st.inZ[e]) {
                if (tripleAvailable(st, i)) cnt++;
            }
            if (cnt < mrvCount) {
                mrvCount = cnt;
                mrvDim   = 2;
                mrvElem  = e;
            }
        }

        if (mrvDim == -1) return null;  // no free element

        // Build candidates list for the chosen (dim, elem)
        List<Integer> candidates = new ArrayList<>();
        int[][] inDim = (mrvDim == 0) ? st.inX : (mrvDim == 1) ? st.inY : st.inZ;
        for (int i : inDim[mrvElem]) {
            if (tripleAvailable(st, i)) candidates.add(i);
        }
        return candidates;
    }

    // ------------------------------------------------------------------
    // Core recursive function — maps 1-to-1 to the pseudocode.
    // ------------------------------------------------------------------
    private static void recur(State st) {
        // nodes++ is FIRST (see hand-off from Phase 4/5).
        st.nodes[0]++;

        if (st.aborted.get()) return;

        // --- 1) Upper-bound pruning ---
        // free = not used AND not discarded
        int freeX = st.usedX.freeCountCombined(st.discX);
        int freeY = st.usedY.freeCountCombined(st.discY);
        int freeZ = st.usedZ.freeCountCombined(st.discZ);
        int upper = st.chosen.size() + Math.min(freeX, Math.min(freeY, freeZ));
        if (upper <= st.best.size()) return;

        // --- 2) MRV ---
        List<Integer> candidates = pickMrv(st);
        int dim   = mrvDim;
        int e     = mrvElem;
        int count = mrvCount;

        // No free element → current partial is maximal locally.
        if (dim == -1) {
            if (st.chosen.size() > st.best.size()) {
                st.best = new ArrayList<>(st.chosen);
            }
            return;
        }

        // --- 3) MRV element has 0 available triples: discard it ---
        if (count == 0) {
            if (dim == 0) {
                st.discX.set(e);
                recur(st);
                st.discX.xorBit(e);
            } else if (dim == 1) {
                st.discY.set(e);
                recur(st);
                st.discY.xorBit(e);
            } else {
                st.discZ.set(e);
                recur(st);
                st.discZ.xorBit(e);
            }
            return;
        }

        // --- 4) Try each available triple for (dim, e) ---
        for (int i : candidates) {
            if (st.aborted.get()) return;
            int x = st.inst.triples[i][0];
            int y = st.inst.triples[i][1];
            int z = st.inst.triples[i][2];
            st.usedX.set(x);
            st.usedY.set(y);
            st.usedZ.set(z);
            st.chosen.add(i);

            recur(st);

            st.chosen.remove(st.chosen.size() - 1);
            st.usedX.xorBit(x);
            st.usedY.xorBit(y);
            st.usedZ.xorBit(z);
        }

        // --- 5) "Do not match e": discard e in its dimension ---
        if (dim == 0) {
            st.discX.set(e);
            recur(st);
            st.discX.xorBit(e);
        } else if (dim == 1) {
            st.discY.set(e);
            recur(st);
            st.discY.xorBit(e);
        } else {
            st.discZ.set(e);
            recur(st);
            st.discZ.xorBit(e);
        }
    }
}

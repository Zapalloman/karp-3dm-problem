package com.threedm;

/**
 * Bitmask.java — Bitmask wrapper for n-bit sets.
 *
 * Decision (Phase 6):
 *   - n <= 64: single long word. Operations are trivially O(1).
 *   - n >  64: long[] array with ceil(n/64) words. Same interface.
 *
 * Methods: set(i), clear(i), test(i), xorBit(i), popcount(),
 *          freeCountCombined(other) which computes popcount(~(this|other) & maskN)
 *          without allocating a temporary Bitmask.
 *
 * No templates/generics — plain runtime branch on 'large' flag, just like
 * the C++ version uses a mode flag.
 */
public final class Bitmask {
    /** true when n > 64 */
    private final boolean large;
    /** number of elements (bits) */
    private final int n;

    // small path
    private long word;
    /** mask for the low n bits (only used in small path) */
    private final long maskN;

    // large path
    private long[] words;
    /** number of longs in words[] = ceil(n/64) */
    private final int numWords;

    /** Create a zero-initialized bitmask for n elements. */
    public Bitmask(int n) {
        this.n = n;
        if (n <= 64) {
            this.large = false;
            this.word = 0L;
            this.maskN = (n == 64) ? -1L : ((1L << n) - 1L);
            this.numWords = 1;
            this.words = null;
        } else {
            this.large = true;
            this.numWords = (n + 63) >>> 6;  // ceil(n/64)
            this.words = new long[numWords];
            this.maskN = 0L;  // not used in large path
            this.word = 0L;
        }
    }

    /** Set bit i to 1. */
    public void set(int i) {
        if (!large) {
            word |= (1L << i);
        } else {
            words[i >>> 6] |= (1L << (i & 63));
        }
    }

    /** Clear bit i to 0. */
    public void clear(int i) {
        if (!large) {
            word &= ~(1L << i);
        } else {
            words[i >>> 6] &= ~(1L << (i & 63));
        }
    }

    /** Test (read) bit i. */
    public boolean test(int i) {
        if (!large) {
            return ((word >>> i) & 1L) != 0;
        } else {
            return ((words[i >>> 6] >>> (i & 63)) & 1L) != 0;
        }
    }

    /**
     * Flip bit i (XOR). Used on backtrack to undo a set/clear.
     * Correct because exactly one bit is toggled at a time.
     */
    public void xorBit(int i) {
        if (!large) {
            word ^= (1L << i);
        } else {
            words[i >>> 6] ^= (1L << (i & 63));
        }
    }

    /**
     * Count set bits (popcount).
     * Uses Long.bitCount which maps to POPCNT on x86.
     */
    public int popcount() {
        if (!large) {
            return Long.bitCount(word & maskN);
        } else {
            int total = 0;
            int fullWords = n >>> 6;
            for (int w = 0; w < fullWords; w++) {
                total += Long.bitCount(words[w]);
            }
            int rem = n & 63;
            if (rem != 0) {
                long lastMask = (1L << rem) - 1L;
                total += Long.bitCount(words[fullWords] & lastMask);
            }
            return total;
        }
    }

    /**
     * Compute the number of bits that are 0 in BOTH this AND other,
     * restricted to the first n bits.
     *
     * Equivalent to popcount(~(this | other) & maskN) but without
     * allocating a temporary Bitmask.
     *
     * Used for the upper-bound computation in SMART:
     *   freeX = usedX.freeCountCombined(discX)
     */
    public int freeCountCombined(Bitmask other) {
        if (!large) {
            return Long.bitCount((~(word | other.word)) & maskN);
        } else {
            int total = 0;
            int fullWords = n >>> 6;
            for (int w = 0; w < fullWords; w++) {
                total += Long.bitCount(~(words[w] | other.words[w]));
            }
            int rem = n & 63;
            if (rem != 0) {
                long lastMask = (1L << rem) - 1L;
                total += Long.bitCount((~(words[fullWords] | other.words[fullWords])) & lastMask);
            }
            return total;
        }
    }
}

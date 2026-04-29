// bitmask.hpp — Bitmask type for 3DM solver.
//
// Dispatch in runtime between two representations:
//   - n <= 64  : single uint64_t
//   - n >  64  : std::vector<uint64_t> with ceil(n/64) words
//
// No templates, no metaprogramming. Plain struct with a mode flag.
// This keeps the code readable and 1-to-1 mappable to the pseudocode.

#pragma once

#include <cstdint>
#include <cassert>
#include <vector>

namespace tdm {

// Forward-checking friendly bitmask.
// mode == 0 : small (n <= 64), data stored in word
// mode == 1 : large (n >  64), data stored in words[]
struct Bitmask {
    int     n;       // number of bits (elements)
    int     mode;    // 0 = small, 1 = large
    uint64_t word;   // used when mode == 0
    std::vector<uint64_t> words; // used when mode == 1

    // Construct a zero-bitmask for n elements.
    explicit Bitmask(int n_elems) : n(n_elems), mode(n_elems <= 64 ? 0 : 1),
                                     word(0)
    {
        if (mode == 1) {
            words.assign((n_elems + 63) / 64, uint64_t(0));
        }
    }

    // Default construct (unusable until assigned from a real Bitmask).
    Bitmask() : n(0), mode(0), word(0) {}

    // Set bit b.
    void set(int b) {
        assert(b >= 0 && b < n);
        if (mode == 0) {
            word |= (uint64_t(1) << b);
        } else {
            words[b / 64] |= (uint64_t(1) << (b % 64));
        }
    }

    // Clear bit b (toggle – used for XOR-undo; see hand-off note).
    // Since we set exactly one bit at a time, XOR == AND-NOT here.
    void xor_bit(int b) {
        assert(b >= 0 && b < n);
        if (mode == 0) {
            word ^= (uint64_t(1) << b);
        } else {
            words[b / 64] ^= (uint64_t(1) << (b % 64));
        }
    }

    // Test bit b.
    bool test(int b) const {
        assert(b >= 0 && b < n);
        if (mode == 0) {
            return (word >> b) & uint64_t(1);
        } else {
            return (words[b / 64] >> (b % 64)) & uint64_t(1);
        }
    }

    // Bitwise OR into this bitmask (element-wise used|disc).
    // Returns a new Bitmask (used only for union, not in hot path).
    Bitmask operator|(const Bitmask& other) const {
        Bitmask result(n);
        if (mode == 0) {
            result.word = word | other.word;
        } else {
            for (int k = 0; k < (int)words.size(); ++k)
                result.words[k] = words[k] | other.words[k];
        }
        return result;
    }

    // Count free bits: popcount(~(used|disc) & mask_n).
    // mask_n = (1<<n)-1 for n<=64.
    int free_count() const {
        if (mode == 0) {
            // mask_n: n bits set
            uint64_t mask_n = (n == 64) ? ~uint64_t(0) : ((uint64_t(1) << n) - 1);
            uint64_t free_bits = (~word) & mask_n;
            return __builtin_popcountll(free_bits);
        } else {
            int total = 0;
            int full_words = n / 64;
            int rem = n % 64;
            for (int k = 0; k < full_words; ++k)
                total += __builtin_popcountll(~words[k]);
            if (rem > 0) {
                uint64_t mask = (uint64_t(1) << rem) - 1;
                total += __builtin_popcountll((~words[full_words]) & mask);
            }
            return total;
        }
    }

    // Free-count after combining with another mask (for used|disc combined).
    int free_count_combined(const Bitmask& other) const {
        if (mode == 0) {
            uint64_t mask_n = (n == 64) ? ~uint64_t(0) : ((uint64_t(1) << n) - 1);
            uint64_t free_bits = (~(word | other.word)) & mask_n;
            return __builtin_popcountll(free_bits);
        } else {
            int total = 0;
            int full_words = n / 64;
            int rem = n % 64;
            for (int k = 0; k < full_words; ++k)
                total += __builtin_popcountll(~(words[k] | other.words[k]));
            if (rem > 0) {
                uint64_t mask = (uint64_t(1) << rem) - 1;
                total += __builtin_popcountll((~(words[full_words] | other.words[full_words])) & mask);
            }
            return total;
        }
    }

    // Test whether bit b is set in (this | other).
    bool test_combined(int b, const Bitmask& other) const {
        assert(b >= 0 && b < n);
        if (mode == 0) {
            return ((word | other.word) >> b) & uint64_t(1);
        } else {
            return ((words[b / 64] | other.words[b / 64]) >> (b % 64)) & uint64_t(1);
        }
    }
};

} // namespace tdm

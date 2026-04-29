// smart.hpp — SMART backtracking solver for 3DM.
//
// Implements solveSmart / recur from docs/ALGORITHMS.md with:
//   1. Bitmask O(1) conflict test
//   2. MRV (Minimum Remaining Values)
//   3. Forward checking via bitmasks
//   4. Upper-bound pruning
//   5. Discarded-element tracking

#pragma once

#include <atomic>
#include "instance.hpp"
#include "matching.hpp"

namespace tdm {

// Run the SMART backtracking algorithm on inst.
Matching solve_smart(const Instance& inst,
                     std::atomic<bool>& aborted,
                     long long& nodes_out);

} // namespace tdm

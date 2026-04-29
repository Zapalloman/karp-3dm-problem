// brute.hpp — BASE backtracking solver for 3DM.
//
// Implements solveBrute / recur from docs/ALGORITHMS.md.
// No heuristics. Complexity O(2^m).

#pragma once

#include <atomic>
#include "instance.hpp"
#include "matching.hpp"

namespace tdm {

// Run the BASE backtracking algorithm on inst.
// aborted is an atomic flag; when set to true the recursion exits early,
// returning the best partial solution found so far.
// nodes_out receives the total node count.
Matching solve_brute(const Instance& inst,
                     std::atomic<bool>& aborted,
                     long long& nodes_out);

} // namespace tdm

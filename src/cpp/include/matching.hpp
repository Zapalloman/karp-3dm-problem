// matching.hpp — Matching data structure and output writer for 3DM.
//
// Output format (docs/INSTANCE_FORMAT.md):
//   k
//   i1        (1-based index of chosen triple)
//   ...
//   ik
//   # stats: time_ms=<float> nodes=<int> algo=<brute|smart> n=<n> m=<m> [timed_out=1]

#pragma once

#include <string>
#include <vector>

namespace tdm {

struct Stats {
    double time_ms;
    long long nodes;
    std::string algo;    // "brute" or "smart"
    int n;
    int m;
    bool timed_out;
};

struct Matching {
    std::vector<int> indices; // 0-based indices into Instance::triples

    int size() const { return static_cast<int>(indices.size()); }
};

// Write matching + stats to file at path, or to stdout if path is empty.
void write_matching(const std::string& path,
                    const Matching& matching,
                    const Stats& stats);

} // namespace tdm

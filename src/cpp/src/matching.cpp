// matching.cpp — Output writer for 3DM solutions.

#include "matching.hpp"

#include <fstream>
#include <iostream>
#include <sstream>
#include <iomanip>

namespace tdm {

void write_matching(const std::string& path,
                    const Matching& matching,
                    const Stats& stats)
{
    std::ostringstream oss;

    // Line 1: size of matching.
    oss << matching.size() << "\n";

    // Lines 2..k+1: 1-based triple indices.
    for (int idx : matching.indices) {
        oss << (idx + 1) << "\n";
    }

    // Stats line.
    oss << "# stats: "
        << "time_ms=" << std::fixed << std::setprecision(3) << stats.time_ms
        << " nodes=" << stats.nodes
        << " algo=" << stats.algo
        << " n=" << stats.n
        << " m=" << stats.m;
    if (stats.timed_out) {
        oss << " timed_out=1";
    }
    oss << "\n";

    std::string output = oss.str();

    if (path.empty()) {
        std::cout << output;
    } else {
        std::ofstream fh(path);
        if (!fh.is_open()) {
            throw std::runtime_error("Cannot open output file: " + path);
        }
        fh << output;
    }
}

} // namespace tdm

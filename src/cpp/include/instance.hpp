// instance.hpp — Instance data structure and parser for 3DM.
//
// Format (docs/INSTANCE_FORMAT.md):
//   # comment / metadata lines
//   n m
//   x1 y1 z1
//   ...
//   xm ym zm

#pragma once

#include <map>
#include <string>
#include <vector>
#include <tuple>

namespace tdm {

struct Triple {
    int x, y, z;
};

struct Instance {
    int n;                               // |X| = |Y| = |Z|
    int m;                               // |T|
    std::vector<Triple> triples;         // 0-based element indices
    std::map<std::string, std::string> meta; // opt, seed, family, note

    // Factory: parse from file.
    // Throws std::runtime_error on parse errors.
    static Instance from_file(const std::string& path);
};

} // namespace tdm

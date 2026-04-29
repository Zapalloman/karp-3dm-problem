// instance.cpp — Parser for .3dm instance files.

#include "instance.hpp"

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace tdm {

// Parse a comment line looking for recognised metadata:
//   # opt=K  # seed=S  # family=NAME  # note: text
// Returns true if a key/value pair was extracted.
static bool parse_meta_line(const std::string& line,
                             std::string& key_out,
                             std::string& val_out)
{
    // Skip leading '#' and whitespace.
    std::size_t pos = 1;
    while (pos < line.size() && line[pos] == ' ') ++pos;
    std::string body = line.substr(pos);

    // Recognised '=' prefixes.
    static const char* kv_keys[] = {"opt", "seed", "family", nullptr};
    for (int k = 0; kv_keys[k] != nullptr; ++k) {
        std::string prefix = std::string(kv_keys[k]) + "=";
        if (body.rfind(prefix, 0) == 0) {
            key_out = kv_keys[k];
            val_out = body.substr(prefix.size());
            return true;
        }
    }
    if (body.rfind("note:", 0) == 0) {
        key_out = "note";
        val_out = body.substr(5);
        if (!val_out.empty() && val_out[0] == ' ') val_out = val_out.substr(1);
        return true;
    }
    return false;
}

Instance Instance::from_file(const std::string& path)
{
    std::ifstream fh(path);
    if (!fh.is_open()) {
        throw std::runtime_error("Cannot open file: " + path);
    }

    std::map<std::string, std::string> meta;
    std::vector<std::string> data_lines;

    std::string raw_line;
    while (std::getline(fh, raw_line)) {
        // Strip trailing whitespace / carriage return.
        while (!raw_line.empty() &&
               (raw_line.back() == '\r' || raw_line.back() == ' ' ||
                raw_line.back() == '\t')) {
            raw_line.pop_back();
        }
        if (raw_line.empty()) continue;          // blank line
        if (raw_line[0] == '#') {
            std::string k, v;
            if (parse_meta_line(raw_line, k, v)) {
                meta[k] = v;
            }
            continue;                            // comment line
        }
        data_lines.push_back(raw_line);
    }

    if (data_lines.empty()) {
        throw std::runtime_error("Instance file has no data lines (missing 'n m' header): " + path);
    }

    // Parse header.
    {
        std::istringstream iss(data_lines[0]);
        int n, m;
        if (!(iss >> n >> m)) {
            throw std::runtime_error("Cannot parse header 'n m' from: " + data_lines[0]);
        }
        int extra;
        if (iss >> extra) {
            throw std::runtime_error("Header line must have exactly 2 integers, got more: " + data_lines[0]);
        }
        if (n < 1) throw std::runtime_error("n must be >= 1");
        if (m < 0) throw std::runtime_error("m must be >= 0");

        // Parse triples.
        std::vector<std::string> triple_lines(data_lines.begin() + 1, data_lines.end());
        if ((int)triple_lines.size() != m) {
            throw std::runtime_error(
                "Header declares m=" + std::to_string(m) +
                " triples but found " + std::to_string(triple_lines.size()) +
                " triple lines.");
        }

        std::vector<Triple> triples;
        triples.reserve(m);
        for (int idx = 0; idx < m; ++idx) {
            std::istringstream tss(triple_lines[idx]);
            int x, y, z;
            if (!(tss >> x >> y >> z)) {
                throw std::runtime_error("Cannot parse triple line " + std::to_string(idx + 1) + ": " + triple_lines[idx]);
            }
            if (x < 0 || x >= n) throw std::runtime_error("Triple " + std::to_string(idx+1) + ": x=" + std::to_string(x) + " out of range [0," + std::to_string(n) + ")");
            if (y < 0 || y >= n) throw std::runtime_error("Triple " + std::to_string(idx+1) + ": y=" + std::to_string(y) + " out of range [0," + std::to_string(n) + ")");
            if (z < 0 || z >= n) throw std::runtime_error("Triple " + std::to_string(idx+1) + ": z=" + std::to_string(z) + " out of range [0," + std::to_string(n) + ")");
            triples.push_back({x, y, z});
        }

        return Instance{n, m, triples, meta};
    }
}

} // namespace tdm

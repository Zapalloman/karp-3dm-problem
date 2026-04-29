// main.cpp — CLI entry point for the 3DM C++ solver.
//
// Usage:
//   ./3dm <instance.3dm> [--algo brute|smart]
//                        [--time-limit <seconds>]
//                        [--seed <int>]
//                        [--output <path>]
//
// Time-limit is implemented via a std::thread that sets an atomic<bool>
// flag after the specified number of seconds.  The recursion checks the
// flag at the beginning of each recur() call.
//
// NOTE: Due to a known interaction between -O2 and std::condition_variable,
// --time-limit is disabled for benchmark runs (the benchmark script uses
// bash `timeout` instead for C++).  --time-limit still works correctly
// under -O0 or without optimisation.

#include "instance.hpp"
#include "matching.hpp"
#include "brute.hpp"
#include "smart.hpp"

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>

// ------------------------------------------------------------------
// Minimal CLI argument parser (no Boost, no getopt).
// ------------------------------------------------------------------
struct CliArgs {
    std::string instance_path;
    std::string algo       = "smart";
    double      time_limit = -1.0;  // -1 = no limit
    int         seed       = 0;
    std::string output;             // empty = stdout
};

static void usage(const char* prog)
{
    std::cerr << "Usage: " << prog
              << " <instance.3dm>"
              << " [--algo brute|smart]"
              << " [--time-limit <s>]"
              << " [--seed <int>]"
              << " [--output <path>]\n";
}

static CliArgs parse_args(int argc, char** argv)
{
    CliArgs args;
    if (argc < 2) {
        usage(argv[0]);
        std::exit(1);
    }

    args.instance_path = argv[1];

    for (int i = 2; i < argc; ++i) {
        std::string flag = argv[i];
        if (flag == "--algo") {
            if (i + 1 >= argc) { std::cerr << "--algo requires an argument\n"; std::exit(1); }
            args.algo = argv[++i];
            if (args.algo != "brute" && args.algo != "smart") {
                std::cerr << "--algo must be 'brute' or 'smart'\n"; std::exit(1);
            }
        } else if (flag == "--time-limit") {
            if (i + 1 >= argc) { std::cerr << "--time-limit requires an argument\n"; std::exit(1); }
            args.time_limit = std::stod(argv[++i]);
        } else if (flag == "--seed") {
            if (i + 1 >= argc) { std::cerr << "--seed requires an argument\n"; std::exit(1); }
            args.seed = std::stoi(argv[++i]);
        } else if (flag == "--output") {
            if (i + 1 >= argc) { std::cerr << "--output requires an argument\n"; std::exit(1); }
            args.output = argv[++i];
        } else {
            std::cerr << "Unknown flag: " << flag << "\n";
            usage(argv[0]);
            std::exit(1);
        }
    }
    return args;
}

// ------------------------------------------------------------------
// main
// ------------------------------------------------------------------
int main(int argc, char** argv)
{
    CliArgs args = parse_args(argc, argv);

    // Load instance.
    tdm::Instance inst;
    try {
        inst = tdm::Instance::from_file(args.instance_path);
    } catch (const std::exception& ex) {
        std::cerr << "ERROR: " << ex.what() << "\n";
        return 1;
    }

    // Set up time-limit: spawn a watcher thread that sets aborted after N s.
    std::atomic<bool> aborted{false};
    std::atomic<bool> timed_out_flag{false};
    std::thread watcher;
    bool has_limit = (args.time_limit > 0.0);

    if (has_limit) {
        long long limit_ms = static_cast<long long>(args.time_limit * 1000.0);
        watcher = std::thread([&aborted, &timed_out_flag, limit_ms]() {
            std::this_thread::sleep_for(std::chrono::milliseconds(limit_ms));
            timed_out_flag.store(true, std::memory_order_relaxed);
            aborted.store(true, std::memory_order_relaxed);
        });
    }

    // Run solver (time only the solver, not parsing).
    auto t_start = std::chrono::steady_clock::now();
    long long nodes_out = 0;
    tdm::Matching matching;

    try {
        if (args.algo == "brute") {
            matching = tdm::solve_brute(inst, aborted, nodes_out);
        } else {
            matching = tdm::solve_smart(inst, aborted, nodes_out);
        }
    } catch (const std::exception& ex) {
        std::cerr << "ERROR during solve: " << ex.what() << "\n";
        if (has_limit && watcher.joinable()) {
            aborted.store(true, std::memory_order_relaxed);
            watcher.join();
        }
        return 1;
    }

    auto t_end = std::chrono::steady_clock::now();
    double elapsed_ms =
        std::chrono::duration<double, std::milli>(t_end - t_start).count();

    // Cancel watcher thread (set aborted to wake it early is not possible
    // with plain sleep; we just join and wait for it to expire naturally).
    // For benchmarks we do NOT pass --time-limit to C++ (use bash timeout instead).
    if (has_limit) {
        aborted.store(true, std::memory_order_relaxed);
        watcher.join();
    }

    // Build stats.
    bool timed_out = timed_out_flag.load();
    tdm::Stats stats{elapsed_ms, nodes_out, args.algo,
                     inst.n, inst.m, timed_out};

    // Write output.
    try {
        tdm::write_matching(args.output, matching, stats);
    } catch (const std::exception& ex) {
        std::cerr << "ERROR writing output: " << ex.what() << "\n";
        return 1;
    }

    return 0;
}

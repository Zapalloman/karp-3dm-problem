package com.threedm;

import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Main.java — CLI entry point for the 3DM solvers.
 *
 * Usage:
 *   java -cp build com.threedm.Main <instance.3dm>
 *        [--algo brute|smart] [--time-limit S] [--seed N] [--output P]
 *
 * --seed is accepted for CLI uniformity (currently unused; smart is
 * deterministic, tie-breaking by element index ascending).
 *
 * --time-limit: a separate Thread sleeps for the given number of milliseconds
 * and then sets aborted = true.  The recursion checks this flag at the start
 * of every call, so it will abort promptly after the limit expires.
 */
public final class Main {

    private Main() {}

    public static void main(String[] args) {
        // --- Parse arguments ---
        String instancePath = null;
        String algo = "smart";
        double timeLimitSec = -1.0;
        // seed is accepted but currently unused (deterministic algorithm)
        @SuppressWarnings("unused")
        int seed = 0;
        String output = null;

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--algo":
                    if (i + 1 >= args.length) die("--algo requires an argument (brute|smart)");
                    algo = args[++i];
                    if (!algo.equals("brute") && !algo.equals("smart"))
                        die("--algo must be 'brute' or 'smart', got: " + algo);
                    break;
                case "--time-limit":
                    if (i + 1 >= args.length) die("--time-limit requires a numeric argument");
                    try { timeLimitSec = Double.parseDouble(args[++i]); }
                    catch (NumberFormatException e) { die("--time-limit: not a number: " + args[i]); }
                    break;
                case "--seed":
                    if (i + 1 >= args.length) die("--seed requires an integer argument");
                    try { seed = Integer.parseInt(args[++i]); }
                    catch (NumberFormatException e) { die("--seed: not an integer: " + args[i]); }
                    break;
                case "--output":
                    if (i + 1 >= args.length) die("--output requires a path argument");
                    output = args[++i];
                    break;
                default:
                    if (args[i].startsWith("--"))
                        die("Unknown option: " + args[i]);
                    if (instancePath != null)
                        die("Multiple positional arguments; expected exactly one instance path.");
                    instancePath = args[i];
            }
        }
        if (instancePath == null) {
            System.err.println("Usage: java -cp build com.threedm.Main <instance.3dm>");
            System.err.println("       [--algo brute|smart] [--time-limit S] [--seed N] [--output P]");
            System.exit(1);
        }

        // --- Load instance ---
        Instance inst;
        try {
            inst = Instance.fromFile(instancePath);
        } catch (IOException | IllegalArgumentException e) {
            System.err.println("ERROR: " + e.getMessage());
            System.exit(1);
            return;  // unreachable; silences compiler warning
        }

        // --- Set up time-limit flag ---
        final AtomicBoolean aborted = new AtomicBoolean(false);
        Thread watcherThread = null;
        if (timeLimitSec > 0) {
            final long limitMs = (long)(timeLimitSec * 1000.0);
            watcherThread = new Thread(() -> {
                try {
                    Thread.sleep(limitMs);
                } catch (InterruptedException ex) {
                    // Interrupted means the solver finished early; nothing to do.
                    return;
                }
                aborted.set(true);
            });
            watcherThread.setDaemon(true);
            watcherThread.start();
        }

        // --- Run solver ---
        long[] nodesOut = new long[1];
        long tStart = System.nanoTime();

        Matching matching;
        if (algo.equals("brute")) {
            matching = Brute.solve(inst, aborted, nodesOut);
        } else {
            matching = Smart.solve(inst, aborted, nodesOut);
        }

        long tEndNs = System.nanoTime();
        double timeMs = (tEndNs - tStart) / 1_000_000.0;

        // Cancel the watcher thread if it is still running.
        if (watcherThread != null) {
            watcherThread.interrupt();
            try { watcherThread.join(100); } catch (InterruptedException ignored) {}
        }

        // --- Write output ---
        try {
            matching.write(output, timeMs, nodesOut[0], algo,
                           inst.n, inst.m, aborted.get());
        } catch (IOException e) {
            System.err.println("ERROR writing output: " + e.getMessage());
            System.exit(1);
        }
    }

    private static void die(String msg) {
        System.err.println("ERROR: " + msg);
        System.exit(1);
    }
}

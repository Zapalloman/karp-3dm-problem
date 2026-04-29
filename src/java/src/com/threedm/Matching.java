package com.threedm;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;

/**
 * Matching.java — DTO for a 3DM solution and output writer.
 *
 * Output format (docs/INSTANCE_FORMAT.md):
 *   k
 *   i1
 *   i2
 *   ...
 *   ik
 *   # stats: time_ms=<float> nodes=<int> algo=<brute|smart> n=<n> m=<m> [timed_out=1]
 *
 * Indices are stored 0-based internally; output is 1-based.
 */
public final class Matching {
    /** 0-based indices into Instance.triples for chosen triples. */
    public final int[] indices;

    public Matching(int[] indices) {
        this.indices = indices;
    }

    /** Number of triples in this matching. */
    public int size() {
        return indices.length;
    }

    /**
     * Write the matching and stats to output (file path, or null for stdout).
     *
     * @param output    file path, or null to write to stdout.
     * @param timeMs    elapsed time in milliseconds.
     * @param nodes     number of recursive calls.
     * @param algo      "brute" or "smart".
     * @param n         instance n.
     * @param m         instance m.
     * @param timedOut  true if time limit was reached.
     */
    public void write(String output,
                      double timeMs,
                      long nodes,
                      String algo,
                      int n,
                      int m,
                      boolean timedOut) throws IOException {
        PrintWriter pw;
        if (output == null) {
            pw = new PrintWriter(System.out);
        } else {
            pw = new PrintWriter(new FileWriter(output));
        }
        try {
            pw.println(indices.length);
            for (int idx : indices) {
                pw.println(idx + 1);  // convert to 1-based
            }
            // Build stats line
            StringBuilder sb = new StringBuilder();
            sb.append("# stats:");
            sb.append(" time_ms=").append(String.format("%.3f", timeMs));
            sb.append(" nodes=").append(nodes);
            sb.append(" algo=").append(algo);
            sb.append(" n=").append(n);
            sb.append(" m=").append(m);
            if (timedOut) sb.append(" timed_out=1");
            pw.println(sb.toString());
            pw.flush();
        } finally {
            if (output != null) pw.close();
        }
    }
}

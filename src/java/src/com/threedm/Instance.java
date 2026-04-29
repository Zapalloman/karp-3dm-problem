package com.threedm;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Instance.java — Parsed 3DM instance and file parser.
 *
 * Format (docs/INSTANCE_FORMAT.md):
 *   # comment lines (ignored except recognised metadata prefixes)
 *   n m
 *   x1 y1 z1
 *   ...
 *   xm ym zm
 *
 * Recognised metadata in comment lines:
 *   # opt=K
 *   # seed=S
 *   # family=NAME
 *   # note: free text
 *
 * Indices are 0-based internally.
 */
public final class Instance {
    /** |X| = |Y| = |Z| */
    public final int n;
    /** |T| = number of triples */
    public final int m;
    /** triples[i] = {x, y, z} with x,y,z in [0, n) */
    public final int[][] triples;
    /** Recognised metadata key->value pairs (opt, seed, family, note) */
    public final Map<String, String> meta;

    private Instance(int n, int m, int[][] triples, Map<String, String> meta) {
        this.n = n;
        this.m = m;
        this.triples = triples;
        this.meta = meta;
    }

    /**
     * Load a .3dm instance from path.
     *
     * @throws IOException if the file cannot be opened.
     * @throws IllegalArgumentException if the file is malformed.
     */
    public static Instance fromFile(String path) throws IOException {
        Map<String, String> meta = new HashMap<>();
        List<String> dataLines = new ArrayList<>();

        try (BufferedReader br = new BufferedReader(new FileReader(path))) {
            String rawLine;
            while ((rawLine = br.readLine()) != null) {
                String line = rawLine.strip();
                if (line.isEmpty()) continue;
                if (line.startsWith("#")) {
                    parseMetaLine(line, meta);
                    continue;
                }
                dataLines.add(line);
            }
        }

        if (dataLines.isEmpty()) {
            throw new IllegalArgumentException(
                "Instance file has no data lines (missing 'n m' header).");
        }

        // Parse header
        String[] headerParts = dataLines.get(0).split("\\s+");
        if (headerParts.length != 2) {
            throw new IllegalArgumentException(
                "Header line must have exactly 2 integers (n m), got: " + dataLines.get(0));
        }
        int n, m;
        try {
            n = Integer.parseInt(headerParts[0]);
            m = Integer.parseInt(headerParts[1]);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(
                "Could not parse header integers: " + dataLines.get(0), e);
        }
        if (n < 1) throw new IllegalArgumentException("n must be >= 1, got " + n);
        if (m < 0) throw new IllegalArgumentException("m must be >= 0, got " + m);

        // Parse triples
        List<String> tripleLines = dataLines.subList(1, dataLines.size());
        if (tripleLines.size() != m) {
            throw new IllegalArgumentException(
                "Header declares m=" + m + " triples but found " + tripleLines.size() + " triple lines.");
        }

        int[][] triples = new int[m][3];
        for (int idx = 0; idx < m; idx++) {
            String tline = tripleLines.get(idx);
            String[] parts = tline.split("\\s+");
            if (parts.length != 3) {
                throw new IllegalArgumentException(
                    "Triple line " + (idx + 1) + " must have exactly 3 integers, got: " + tline);
            }
            int x, y, z;
            try {
                x = Integer.parseInt(parts[0]);
                y = Integer.parseInt(parts[1]);
                z = Integer.parseInt(parts[2]);
            } catch (NumberFormatException e) {
                throw new IllegalArgumentException(
                    "Could not parse integers in triple line " + (idx + 1) + ": " + tline, e);
            }
            if (x < 0 || x >= n)
                throw new IllegalArgumentException(
                    "Triple " + (idx + 1) + ": x=" + x + " out of range [0, " + n + ").");
            if (y < 0 || y >= n)
                throw new IllegalArgumentException(
                    "Triple " + (idx + 1) + ": y=" + y + " out of range [0, " + n + ").");
            if (z < 0 || z >= n)
                throw new IllegalArgumentException(
                    "Triple " + (idx + 1) + ": z=" + z + " out of range [0, " + n + ").");
            triples[idx][0] = x;
            triples[idx][1] = y;
            triples[idx][2] = z;
        }

        return new Instance(n, m, triples, meta);
    }

    private static void parseMetaLine(String line, Map<String, String> meta) {
        // line starts with '#'
        String body = line.substring(1).strip();
        String[] keysWithEquals = {"opt", "seed", "family"};
        for (String key : keysWithEquals) {
            String prefix = key + "=";
            if (body.startsWith(prefix)) {
                meta.put(key, body.substring(prefix.length()).strip());
                return;
            }
        }
        if (body.startsWith("note:")) {
            meta.put("note", body.substring("note:".length()).strip());
        }
    }

    /** Return the opt value from metadata, or -1 if not present. */
    public int optFromMeta() {
        String v = meta.get("opt");
        if (v == null) return -1;
        try { return Integer.parseInt(v.trim()); }
        catch (NumberFormatException e) { return -1; }
    }
}

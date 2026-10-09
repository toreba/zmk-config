#!/usr/bin/env python3
"""Convert a Glove80 ZMK .keymap into the layout JSON MoergoLayerViz reads
(the format the MoErgo layout editor exports), so the keymap file stays the
single source of truth.

    keymap2moergo.py config/glove80.keymap > layout.json

Handles: #define'd layer numbers and other constants, layers (80 bindings
each), hold-tap and macro definitions (so home-row mods show tap and hold).
Keycodes stay as written (LCTRL, N1, LS(A), ...); the app maps them itself.
"""
import json
import re
import sys

KEYS_PER_LAYER = 80


def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def defines(s):
    d = {}
    for m in re.finditer(r"^\s*#define\s+(\w+)\s+(.+?)\s*$", s, flags=re.M):
        d[m.group(1)] = m.group(2).strip()
    return d


def expand(tok, d, depth=0):
    while tok in d and depth < 10:
        tok, depth = d[tok], depth + 1
    return tok


def tokenize_bindings(text, d):
    """'&kp A &mt LCTRL B' -> [('&kp',['A']), ('&mt',['LCTRL','B'])]"""
    out = []
    for tok in text.replace("\n", " ").split():
        if tok.startswith("&"):
            out.append((tok, []))
        elif out:
            out[-1][1].append(expand(tok, d))
        else:
            raise ValueError(f"parameter {tok!r} before any behavior")
    return out


def binding_json(name, params):
    b = {"value": name}
    if params:
        b["params"] = [{"value": p} for p in params]
    return b


def node_blocks(s, inner_re):
    """Yield (label, body) for every 'label: name { body }' or 'name { body }'
    whose body matches inner_re. Brace-balanced."""
    for m in re.finditer(r"(?:(\w+)\s*:\s*)?(\w+)\s*\{", s):
        start = m.end()
        depth, i = 1, start
        while depth and i < len(s):
            depth += {"{": 1, "}": -1}.get(s[i], 0)
            i += 1
        body = s[start : i - 1]
        # innermost nodes only (containers like `behaviors {` also match)
        if "{" not in body and re.search(inner_re, body):
            yield (m.group(1) or m.group(2)), body, m.group(2)


def main(path):
    raw = open(path).read()
    s = strip_comments(raw)
    d = defines(s)

    layers, layer_names = [], []
    for label, body, node in node_blocks(s, r"bindings\s*=\s*<"):
        if "compatible" in body:  # behaviors/macros, handled below
            continue
        if not node.startswith("layer_") and "display-name" not in body and "label" not in body:
            continue
        m = re.search(r"bindings\s*=\s*<(.*?)>\s*;", body, flags=re.S)
        if not m:
            continue
        b = tokenize_bindings(m.group(1), d)
        if len(b) != KEYS_PER_LAYER:
            raise SystemExit(f"layer {node}: {len(b)} bindings, expected {KEYS_PER_LAYER}")
        dn = re.search(r'display-name\s*=\s*"([^"]*)"', body) or re.search(r'label\s*=\s*"([^"]*)"', body)
        layer_names.append(dn.group(1) if dn else re.sub(r"^layer_", "", node))
        layers.append([binding_json(n, p) for n, p in b])

    hold_taps, macros = [], []
    for label, body, node in node_blocks(s, r"compatible\s*=\s*\"zmk,behavior-(hold-tap|macro)\""):
        kind = re.search(r"behavior-(hold-tap|macro)", body).group(1)
        if kind == "hold-tap":
            m = re.search(r"bindings\s*=\s*<\s*(&\w+)\s*>\s*,\s*<\s*(&\w+)\s*>", body)
            if m:
                hold_taps.append({"name": "&" + label, "bindings": [m.group(1), m.group(2)]})
        else:
            parts = re.findall(r"<([^>]*)>", re.search(r"bindings\s*=\s*(.*?);", body, flags=re.S).group(1))
            bl = []
            for part in parts:
                bl += [binding_json(n, p) for n, p in tokenize_bindings(part, d)]
            cells = re.search(r"#binding-cells\s*=\s*<(\d+)>", body)
            n = int(cells.group(1)) if cells else 0
            macros.append({"name": "&" + label, "params": [f"param{i+1}" for i in range(n)], "bindings": bl})

    doc = {
        "keyboard": "glove80",
        "firmware_api_version": "1",
        "title": "Glove80 (zmk-config)",
        "layer_names": layer_names,
        "layers": layers,
        "macros": macros,
        "holdTaps": hold_taps,
        "combos": [],
    }
    json.dump(doc, sys.stdout, indent=1)
    print(file=sys.stdout)
    print(f"{len(layers)} layers, {len(hold_taps)} hold-taps, {len(macros)} macros", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])

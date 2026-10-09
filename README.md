# Glove80 firmware (zmk-config)

My MoErgo Glove80 keyboard, built at home with Nix instead of the MoErgo web
editor. The keymap file is the single source of truth.

- **Firmware**: MoErgo's ZMK distribution (`moergo-sc/zmk` v26.09) with
  **ZMK Studio** (live keymap edits over USB) and the **Raw HID** modules
  that feed the [MoergoLayerViz](https://github.com/ovandongen/moergo-layer-viz)
  on-screen overlay (active layer, key presses).
- **Keymap**: `config/glove80.keymap`, the TailorKey layout (home-row mods
  with opposite-hand hold triggers) plus `&studio_unlock` on the Magic layer.
- **Builds** on macOS and Linux with Nix; GitHub Actions as a fallback for
  machines without Nix (Windows).

## Daily use

```sh
nix build                                   # result/zmk_lh.uf2, result/zmk_rh.uf2, result/layout.json
nix run .#layout -- ~/glove80/layout.json   # layout file for the overlay app (then reload it there)
```

Flash, **right half first**, then left. Each half appears as a USB drive and
ejects itself when the copy is done:

| Half  | Cable in | Press            | Drive        | Copy                                     |
|-------|----------|------------------|--------------|------------------------------------------|
| right | right    | Magic + `'`      | GLV80RHBOOT  | `cp result/zmk_rh.uf2 /Volumes/GLV80RHBOOT/` |
| left  | left     | Magic + Esc      | GLV80LHBOOT  | `cp result/zmk_lh.uf2 /Volumes/GLV80LHBOOT/` |

On Linux the drive mounts under `/run/media/$USER/` (or use `nix run .#flash`).
Magic is the bottom-left key of the left half; "Esc" and "'" are the
outermost keys of the 4th row on each half. If a combo does not work, hold
Magic + E (left) or I + PgDn (right) while powering that half on.

Bluetooth pairings survive a flash. If keys or the overlay misbehave over
Bluetooth afterwards, forget the keyboard on the host and pair again (the HID
descriptor changed).

## Editing the keymap

- Text: `config/glove80.keymap` (VS Code with the *ZMK Tools* extension gives
  syntax and completion). Layers are the `layer_*` nodes; `#define LAYER_*`
  gives them numbers.
- Live: **ZMK Studio** (`zmk-studio`, from nixpkgs). Plug the **left** half
  in over USB, connect, press **Magic + F3** (`&studio_unlock`) on the
  keyboard. Studio edits live on the keyboard only and do not survive a
  flash: put what you want to keep into the keymap file.
- Pictures of all layers: `keymap-drawer` (nixpkgs), e.g.
  `keymap parse -z config/glove80.keymap > /tmp/k.yaml && keymap draw /tmp/k.yaml > layers.svg`.

## The overlay (MoergoLayerViz)

Shows the active layer live; needs this firmware (Raw HID) and the layout
file from `nix run .#layout -- <file>` (same format as a MoErgo editor
export; `tools/keymap2moergo.py` generates it from the keymap). The app
remembers the file; after regenerating, reload it in the app.

- macOS: `MoergoLayerViz-osx-arm64-Setup.pkg` from the releases page. The
  package is unsigned: `sudo installer -pkg <file> -target LocalSystem`.
  F12 shows/hides the overlay.
- NixOS: `moergo-layer-viz` from `tb.glove80` in nix-config (udev rule and
  `plugdev` group included; log out and in once). No global hotkey on Wayland.
- Works over USB and Bluetooth.

## Repo layout

| Path | What |
|------|------|
| `config/glove80.keymap` | the keymap |
| `config/glove80.conf` | `CONFIG_RAW_HID`, `CONFIG_HID_VIZ` (both halves) |
| `config/west.yml` | pinned sources: moergo-sc/zmk, zmk-raw-hid, zmk-hid-viz |
| `flake.nix` | zmk-nix build; Studio + `raw_hid_adapter` shield on the left (central) half |
| `build.yaml` | the same matrix for GitHub Actions |
| `tools/keymap2moergo.py` | keymap → overlay layout JSON |

## Updating the firmware sources

Change a `revision` in `config/west.yml` (tags of
[moergo-sc/zmk](https://github.com/moergo-sc/zmk/tags), commits of the two
modules), then `nix run .#update` to refresh `zephyrDepsHash` in `flake.nix`,
then `nix build`. `nix flake update` bumps zmk-nix and nixpkgs.

Known quirk: nanopb (pinned by the fork) still imports `pkg_resources`,
which setuptools dropped; `flake.nix` shims it. Remove the shim when the
fork bumps nanopb.

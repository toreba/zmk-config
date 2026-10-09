{
  # Glove80 firmware, built with zmk-nix:
  #   nix build            -> result/zmk_{lh,rh}.uf2 + result/layout.json (overlay)
  #   nix run .#flash      -> copies them to the halves in bootloader mode
  #   nix run .#update     -> bumps the pinned deps hash after a west.yml change
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    zmk-nix = {
      url = "github:lilyinstarlight/zmk-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      zmk-nix,
    }:
    let
      forAllSystems = nixpkgs.lib.genAttrs (nixpkgs.lib.attrNames zmk-nix.packages);
    in
    {
      packages = forAllSystems (
        system: rec {
          # nix build -> result/zmk_lh.uf2, result/zmk_rh.uf2, result/layout.json
          default = nixpkgs.legacyPackages.${system}.runCommand "glove80" { } ''
            mkdir $out
            ln -s ${firmware}/zmk_lh.uf2 ${firmware}/zmk_rh.uf2 $out/
            ${layout}/bin/layout > $out/layout.json
          '';

          firmware = zmk-nix.legacyPackages.${system}.buildSplitKeyboard {
            name = "glove80-firmware";

            src = nixpkgs.lib.sourceFilesBySuffices self [
              ".board"
              ".cmake"
              ".conf"
              ".defconfig"
              ".dts"
              ".dtsi"
              ".json"
              ".keymap"
              ".overlay"
              ".shield"
              ".yml"
              "_defconfig"
            ];

            board = "glove80_%PART%";
            parts = [
              "lh"
              "rh"
            ];
            centralPart = "lh";
            # Raw HID (overlay) lives on the central half; ZMK Studio too
            # (buildSplitKeyboard enables it for centralPart only).
            shield = {
              lh = "raw_hid_adapter";
              _ = null;
            };
            enableZmkStudio = true;
            # nanopb's generator (Studio protobufs, pinned by the fork) still
            # imports pkg_resources, gone from setuptools >= 81. It only
            # needs resource_filename(); shim it.
            postConfigure = ''
              mkdir -p "$NIX_BUILD_TOP/shim"
              cat > "$NIX_BUILD_TOP/shim/pkg_resources.py" <<'PY'
              import importlib.resources
              def resource_filename(package, name):
                  return str(importlib.resources.files(package) / name)
              PY
              export PYTHONPATH="$NIX_BUILD_TOP/shim''${PYTHONPATH:+:$PYTHONPATH}"
            '';

            zephyrDepsHash = "sha256-ZPbcbpUGvENijM1QPXpFbCm5Pk1nhwgSZtsohrwrjTo=";

            meta = {
              description = "Glove80 firmware (MoErgo ZMK + Studio + Raw HID overlay)";
              license = nixpkgs.lib.licenses.mit;
              platforms = nixpkgs.lib.platforms.all;
            };
          };

          flash = zmk-nix.packages.${system}.flash.override { inherit firmware; };
          update = zmk-nix.packages.${system}.update;

          # layout.json for the MoergoLayerViz overlay, from the keymap.
          layout = nixpkgs.legacyPackages.${system}.writeShellApplication {
            name = "layout";
            runtimeInputs = [ nixpkgs.legacyPackages.${system}.python3 ];
            text = ''python3 -I ${./tools/keymap2moergo.py} "''${1:-${./config/glove80.keymap}}"'';
          };
        }
      );

      devShells = forAllSystems (system: {
        default = zmk-nix.devShells.${system}.default;
      });
    };
}

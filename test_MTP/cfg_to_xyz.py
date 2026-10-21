#!/usr/bin/env python3
"""Convert MLIP .cfg files (BEGIN_CFG/END_CFG blocks) to extended .xyz format.

Usage:
    python cfg_to_xyz.py input.cfg output.xyz [--type-map 0:C,1:H]
"""
import argparse
import sys

DEFAULT_TYPE_MAP = {0: "C", 1: "H"}


def parse_type_map(spec):
    if not spec:
        return dict(DEFAULT_TYPE_MAP)
    mapping = {}
    for pair in spec.split(","):
        k, v = pair.split(":")
        mapping[int(k.strip())] = v.strip()
    return mapping


def parse_cfg(path):
    """Yield one dict per BEGIN_CFG...END_CFG block."""
    with open(path, "r") as f:
        lines = [line.rstrip("\n") for line in f]

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        if line != "BEGIN_CFG":
            i += 1
            continue
        i += 1
        frame = {
            "size": None,
            "lattice": [],
            "atoms": [],  # list of (type, x, y, z, fx, fy, fz)
            "energy": None,
        }
        while i < n and lines[i].strip() != "END_CFG":
            l = lines[i].strip()
            if l == "Size":
                i += 1
                frame["size"] = int(lines[i].strip())
            elif l == "Supercell":
                for _ in range(3):
                    i += 1
                    frame["lattice"].append([float(x) for x in lines[i].split()])
            elif l.startswith("AtomData"):
                header = l.split()[1:]  # column names after 'AtomData:'
                # header like: id type cartes_x cartes_y cartes_z fx fy fz
                col_idx = {name: idx for idx, name in enumerate(header)}
                n_atoms = frame["size"]
                for _ in range(n_atoms):
                    i += 1
                    parts = lines[i].split()
                    typ = int(parts[col_idx["type"]])
                    x = float(parts[col_idx["cartes_x"]])
                    y = float(parts[col_idx["cartes_y"]])
                    z = float(parts[col_idx["cartes_z"]])
                    if "fx" in col_idx:
                        fx = float(parts[col_idx["fx"]])
                        fy = float(parts[col_idx["fy"]])
                        fz = float(parts[col_idx["fz"]])
                    else:
                        fx = fy = fz = 0.0
                    frame["atoms"].append((typ, x, y, z, fx, fy, fz))
            elif l == "Energy":
                i += 1
                frame["energy"] = float(lines[i].strip())
            # ignore PlusStress, Feature, and anything else
            i += 1
        yield frame
        i += 1  # skip END_CFG


def write_xyz(frames, out_path, type_map):
    with open(out_path, "w") as f:
        for frame in frames:
            n_atoms = frame["size"]
            lat = frame["lattice"]
            lattice_str = " ".join(
                f"{lat[r][c]:.6f}" for r in range(3) for c in range(3)
            )
            energy = frame["energy"]
            f.write(f"{n_atoms}\n")
            f.write(
                f'Lattice="{lattice_str}" '
                f'Properties=species:S:1:pos:R:3:forces:R:3 '
                f'energy={energy!r}\n'
            )
            for typ, x, y, z, fx, fy, fz in frame["atoms"]:
                species = type_map.get(typ, str(typ))
                f.write(
                    f"{species:<3s}{x:13.6f}{y:13.6f}{z:13.6f}"
                    f"{fx:13.6f}{fy:13.6f}{fz:13.6f}\n"
                )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Input .cfg file")
    parser.add_argument("output", help="Output .xyz file")
    parser.add_argument(
        "--type-map",
        default="",
        help="Comma-separated type:element mapping, e.g. '0:C,1:H' "
        "(default: 0:C,1:H)",
    )
    args = parser.parse_args()

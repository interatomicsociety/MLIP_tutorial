#!/usr/bin/env python3
import sys
import os

def split_qe_md_scf_dynamic(filepath):
    # Standard QE conversion factor: 1 Bohr (a.u.) = 0.529177210903 Angstroms
    BOHR_TO_ANGSTROM = 0.529177210903

    if not os.path.isfile(filepath):
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)

    with open(filepath, 'r') as f:
        lines = f.readlines()

    # --- 1. Find the lattice parameter (alat) and number of atoms (nat) ---
    alat = None
    nat = None
    
    for line in lines:
        if "lattice parameter (alat)" in line:
            alat = float(line.split('=')[1].split()[0])
        elif "number of atoms/cell" in line:
            nat = int(line.split('=')[1].split()[0])
            
        if alat and nat:
            break
            
    if not alat or not nat:
        print("Error: Could not find 'lattice parameter (alat)' or 'number of atoms/cell' in the output.")
        sys.exit(1)

    alat_ang = alat * BOHR_TO_ANGSTROM

    # --- 2. Split into Header and Dynamics Blocks ---
    header_lines = []
    blocks = []
    current_block = []
    state = "HEADER"
    
    for line in lines:
        if state == "HEADER":
            if "Self-consistent Calculation" in line:
                state = "STEP_0"
                current_block.append(line)
            else:
                header_lines.append(line)
        elif state == "STEP_0":
            if "Entering Dynamics" in line:
                blocks.append(current_block)
                current_block = [line]
                state = "STEP_N"
            else:
                current_block.append(line)
        elif state == "STEP_N":
            if "Entering Dynamics" in line:
                blocks.append(current_block)
                current_block = [line]
            else:
                current_block.append(line)
                
    if current_block:
        blocks.append(current_block)

    # --- 3. Locate the coordinate block in the header securely ---
    coord_start_idx = -1
    
    for i, line in enumerate(header_lines):
        # Using substring checks to avoid whitespace mismatches
        if "site n." in line and "positions (alat units)" in line:
            coord_start_idx = i + 1
            break

    if coord_start_idx == -1:
        print("Error: Could not locate the 'site n. atom positions' block in the header.")
        sys.exit(1)
        
    coord_end_idx = coord_start_idx + nat

    base_name = os.path.splitext(os.path.basename(filepath))[0]

    # --- 4. Process blocks and inject updated coordinates ---
    for idx, block in enumerate(blocks):
        atoms = []
        in_atoms = False
        
        # Parse the updated ATOMIC_POSITIONS in Angstroms
        for line in block:
            if "ATOMIC_POSITIONS (angstrom)" in line:
                in_atoms = True
                continue
            if in_atoms:
                parts = line.split()
                if len(parts) == 4 and parts[1].replace('.', '', 1).lstrip('-').isdigit():
                    atoms.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
                elif line.strip() == "" or "kinetic energy" in line:
                    in_atoms = False

        out_header = header_lines.copy()
        
        # If we successfully read atoms from the MD step, replace them
        if atoms and len(atoms) == nat:
            updated_coords = []
            for i, (elem, ax, ay, az) in enumerate(atoms, 1):
                tx = ax / alat_ang
                ty = ay / alat_ang
                tz = az / alat_ang
                
                fmt_line = f"     {i:>4}           {elem:<4}tau({i:>4}) = ( {tx:11.7f}   {ty:11.7f}   {tz:11.7f}  )\n"
                updated_coords.append(fmt_line)
                
            out_header = out_header[:coord_start_idx] + updated_coords + out_header[coord_end_idx:]

        out_name = f"{base_name}_scf_{idx}.out"
        with open(out_name, 'w') as out_f:
            out_f.writelines(out_header)
            out_f.writelines(block)
            
        print(f"Generated standalone SCF output: {out_name}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        split_qe_md_scf_dynamic(sys.argv[1])
    else:
        print("Usage: python md2scf_dynamic_v2.py <path_to_md_log.out>")

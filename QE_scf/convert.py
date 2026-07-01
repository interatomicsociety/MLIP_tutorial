#!/usr/bin/env python3
import sys
import os

def convert_qe_to_cfg(filepath):
    # Constants for physical unit conversions
    BOHR2ANG = 0.529177210903
    RY2EV = 13.6056980659
    RY_AU_TO_EV_ANG = 25.7110430973

    if not os.path.isfile(filepath):
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)

    with open(filepath, 'r') as f:
        lines = f.readlines()

    nat = None
    alat = None
    a1, a2, a3 = None, None, None
    positions = []
    forces = []
    energy = None
    stress = {}

    # Parse Quantum ESPRESSO output
    for i, line in enumerate(lines):
        if "number of atoms/cell" in line:
            nat = int(line.split('=')[1].split()[0])
        elif "lattice parameter (alat)" in line:
            alat = float(line.split('=')[1].split()[0])
        elif "a(1) =" in line:
            parts = line.split('=')[1].replace('(','').replace(')','').split()
            a1 = [float(x) for x in parts]
        elif "a(2) =" in line:
            parts = line.split('=')[1].replace('(','').replace(')','').split()
            a2 = [float(x) for x in parts]
        elif "a(3) =" in line:
            parts = line.split('=')[1].replace('(','').replace(')','').split()
            a3 = [float(x) for x in parts]
        elif "site n." in line and "positions (alat units)" in line:
            positions.clear() # Clear array to handle possible multiple outputs (e.g., relax)
            for j in range(nat):
                parts = lines[i + 1 + j].split('=')[1].replace('(','').replace(')','').split()
                positions.append([float(x) for x in parts])
        elif "Forces acting on atoms (cartesian axes, Ry/au):" in line:
            forces.clear()
            offset = 1
            # Bypass potential blank lines before forces start
            while i + offset < len(lines) and lines[i + offset].strip() == "":
                offset += 1
            for j in range(nat):
                parts = lines[i + offset + j].split()
                t = int(parts[3])
                fx = float(parts[6])
                fy = float(parts[7])
                fz = float(parts[8])
                forces.append([t, fx, fy, fz])
        elif line.startswith("!    total energy"):
            energy = float(line.split('=')[1].split('Ry')[0])
        elif "total   stress  (Ry/bohr**3)                   (kbar)     P=" in line:
            # Extract stress directly from the printed kbar columns
            r1 = lines[i+1].split()
            r2 = lines[i+2].split()
            r3 = lines[i+3].split()
            stress['xx'] = float(r1[3])
            stress['xy'] = float(r1[4])
            stress['xz'] = float(r1[5])
            stress['yy'] = float(r2[4])
            stress['yz'] = float(r2[5])
            stress['zz'] = float(r3[5])

    # Validation
    if not all([nat, alat, a1, positions, forces, energy, stress]):
        print("Error: Missing required data in the QE output. Ensure the log includes complete SCF, forces, and stress.")
        sys.exit(1)

    # Convert native QE units to CFG format units
    alat_ang = alat * BOHR2ANG
    energy_ev = energy * RY2EV
    supercell_ang = [
        [x * alat_ang for x in a1],
        [x * alat_ang for x in a2],
        [x * alat_ang for x in a3]
    ]

    base_name = os.path.splitext(os.path.basename(filepath))[0]
    out_name = f"{base_name}.cfg"

    # Write formatted Extended CFG
    with open(out_name, 'w') as f:
        f.write("BEGIN_CFG\n")
        f.write(" Size\n")
        f.write(f"    {nat}\n")
        f.write(" Supercell\n")
        for row in supercell_ang:
            f.write(f"    {row[0]:.6f}    {row[1]:.6f}    {row[2]:.6f}\n")
        f.write(" AtomData:  id type       cartes_x      cartes_y      cartes_z           fx          fy          fz\n")
        
        for i in range(nat):
            idx = i + 1
            # Shift QE 1-based type index to 0-based integers
            t = forces[i][0] - 1  
            
            # Position conversion
            cx = positions[i][0] * alat_ang
            cy = positions[i][1] * alat_ang
            cz = positions[i][2] * alat_ang
            
            # Force conversion
            fx = forces[i][1] * RY_AU_TO_EV_ANG
            fy = forces[i][2] * RY_AU_TO_EV_ANG
            fz = forces[i][3] * RY_AU_TO_EV_ANG
            
            f.write(f"    {idx:<4} {t:<7} {cx:.6f}    {cy:.6f}    {cz:.6f}   {fx: .6f}   {fy: .6f}   {fz: .6f}\n")
            
        f.write(" Energy\n")
        f.write(f"    {energy_ev}\n")
        f.write(" PlusStress:  xx          yy          zz          yz          xz          xy\n")
        f.write(f"    {stress['xx']:.3f}         {stress['yy']:.3f}    {stress['zz']:.3f}    {stress['yz']:.3f}    {stress['xz']:.3f}    {stress['xy']:.3f}\n")
        f.write(" Feature   EFS_by       QE\n")
        f.write("END_CFG\n")

    print(f"Successfully created: {out_name}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        convert_qe_to_cfg(sys.argv[1])
    else:
        print("Usage: python qe2cfg.py <path_to_pwout.out>")

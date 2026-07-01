import os
import sys

# Define the file names
INPUT_FILENAME = sys.argv[1]

# Mapping of integer atom types to chemical symbols based on your sample
TYPE_MAP = {'0': 'C', '1': 'H'}

# Standard QE Header 
QE_TEMPLATE_TOP = """&control
    calculation='scf'
    tprnfor=.TRUE.,
    restart_mode='from_scratch',
    pseudo_dir = '../PP/',
    outdir='./',
    disk_io='low',
    tstress=.true.,
    etot_conv_thr = 1e-5,
    forc_conv_thr = 1e-4
 /
 &system
    ibrav = 0,
    nat=  12,
    ntyp= 2,
    input_dft = "PBE",
    ecutwfc = 20,
    ecutrho = 200,
    nosym=.true.,
    occupations = 'smearing',
    degauss = 0.001
 /
 &electrons
    conv_thr =  1.0d-5
    mixing_beta = 0.1
    electron_maxstep = 500
 /
CELL_PARAMETERS angstrom
8.000000 0 0
0 8.000000 0
0 0 8.000000
ATOMIC_SPECIES
 C 12.011 C.pbe-n-kjpaw_psl.1.0.0.UPF
 H 1.0 H.pbe-kjpaw_psl.1.0.0.UPF
ATOMIC_POSITIONS angstrom
"""

# Standard QE Footer
QE_TEMPLATE_BOTTOM = """K_POINTS {automatic}
 1 1 1 0 0 0
"""

def generate_qe_inputs(filename):
    if not os.path.exists(filename):
        print(f"Error: Could not find {filename}")
        return

    with open(filename, 'r') as f:
        lines = f.readlines()

    structures = []
    current_structure = []
    in_atom_data = False

    # Parse the CFG file block by block
    for line in lines:
        line = line.strip()
        
        if line == 'BEGIN_CFG':
            current_structure = []
            in_atom_data = False
        elif line.startswith('AtomData:'):
            in_atom_data = True
        elif line.startswith('Energy') or line.startswith('PlusStress'):
            in_atom_data = False
        elif line == 'END_CFG':
            if current_structure:
                structures.append(current_structure)
            in_atom_data = False
        elif in_atom_data and line:
            parts = line.split()
            
            # Ensure the line is actually an atom row (id type x y z fx fy fz)
            # Checking if parts[0] is a digit avoids errors with unexpected text formatting
            if len(parts) >= 5 and parts[0].isdigit():
                atom_type = parts[1]
                x, y, z = parts[2], parts[3], parts[4]
                element = TYPE_MAP.get(atom_type, 'X')
                
                # Format to closely match the desired scientific notation/spacing 
                formatted_coord = f"  {element}   {float(x):.16e} {float(y):.16e} {float(z):.16e}"
                current_structure.append(formatted_coord)

    # Write out the independent QE files
    for i, atoms in enumerate(structures):
        out_filename = f"qe_scf_{i+1}.in"
        with open(out_filename, 'w') as out:
            out.write(QE_TEMPLATE_TOP)
            for atom_line in atoms:
                out.write(atom_line + "\n")
            out.write(QE_TEMPLATE_BOTTOM)
            
        print(f"Successfully generated: {out_filename} (contains {len(atoms)} atoms)")

if __name__ == "__main__":
    generate_qe_inputs(INPUT_FILENAME)

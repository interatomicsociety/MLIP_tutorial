python3 make_qe.py diff.cfg

for i in {1..21};
do
mkdir qe_$i
mv ./qe_scf_$i.in ./qe_$i
done

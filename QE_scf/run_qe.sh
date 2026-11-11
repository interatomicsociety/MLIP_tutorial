for i in {1..7}
do
cd qe_$i
qe_pw < qe_scf_$i.in > ../md_scf_$i.out
cd ..
done
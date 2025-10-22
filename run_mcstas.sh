cd mcstas

#rm -rf silica_100nm_air_*
mcrun -c --mpi 8 GISANS_test.instr -n 1e4 -d silica_100nm_air_10m collimation=10.0  source_size=0.01 model=silica_100nm_air
mcrun --mpi 8 GISANS_test.instr -n 1e4 -d silica_100nm_air_20m collimation=20.0  source_size=0.01 model=silica_100nm_air
mcrun --mpi 8 GISANS_test.instr -n 1e4 -d silica_100nm_air_05m collimation=5.0  source_size=0.01 model=silica_100nm_air

rm -rf hexagonal_spheres_*
mcrun --mpi 8 GISANS_test.instr -n 1e4 -d hexagonal_spheres_10m collimation=10.0  source_size=0.01 model=hexagonal_spheres
mcrun --mpi 8 GISANS_test.instr -n 1e4 -d hexagonal_spheres_20m collimation=20.0  source_size=0.01 model=hexagonal_spheres
mcrun --mpi 8 GISANS_test.instr -n 1e4 -d hexagonal_spheres_05m collimation=5.0  source_size=0.01 model=hexagonal_spheres

rm -rf interference_2d_paracrystal_*
mcrun -c --mpi 8 GISANS_test.instr -n 1e3 -d interference_2d_paracrystal_10m collimation=10 model=interference_2d_paracrystal
mcrun -c --mpi 8 GISANS_test.instr -n 1e3 -d interference_2d_paracrystal_20m collimation=20 model=interference_2d_paracrystal
mcrun -c --mpi 8 GISANS_test.instr -n 1e3 -d interference_2d_paracrystal_05m collimation=5 model=interference_2d_paracrystal
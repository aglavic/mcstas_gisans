"""
Model for Silica particles on Silicon measured in air.
"""
import bornagain as ba
from bornagain import nm, deg

def get_sample(phi_i=0.):
    # Define materials
    material_Air = ba.MaterialBySLD("Air", 0.0, 0.0)
    material_SiO2 = ba.MaterialBySLD("SiO2", 3.47e-06, 0.0)
    material_Silicon = ba.MaterialBySLD("Silicon", 2.07e-06, 0.0)

    # Define form factors
    ff = ba.Sphere(60*nm)

    # Define particles
    particle = ba.Particle(material_SiO2, ff)
    particle.translate(ba.R3(0., 0., -120*nm))

    # Define 2D lattices
    lattice = ba.BasicLattice2D(
        125*nm, 125*nm, 120*deg, 0*deg)

    # Define interference functions
    iff = ba.InterferenceFinite2DLattice(lattice, 5, 5)
    iff.setIntegrationOverXi(True)

    # Define particle layouts
    layout = ba.ParticleLayout()
    layout.addParticle(particle, 1.0)
    layout.setInterference(iff)
    layout.setTotalParticleSurfaceDensity(7.39008344563e-05)

    # Define layers
    layer_1 = ba.Layer(material_Air)
    layer_2 = ba.Layer(material_Air, 120*nm)
    layer_2.setNumberOfSlices(5)
    layer_2.addLayout(layout)
    layer_3 = ba.Layer(material_Silicon)

    # Define sample
    sample = ba.Sample()
    sample.addLayer(layer_1)
    sample.addLayer(layer_2)
    sample.addLayer(layer_3)

    return sample

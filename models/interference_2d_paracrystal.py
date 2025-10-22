import bornagain as ba
from bornagain import deg, nm


def get_sample():
    # Define materials
    material_Particle = ba.RefractiveMaterial("Particle", 0.0006, 2e-08)
    material_Substrate = ba.RefractiveMaterial("Substrate", 6e-06, 2e-08)
    material_Vacuum = ba.RefractiveMaterial("Vacuum", 0.0, 0.0)

    # Define form factors
    ff = ba.Cylinder(5*nm, 5*nm)

    # Define particles
    particle = ba.Particle(material_Particle, ff)

    # Define 2D lattices
    lattice = ba.BasicLattice2D(
        20*nm, 20*nm, 120*deg, 0*deg)

    # Define interference functions
    iff = ba.Interference2DParacrystal(lattice, 0*nm, 20000*nm, 20000*nm)
    iff.setIntegrationOverXi(True)
    iff_pdf_1  = ba.Profile2DCauchy(1*nm, 1*nm, 0*deg)
    iff_pdf_2  = ba.Profile2DCauchy(1*nm, 1*nm, 0*deg)
    iff.setProbabilityDistributions(iff_pdf_1, iff_pdf_2)

    # Define particle layouts
    layout = ba.ParticleLayout()
    layout.addParticle(particle, 1.0)
    layout.setInterference(iff)
    layout.setTotalParticleSurfaceDensity(0.00288675134595)

    # Define layers
    layer_1 = ba.Layer(material_Vacuum)
    layer_1.addLayout(layout)
    layer_2 = ba.Layer(material_Substrate)

    # Define sample
    sample = ba.Sample()
    sample.addLayer(layer_1)
    sample.addLayer(layer_2)

    return sample
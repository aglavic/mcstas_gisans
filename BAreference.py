"""
Perform BornAgain reference simulation to compare with McStas results.

Uses a divergent beam with wavelength spread and the same detector distance/pixel size.
"""

import numpy as np
from scipy.signal import convolve2d
from dataclasses import dataclass
from importlib import import_module
from time import time

import bornagain as ba
from bornagain import deg, angstrom, nm
from bornagain.numpyutil import Arrayf64Converter

MFILE = "models."

@dataclass
class InstrumentConfig:
    I0:float = None # total neutron weight on sample
    collimation:float = 10.0 # m - collimation/detector distance
    source_size:float = 0.01 # m - size of beam at collimation distance
    alpha_i:float = 0.3 # ° - incident angle
    wavelength:float = 6.0 # Å - central wavelength

    def __post_init__(self):
        if self.I0 is None:
            # approximate flux for the configuration of the McStas model
            self.I0 = 354994*(5.0/self.collimation)**2

class BARunner:
    """
    Generates appropriate beam parameters and runs simulation similar to BARunnerProcess in BAserver module.
    """
    DET_PIXELS = 256
    DET_SIZE = 1.0 # m - total width/height of detector
    resolution = 0.1 # relative wavelength resolution (uniform distributed FWHM)

    def __init__(self, ba_model="silica_100nm_air", instrument_config:InstrumentConfig = InstrumentConfig()):
        self.instrument_config = instrument_config
        self.ba_model = ba_model

    def simulate(self):
        print("Generate model")
        print(f"  instrument configuration: {self.instrument_config}")
        sim_module = import_module(MFILE+self.ba_model)
        self.sample = sim_module.get_sample(0.)

        self.sim = self.get_simulation()
        self.add_beam_resolution()
        self.sim.options().setUseAvgMaterials(True)
        self.sim.options().setIncludeSpecular(True)
        print("Run simulation")
        self.res = self.sim.simulate()

        print("Extract data")
        self.I = Arrayf64Converter.asNpArray(self.res.dataArray())
        self.add_transmitted()
        self.apply_sample_size()

    def get_simulation(self):
        beam = ba.Beam(self.instrument_config.I0,
                       self.instrument_config.wavelength*angstrom,
                       self.instrument_config.alpha_i*deg)

        # Define detector
        ang_range = np.arctan2(self.DET_SIZE/2., self.instrument_config.collimation)
        print(f"  ang_range={ang_range}")
        corr = self.instrument_config.alpha_i*deg
        detector = ba.SphericalDetector(self.DET_PIXELS, -ang_range, ang_range,
                                        self.DET_PIXELS, -ang_range-corr, ang_range-corr)

        return ba.ScatteringSimulation(beam, self.sample, detector)

    def add_beam_resolution(self):
        # add wavelength distribution and divergence to simulation
        distr_1 = ba.DistributionGate(
                self.instrument_config.wavelength*(1-self.resolution/2.)*angstrom,
                self.instrument_config.wavelength*(1+self.resolution/2.)*angstrom, 5)
        self.sim.addParameterDistribution(ba.ParameterDistribution.BeamWavelength, distr_1)

        bangle = np.arctan2(self.instrument_config.source_size/2., self.instrument_config.collimation)

        distr_2 = ba.DistributionGate(self.instrument_config.alpha_i*deg-bangle,
                                          self.instrument_config.alpha_i*deg+bangle, 5)
        self.sim.addParameterDistribution(ba.ParameterDistribution.BeamGrazingAngle, distr_2)
        distr_3 = ba.DistributionGate(-bangle, +bangle, 5)
        self.sim.addParameterDistribution(ba.ParameterDistribution.BeamAzimuthalAngle, distr_3)
        print(f"  beam angular resolution = +/- {bangle/deg} degrees")

    def get_simulation_specular(self):
        scan = ba.AlphaScan(2, self.instrument_config.alpha_i*deg, self.instrument_config.alpha_i*deg+1e-6)
        scan.setWavelength(self.instrument_config.wavelength*angstrom)
        return ba.SpecularSimulation(scan, self.sample)

    def add_transmitted(self):
        ssim = self.get_simulation_specular()
        res = ssim.simulate()
        ref = Arrayf64Converter.asNpArray(res.dataArray())[0]
        # size of beam on detector in pixels
        beam_size = max(1, round(self.instrument_config.source_size * self.DET_SIZE/self.DET_PIXELS))
        cen = self.DET_PIXELS//2
        start = cen - beam_size//2
        end = start+beam_size+1
        self.I[start:end, start:end] = (1.-ref)*self.instrument_config.I0/beam_size**2

    def apply_sample_size(self):
        # model sample width by detector image convolution with uniform distribution
        # (moving detector is approximately equivalent to moving beam and reflection location)
        samle_size_pix = 0.01 / self.DET_SIZE * self.DET_PIXELS # 10mm sample in pixel coordinates ~2.5
        side_fraction = (samle_size_pix-1.0)/2.0 # fraction of left/right pixel that is filled
        kernel = np.array([[side_fraction/3., 1./3., side_fraction/3.]])
        kernel /= kernel.sum() # normalized kernel to keep integrated intensity
        self.I = convolve2d(self.I, kernel, mode='same')



    def store_result(self, fname):
        print(f"Saving to file {fname}")
        np.savez(fname, self.I)

if __name__ == "__main__":
    import sys, os
    if len(sys.argv) < 3:
        exit("Required arguments: model_name collimation {output_file}")
    model = sys.argv[1]
    collimation = float(sys.argv[2])
    inst_config = InstrumentConfig(collimation=collimation)
    runner = BARunner(ba_model=model, instrument_config=inst_config)
    start = time()
    runner.simulate()
    print(f"Finished in {time()-start} seconds")
    if len(sys.argv) >= 4:
        out_name = sys.argv[3]
    else:
        out_name = os.path.join('ba_output', f'{model}_{collimation:02.0f}m.npz')
    runner.store_result(out_name)
"""
A socket server that creates a new process for every connection,
in the process it uses events received from McStas to run BornAgain
simulations and then send back the simulated events.

Developed for BornAgain 23.0.
"""

import asyncio
import logging
import socket
import multiprocessing
import numpy as np

from importlib import import_module
import bornagain as ba
from bornagain import deg, angstrom, nm
from bornagain.numpyutil import Arrayf64Converter

MFILE = "models."

V2L = 3956.034012 # m/s·Å
ANGLE_RANGE=1.5 # degree scattering angle covered by detector
DEBUG = False

class BARunnerProcess(multiprocessing.Process):
    """
    Creates a worker process with input and output Queue
    that is alive as long as the client is connected.
    For every message received from the client it runs a BornAgain simulation.
    """


    def __init__(self, odim=102, ang_range=ANGLE_RANGE, ba_model="silica_100nm_air"):
        self.log = multiprocessing.Queue() # sends log-messages back to the main process
        self.input = multiprocessing.Queue()
        self.output = multiprocessing.Queue()
        self.ang_range=ang_range
        self.ba_model=ba_model
        self.odim = odim # length of event stream to return per input
        super().__init__()

    def run(self):
        self.log.put_nowait((logging.INFO,
                            f'Start long running computation on process {multiprocessing.current_process()}'))
        # detector dimension to create at least as many events as requested
        self.det_dim = int(np.sqrt(self.odim-3)+1)
        self.log.put_nowait((logging.INFO,
                            f'  simulation detector size {self.det_dim}x{self.det_dim}'))
        sim_module = import_module(MFILE+self.ba_model)
        self.log.put_nowait((logging.INFO,
                             f'  loaded model {MFILE+self.ba_model}'))

        while True:
            data = self.input.get()
            if type(data) is str and data == 'quit':
                break
            e = data[0]
            if DEBUG:
                # for debug purpose, send back just copies of the initial event
                self.output.put(np.array([e]*self.odim, dtype=EVENT_TYPE))
                continue

            out_events = []

            alpha_i = np.arctan2(e.vz, e.vy) * 180. / np.pi  # deg
            phi_i = np.arctan2(e.vx, e.vy) * 180. / np.pi  # deg
            v = np.sqrt(e.vx ** 2 + e.vy ** 2 + e.vz ** 2)
            wavelength = V2L / v  # Å
            #self.log.put_nowait(f'  incident beam {alpha_i}°, {phi_i}°, {wavelength}')

            self.sample = sim_module.get_sample(phi_i)

            # Calculated reflected and transmitted (1-reflected) beams
            ssim = self.get_simulation_specular(wavelength, alpha_i)
            res = ssim.simulate()
            pref = e.p*Arrayf64Converter.asNpArray(res.dataArray())[0]
            spec = (pref, e.vx, e.vy, -e.vz)
            ptrans = (1.0-Arrayf64Converter.asNpArray(res.dataArray())[0])*e.p
            trans = (ptrans, e.vx, e.vy, e.vz)

            # calculate BINS² outgoing beams with a random angle within one pixel range (-1,-1) to (1,1)
            Ry =  2*np.random.random()-1
            Rz =  2*np.random.random()-1

            sim = self.get_simulation(wavelength, alpha_i, e.p, Ry, Rz)
            sim.options().setUseAvgMaterials(True)
            # only use one thread, multithreading through McStas making multiple socket connections
            sim.options().setNumberOfThreads(1)
            res = sim.simulate()
            # get probability (intensity) for all pixels
            pout = Arrayf64Converter.asNpArray(res.dataArray())
            # calculate beam angle relative to coordinate system, including incident beam direction
            #alpha_f = ANGLE_RANGE*(np.linspace(1., -1., self.det_dim)+Ry/(self.det_dim-1))
            xs = res.xAxis()
            ys = res.yAxis()
            alpha_f = np.array([ys.binCenter(i) for i in range(ys.size())])
            phi_f = np.array([xs.binCenter(i) for i in range(ys.size())])-phi_i*deg

            VX, VZ= np.meshgrid(np.sin(phi_f)*v, -np.sin(alpha_f)*v)
            VY = np.sqrt(v**2 - VX**2 - VZ**2)
            for pouti, vxi, vyi, vzi in zip(pout.flatten(), VX.flatten(), VY.flatten(), VZ.flatten()):
                out_events.append((pouti, vxi, vyi, vzi))

            #out = np.array(out_events)
            if len(out_events)<(self.odim-2):
                # if number of events requested is too small, throw away random event
                np.random.shuffle(out_events)
                out_events = out_events[:self.odim-1]
            out = np.array([spec, trans]+out_events, dtype=EVENT_TYPE)
            self.log.put_nowait((logging.DEBUG, f'  sending back {len(out)} processed events'))
            # convert numpy EVENT_TYPE events back to string
            mstrs = []
            for event in out:
                mstrs.append("%16.9e;%16.9e;%16.9e;%16.9e\n" % tuple(event))
            message = "".join(mstrs)
            self.output.put(message)

    def get_simulation(self, wavelength=6.0, alpha_i=0.2, p=1.0, Ry=0., Rz=0.):
        """
        Create a simulation with BINS² pixels that cover an angular range of
        ANGLE_RANGE degrees.
        The Ry and Rz values are relative rotations of the detector within one pixel
        to finely define the outgoing direction of events.
        """
        beam = ba.Beam(p, wavelength*angstrom, alpha_i*deg)

        dRy = Ry*self.ang_range*deg/(self.det_dim)
        dRz = Rz*self.ang_range*deg/(self.det_dim)

        # Define detector
        detector = ba.SphericalDetector(self.det_dim, -self.ang_range*deg+dRz, self.ang_range*deg+dRz,
                                        self.det_dim, -self.ang_range*deg+dRy, self.ang_range*deg+dRy)

        return ba.ScatteringSimulation(beam, self.sample, detector)

    def get_simulation_specular(self, wavelength=6.0, alpha_i=0.2):
        scan = ba.AlphaScan(2, alpha_i*deg, alpha_i*deg+1e-6)
        scan.setWavelength(wavelength*angstrom)
        return ba.SpecularSimulation(scan, self.sample)


async def handle_logging(proc):
    while proc.is_alive():
        while proc.log.empty():
            await asyncio.sleep(0.01)
        severity, message = proc.log.get()
        logging.log(severity, message)

EVENT_TYPE = np.dtype([
    ('p', np.float64),
    ('vx', np.float64),
    ('vy', np.float64),
    ('vz', np.float64),
])

async def read_full_request(client):
    loop = asyncio.get_event_loop()
    request = ''
    while not request.endswith('\n'):
        # read until next newline character
        next = (await loop.sock_recv(client, 1)).decode('ascii')
        if next=='':
            return ''
        request += next
    return request

async def handle_client(client):
    logging.info(f"Connection by client {client}")
    loop = asyncio.get_event_loop()

    # handshake with client and extract some simulation parameters
    request = await read_full_request(client)
    if request.startswith('INIT;McStas'):
        _, _, odim, ang_range, ba_model, *__ = request.split(';')
        odim = int(odim)
        ang_range = float(ang_range)
        logging.info(f"From client '{request.strip()}', sending ACK")
        await loop.sock_sendall(client, b'ACK\n')
        worker = BARunnerProcess(odim, ang_range, ba_model.strip())
        worker.start()
        loop.create_task(handle_logging(worker))
    else:
        logging.warning(f"Could not establish handshake, client send {request}")
        client.close()
        return

    # start loop waiting from incoming events
    recieved_events = 0
    while request!='':
        request = await read_full_request(client)
        if request == '':
            break
        event = np.array([tuple(request.split(';'))], dtype=EVENT_TYPE).view(np.rec.recarray)
        worker.input.put(event)
        recieved_events += 1
        logging.debug(f'  received event {event}')
        while worker.output.empty():
            await asyncio.sleep(0.001)
        message = worker.output.get()
        await loop.sock_sendall(client, message.encode('ascii'))

        logging.debug(f'  all events send, waiting for next input...')

    worker.input.put('quit')
    worker.join()
    logging.info(f'Received {recieved_events} events')
    client.close()

async def run_server(interface='127.0.0.1', port=15555):
    logging.info(f"Starting socket server on {interface}:{port}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((interface, port))
    server.listen(50)
    server.setblocking(False)

    loop = asyncio.get_event_loop()

    while True:
        client, _ = await loop.sock_accept(server)
        loop.create_task(handle_client(client))


def main():
    import sys
    if len(sys.argv)>1:
        interface = sys.argv[1]
    else:
        interface = '127.0.0.1'
    asyncio.run(run_server(interface=interface))


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    main()
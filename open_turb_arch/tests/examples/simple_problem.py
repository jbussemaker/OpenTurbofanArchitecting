"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright: (c) 2020, Deutsches Zentrum fuer Luft- und Raumfahrt e.V.
Contact: jasper.bussemaker@dlr.de

Simple architecting problem: only contains existing engine architectures,
1 objective (TSFC) and no constraints.
"""


import os
import time
import pickle
import multiprocessing

os.environ['OPENMDAO_REQUIRE_MPI'] = 'false'  # Suppress OpenMDAO MPI import warnings

from open_turb_arch.architecting import *
from open_turb_arch.architecting.metrics import *
from open_turb_arch.architecting.turbofan import *
from open_turb_arch.evaluation.analysis import *

from open_turb_arch.architecting.pymoo import *
from pymoo.optimize import minimize
from pymoo.algorithms.nsga2 import NSGA2
from pymoo.operators.sampling.latin_hypercube_sampling import LatinHypercubeSampling


def get_architecting_problem():
    analysis_problem = AnalysisProblem(
        design_condition=DesignCondition(
            mach=1e-6,  # Mach number [-]
            alt=0,  # Altitude [ft]
            thrust=150e3,  # Thrust [N]
            turbine_in_temp=1450,  # Turbine inlet temperature [C]
            bleed_offtake=0.5,  # Extraction bleed offtake [kg/s]
            power_offtake=37.5e3,  # Power offtake [W]
            balancer=DesignBalancer(init_turbine_pr=10, init_mass_flow=400, init_extraction_bleed_frac=0.02),
        )
    )

    return ArchitectingProblem(
        analysis_problem=analysis_problem,
        choices=[
            FanChoice(),
            ShaftChoice(),
            GearboxChoice(),
            NozzleMixingChoice(),
            OfftakesChoice(),
        ],
        objectives=[
            TSFCMetric()
        ],
        constraints=[
            JetMachMetric(max_jet_mn=1.),
        ],
        metrics=[
            TSFCMetric(),
            WeightMetric(),
            LengthMetric(),
            DiameterMetric(),
            NOxMetric(),
            NoiseMetric(),
            JetMachMetric(),
        ],
    )


def get_pymoo_architecting_problem():
    return PymooArchitectingProblem(get_architecting_problem())


if __name__ == '__main__':
    architecting_problem = get_architecting_problem()

    architecting_problem.print_results = True
    architecting_problem.verbose = True
    architecting_problem._max_iter = 30
    architecting_problem.save_results_folder = 'results'  # Insert folder name to save results
    architecting_problem.save_results_combined = True

    # The number of processes to be used
    with multiprocessing.Pool(3) as pool:
        t = time.time()
        problem = PymooArchitectingProblem(architecting_problem)
        problem.parallelization = ('starmap', pool.starmap)

        algorithm = NSGA2(
            pop_size=75,
            sampling=LatinHypercubeSampling()
        )
        result = minimize(problem, algorithm, termination=('n_eval', 1000), verbose=True, save_history=True)
        elapsed = time.time() - t

    architecting_problem.finalize()
    with open(architecting_problem.save_results_folder+'/pymoo_algo_results.pkl', 'wb') as fp:
        pickle.dump(result, fp)

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

Realistic architecting problem: contains all possible engine architectures,
3 objectives (TSFC, weight and noise) and 4 constraints (length, diameter,
NOx and jet Mach number).
"""


import time
import pickle
import multiprocessing

from open_turb_arch.architecting.architecting_problem import get_architecting_problem, get_pymoo_architecting_problem

from pymoo.optimize import minimize
from pymoo.algorithms.nsga2 import NSGA2
from pymoo.operators.sampling.latin_hypercube_sampling import LatinHypercubeSampling

if __name__ == '__main__':
    architecting_problem = get_architecting_problem()

    architecting_problem.print_results = True
    architecting_problem._max_iter = 30
    architecting_problem.save_results_folder = 'results'  # Insert folder name to save results
    architecting_problem.save_results_combined = True

    # The number of processes to be used
    with multiprocessing.Pool(3) as pool:
        t = time.time()
        problem = get_pymoo_architecting_problem(architecting_problem)
        problem.parallelization = ('starmap', pool.starmap)

        algorithm = NSGA2(
            pop_size=240,
            sampling=LatinHypercubeSampling(),
        )
        result = minimize(problem, algorithm, termination=('n_eval', 3000), verbose=True)
        elapsed = time.time() - t

    architecting_problem.finalize()
    with open(architecting_problem.save_results_folder+'/pymoo_algo_results.pkl', 'wb') as fp:
        pickle.dump(result, fp)

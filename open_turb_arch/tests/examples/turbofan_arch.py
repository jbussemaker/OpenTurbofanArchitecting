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
"""

import os

if __name__ == '__main__':
    from open_turb_arch.architecting import *
    from open_turb_arch.architecting.metrics import *
    from open_turb_arch.architecting.turbofan import *
    from open_turb_arch.evaluation.analysis import *

    import time
    from open_turb_arch.architecting.pymoo import *
    from pymoo.optimize import minimize
    from pymoo.algorithms.nsga2 import NSGA2
    from pymoo.operators.sampling.latin_hypercube_sampling import LatinHypercubeSampling
    from pymoo.model.evaluator import Evaluator
    from pymoo.visualization.scatter import Scatter
    import multiprocessing

    analysis_problem = AnalysisProblem(
        design_condition=DesignCondition(
            mach=1e-6,  # Mach number [-]
            alt=0,  # Altitude [ft]
            thrust=133e3,  # Thrust [N]
            turbine_in_temp=1450,  # Turbine inlet temperature [C]
            bleed_offtake=0.5,  # Extraction bleed offtake [kg/s]
            power_offtake=37.5,  # Power offtake [W]
            balancer=DesignBalancer(init_turbine_pr=10, init_mass_flow=400, init_extraction_bleed_frac=0.02),
        ),
        # evaluate_conditions=[
        #     EvaluateCondition(
        #         name_='OD0',
        #         mach=0.8, alt=30000,
        #         thrust=75e3,
        #         balancer=OffDesignBalancer(
        #             init_bpr=8.5,
        #             init_shaft_rpm=8000.,
        #             init_mass_flow=200.,
        #             init_far=.025,
        #             init_extraction_bleed_frac=0.01
        #         ),
        #     ),
        # ],
    )

    architecting_problem = ArchitectingProblem(
        analysis_problem=analysis_problem,
        choices=[
            # FuelChoice(),
            FanChoice(fix_include_fan=True, fixed_bpr=11),
            CRTFChoice(fix_include_crtf=False),
            ShaftChoice(fixed_number_shafts=2, fixed_opr=40, fixed_rpm_shaft_hp=19391, fixed_rpm_shaft_ip=19391),
            GearboxChoice(fix_include_gear=False),
            NozzleMixingChoice(fix_include_mixing=False),
            # AfterburnerChoice(),
            # ITBChoice(),
            # CoolingBleedChoice(),
            OfftakesChoice(),
            IntercoolerChoice(fix_include_ic=True),
        ],
        objectives=[
            TSFCMetric(),
            WeightMetric(),
            LengthMetric(),
            DiameterMetric(),
            NOxMetric(),
            NoiseMetric(),
            JetMachMetric(),
        ],
        constraints=[
            TSFCMetric(max_tsfc=20),
            WeightMetric(max_weight=10000),
            LengthMetric(max_length=4.5),
            DiameterMetric(max_diameter=2.75),
            NOxMetric(max_NOx=1.),
            NoiseMetric(max_noise=130),
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

    architecting_problem.print_results = True
    architecting_problem._max_iter = 30
    print(len(architecting_problem.free_opt_des_vars))
    # architecting_problem.save_results_folder = 'C:\\Users\\thiba\\OneDrive\\Documenten\\TU DELFT\\MSc 1\\Thesis\\3. Execution\\Results\\Test'
    # architecting_problem.save_results_combined = True
    #
    # # The number of processes to be used
    # pool = multiprocessing.Pool(3)
    #
    # t = time.time()
    # problem = PymooArchitectingProblem(architecting_problem)
    # problem.parallelization = ('starmap', pool.starmap)
    # pop = LatinHypercubeSampling().do(problem, 240)  # 240
    # algorithm = NSGA2(pop_size=240, sampling=LatinHypercubeSampling())  # 240
    # Evaluator().eval(problem, pop)
    # result = minimize(problem, algorithm, termination=('n_eval', 3000), verbose=True)  # 3000
    # elapsed = time.time() - t
    # pool.close()
    #
    # os.makedirs(architecting_problem.save_results_folder, exist_ok=True)
    # path = os.path.join(architecting_problem.save_results_folder, 'results_pymoo.txt')
    # f = open(path, 'a')
    # f.write(str(result.F))
    # f.write(str(result.G))
    # f.close()
    #
    # print(result.F)
    # print(elapsed)
    # try:
    #     plot = Scatter(title='Objective Space')
    #     plot.add(result.F, s=30, facecolors='none', edgecolors='r')
    #     plot.add(result.F, plot_type='line', color='black', linewidth=2)
    #     plot.show()
    #     print(problem.pareto_front())
    # except:
    #     print('Error')

    n_dv = 0
    n_errors = 0
    length = 0
    unique_dvs = set()
    arch_dvs = []
    metrics_dvs = []
    for dv in architecting_problem.iter_design_vectors(n_cont=1):
        n_dv += 1
        print('Design vector (input): %r' % dv)
        architecture, imputed_dv = architecting_problem.generate_architecture(dv)
        print('Architecture: %r' % architecture)
        print('Imputed design vector: %r' % imputed_dv)
        print('Number of design vectors: %d' % n_dv)
        # try:
        design_vector, objectives, constraints, metrics = architecting_problem.evaluate(dv)
        unique_dvs.add(tuple(imputed_dv))
        print('Metrics: %r' % metrics)
        if length < len(unique_dvs):
            arch_dvs.append(tuple(imputed_dv))
            metrics_dvs.append(tuple(metrics))
        length = len(unique_dvs)
        # except:
        #     print('Error')
        #     n_errors += 1
        print('Number of unique design vectors: %d' % len(unique_dvs))
        print()
        print('Unique design vectors: %r' % unique_dvs)
        print('Architecture design vectors: %r' % arch_dvs)
        print('Metrics design vectors: %r' % metrics_dvs)
        print('Number of errors: %d' % n_errors)
        print()
        break
    print('Unique design vectors %r:' % unique_dvs)
    print('Architecture design vectors: %r' % arch_dvs)
    print('Metrics design vectors: %r' % metrics_dvs)
    print('Number of errors: %d' % n_errors)

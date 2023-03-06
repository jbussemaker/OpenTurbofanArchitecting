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
import json
import numpy as np

from open_turb_arch.architecting import *
from open_turb_arch.architecting.metrics import *
from open_turb_arch.architecting.turbofan import *
from open_turb_arch.evaluation.analysis import *


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
            CRTFChoice(),
            ShaftChoice(),
            GearboxChoice(),
            NozzleMixingChoice(),
            ITBChoice(),
            CoolingBleedChoice(),
            OfftakesChoice(),
            IntercoolerChoice(),
        ],
        objectives=[
            TSFCMetric(),
            WeightMetric(),
            NoiseMetric(),
        ],
        constraints=[
            LengthMetric(max_length=4.5),
            DiameterMetric(max_diameter=2.75),
            NOxMetric(max_NOx=15.),
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


def get_pymoo_architecting_problem(architecting_problem: ArchitectingProblem, parallel_pool=None):
    from open_turb_arch.architecting.pymoo import HAS_PYMOO, PymooArchitectingProblem
    if not HAS_PYMOO:
        raise RuntimeError('pymoo not available or other version than 0.5.0 installed')
    prob = PymooArchitectingProblem(architecting_problem, parallel_pool=parallel_pool)

    path = os.path.join(os.path.dirname(__file__), 'architecting_problem_pf.json')
    if os.path.exists(path):
        with open(path, 'r') as fp:
            pf_data = json.load(fp)

        prob._pareto_front = np.array(pf_data['f'])
        prob._pareto_set = np.array(pf_data['x'])

    return prob

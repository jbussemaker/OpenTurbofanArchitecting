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

Simple turbojet example based on pycycle.example_cycles.simple_turbojet
"""


from open_turb_arch.architecting import *
from open_turb_arch.architecting.metrics import *
from open_turb_arch.architecting.turbofan import *
from open_turb_arch.evaluation.analysis import *


def get_architecting_problem():
    analysis_problem = AnalysisProblem(
        design_condition=DesignCondition(
            mach=1e-6,  # Mach number [-]
            alt=0,  # Altitude [ft]
            thrust=52489,  # Thrust [N]
            turbine_in_temp=1043.5,  # Turbine inlet temperature [C]
            bleed_offtake=0,  # Extraction bleed offtake [kg/s]
            power_offtake=0,  # Power offtake [W]
            balancer=DesignBalancer(init_turbine_pr=4.46, init_mass_flow=168, init_extraction_bleed_frac=0),
        ),
    )

    return ArchitectingProblem(
        analysis_problem=analysis_problem,
        choices=[
            FanChoice(False),
            ShaftChoice(fixed_opr=13.5, fixed_rpm_shaft_hp=8070),
            OfftakesChoice(1, 1),
        ],
        objectives=[
            TSFCMetric(),
        ],
        constraints=[],
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


if __name__ == '__main__':

    architecting_problem = get_architecting_problem()
    architecting_problem.print_results = True
    architecting_problem.max_iter = 30

    dv = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    architecture, imputed_dv = architecting_problem.generate_architecture(dv)
    design_vector, objectives, constraints, metrics = architecting_problem.evaluate(dv)

    print('Design vector: %r' % design_vector)
    print('Objectives: %r' % objectives)
    print('Constraints: %r' % constraints)
    print('Metrics: %r' % metrics)

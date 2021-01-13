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

from open_turb_arch.architecting import *
from open_turb_arch.architecting.metrics import *
from open_turb_arch.architecting.turbofan import *
from open_turb_arch.evaluation.analysis import *

analysis_problem = AnalysisProblem(
    design_condition=DesignCondition(
        mach=1e-6, alt=0,
        thrust=20017,  # 4500 lbf
        turbine_in_temp=1314,  # 2857 degR
        balancer=DesignBalancer(init_turbine_pr=8.36),
    ),
    # evaluate_conditions=[
    #     EvaluateCondition(
    #         name_='OD0',
    #         mach=1e-6, alt=0,
    #         thrust=18000,
    #         balancer=OffDesignBalancer(
    #             init_mass_flow=60.,
    #             init_bpr=3.,
    #             init_shaft_rpm=8070.,
    #             init_far=.02,
    #         ),
    #     ),
    # ],
)

architecting_problem = ArchitectingProblem(
    analysis_problem=analysis_problem,
    choices=[
        FanChoice(fix_include_fan=None, fixed_bpr=None, fixed_fpr=None),
    ],
    objectives=[
        TSFCMetric(),
    ],
    constraints=[
        TSFCMetric(max_tsfc=.25),
    ],
    metrics=[
        TSFCMetric(),
    ],
)

if __name__ == '__main__':
    for has_fan in [0, 1]:
        has_fan_status = 'turbofan' if has_fan else 'turbojet'
        design_vector = [has_fan, 5., 1.5]  # has_fan, bpr, fpr

        print('Design vector %s (input): %r' % (has_fan_status, design_vector))
        architecture, _ = architecting_problem.generate_architecture(design_vector)
        print(architecture)

        design_vector, objectives, constraints, metrics = architecting_problem.evaluate(design_vector)
        print('Design vector %s (output): %r' % (has_fan_status, design_vector))
        print('Objectives %s: %r' % (has_fan_status, objectives))
        print('Constraints %s: %r' % (has_fan_status, constraints))
        print('Metrics %s: %r' % (has_fan_status, metrics))

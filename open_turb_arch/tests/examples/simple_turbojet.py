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

from open_turb_arch.evaluation.analysis import *
from open_turb_arch.evaluation.architecture import *

inlet = Inlet(name='inlet', mach=.6, p_recovery=1)
inlet.target = compressor = Compressor(name='comp', map=CompressorMap.AXI_5, mach=.02, pr=13.5, eff=.83)
compressor.target = burner = Burner(name='burner', fuel=FuelType.JET_A, mach=.02, p_loss_frac=.03)
burner.target = turbine = Turbine(name='turb', map=TurbineMap.LPT_2269, mach=.4, eff=.86)
turbine.target = nozzle = Nozzle(name='nozz', type=NozzleType.CD, v_loss_coefficient=.99)
shaft = Shaft(name='shaft', connections=[compressor, turbine], rpm_design=8070, power_loss=0.)

architecture = TurbofanArchitecture(elements=[inlet, compressor, burner, turbine, nozzle, shaft])

design_condition = DesignCondition(
    mach=1e-6, alt=0,
    thrust=52489,  # 11800 lbf
    turbine_in_temp=1043.5,  # 2370 degR
)
evaluate_conditions = [
    EvaluateCondition(
        name_='OD0',
        mach=1e-5, alt=0,
        thrust=48930.3,  # 11000 lbf
    ),
    EvaluateCondition(
        name_='OD1',
        mach=.2, alt=5000,  # ft
        thrust=35585.8,  # 8000 lbf
    ),
]
analysis_problem = AnalysisProblem(design_condition=design_condition, evaluate_conditions=evaluate_conditions)

design_condition.balancer = DesignBalancer(init_turbine_pr=4.)
evaluate_conditions[0].balancer = evaluate_conditions[1].balancer = OffDesignBalancer(init_mass_flow=80.)

if __name__ == '__main__':
    builder = CycleBuilder(architecture=architecture, problem=analysis_problem)
    prob = builder.get_problem()
    builder.view_n2(prob, show_browser=False)

    builder.run(prob)
    builder.print_results(prob)

    print('\nOutput metrics:')
    for condition, metrics in builder.get_metrics(prob).items():
        print('%8s: %r' % (condition.name, metrics))
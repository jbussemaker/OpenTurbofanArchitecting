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

import pytest
from open_turb_arch.evaluation.analysis import *
from open_turb_arch.evaluation.architecture import *


@pytest.fixture
def simple_turbojet_arch():
    inlet = Inlet(name='inlet', mach=.6, p_recovery=1)
    inlet.target = compressor = Compressor(name='comp', map=CompressorMap.AXI_5, mach=.02, pr=13.5, eff=.83)
    compressor.target = burner = Burner(name='burner', fuel=FuelType.JET_A, mach=.02, p_loss_frac=.03)
    burner.target = turbine = Turbine(name='turb', map=TurbineMap.LPT_2269, mach=.4, eff=.86)
    turbine.target = nozzle = Nozzle(name='nozz', type=NozzleType.CD, v_loss_coefficient=.99)
    shaft = Shaft(name='shaft', connections=[compressor, turbine], rpm_design=8070, power_loss=0.)

    return TurbofanArchitecture(elements=[inlet, compressor, burner, turbine, nozzle, shaft])


def test_simple_turbojet(simple_turbojet_arch: TurbofanArchitecture):
    design_condition = DesignCondition(
        mach=1e-6, alt=0,
        thrust=20017,  # 4500 lbf
        turbine_in_temp=1314,  # 2857 degR
        balancer=DesignBalancer(init_turbine_pr=2.9),
    )
    analysis_problem = AnalysisProblem(design_condition=design_condition)

    b = CycleBuilder(architecture=simple_turbojet_arch, problem=analysis_problem)
    prob = b.get_problem()

    b.run(prob)
    b.print_results(prob)

    metrics = b.get_metrics(prob)
    assert design_condition in metrics
    met = metrics[design_condition]
    assert met.fuel_flow == pytest.approx(.53192, abs=1e-4)
    assert met.mass_flow == pytest.approx(20.338, abs=1e-3)
    assert met.thrust == pytest.approx(20017., abs=.1)
    assert met.tsfc == pytest.approx(26.5737, abs=1e-4)
    assert met.opr == pytest.approx(13.5)


def test_off_design_point(simple_turbojet_arch: TurbofanArchitecture):
    design_condition = DesignCondition(
        mach=1e-6, alt=0,
        thrust=20017,  # 4500 lbf
        turbine_in_temp=1314,  # 2857 degR
        balancer=DesignBalancer(init_turbine_pr=2.9),
    )
    evaluate_condition = EvaluateCondition(
        name_='OD0',
        mach=1e-5, alt=0,
        thrust=10e3,
        balancer=OffDesignBalancer(init_mass_flow=15.),
    )
    analysis_problem = AnalysisProblem(design_condition=design_condition, evaluate_conditions=[evaluate_condition])

    b = CycleBuilder(architecture=simple_turbojet_arch, problem=analysis_problem)
    prob = b.get_problem()

    b.run(prob)
    b.print_results(prob)

    metrics = b.get_metrics(prob)
    assert evaluate_condition in metrics
    met = metrics[evaluate_condition]
    assert met.fuel_flow == pytest.approx(.23485, abs=1e-4)
    assert met.mass_flow == pytest.approx(14.397, abs=1e-3)
    assert met.thrust == pytest.approx(10000., abs=.1)
    assert met.tsfc == pytest.approx(23.485, abs=1e-4)
    assert met.opr == pytest.approx(8.2, abs=1e-2)


@pytest.fixture
def simple_turbofan_arch():
    inlet = Inlet(name='inlet', mach=.6, p_recovery=1)
    inlet.target = fan = Compressor(name='fan', map=CompressorMap.AXI_5, mach=.4578, pr=1.5, eff=.89)
    fan.target = splitter = Splitter(name='splitter', bpr=5., core_mach=.3, bypass_mach=.45)

    splitter.target_core = compressor = Compressor(name='comp', map=CompressorMap.AXI_5, mach=.02, pr=13.5, eff=.83)
    compressor.target = burner = Burner(name='burner', fuel=FuelType.JET_A, mach=.02, p_loss_frac=.03)
    burner.target = turbine = Turbine(name='turb', map=TurbineMap.LPT_2269, mach=.4, eff=.86)
    turbine.target = nozzle = Nozzle(name='nozz', type=NozzleType.CD, v_loss_coefficient=.99)
    shaft = Shaft(name='shaft', connections=[compressor, turbine, fan], rpm_design=8070, power_loss=0.)

    splitter.target_bypass = bypass_nozzle = \
        Nozzle(name='bypass_nozzle', type=NozzleType.CV, v_loss_coefficient=.99, fuel_in_air=False)

    return TurbofanArchitecture(elements=[
        inlet, compressor, burner, turbine, nozzle, shaft, fan, splitter, bypass_nozzle])


def test_simple_turbofan(simple_turbofan_arch: TurbofanArchitecture):
    design_condition = DesignCondition(
        mach=1e-6, alt=0,
        thrust=20017,  # 4500 lbf
        turbine_in_temp=1314,  # 2857 degR
        balancer=DesignBalancer(init_turbine_pr=8.36),
    )
    analysis_problem = AnalysisProblem(design_condition=design_condition)

    b = CycleBuilder(architecture=simple_turbofan_arch, problem=analysis_problem)
    prob = b.get_problem()

    b.run(prob)
    b.print_results(prob)

    metrics = b.get_metrics(prob)
    assert design_condition in metrics
    met = metrics[design_condition]
    assert met.fuel_flow == pytest.approx(.236695, abs=1e-4)
    assert met.mass_flow == pytest.approx(59.357, abs=1e-3)
    assert met.thrust == pytest.approx(20017., abs=.1)
    assert met.tsfc == pytest.approx(11.8247, abs=1e-4)
    assert met.opr == pytest.approx(20.25)

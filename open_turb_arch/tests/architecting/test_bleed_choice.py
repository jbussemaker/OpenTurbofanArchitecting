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
import timeit
from open_turb_arch.architecting.problem import *
from open_turb_arch.architecting.metrics import *
from open_turb_arch.architecting.opt_defs import *
from open_turb_arch.architecting.turbofan import *
from open_turb_arch.evaluation.analysis.balancer import *
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.architecture.turbomachinery import *


@pytest.fixture
def bleed_problem():
    return AnalysisProblem(DesignCondition(
        mach=1e-6, alt=0,
        thrust=20017,  # 4500 lbf
        turbine_in_temp=1314,  # 2857 degR
        balancer=DesignBalancer(init_turbine_pr=8.36),
    ))


def _get_problem(bleed_problem, shaft_choice, bleed_choice):
    return ArchitectingProblem(
        analysis_problem=bleed_problem, choices=[shaft_choice, bleed_choice],
        objectives=[TSFCMetric()], constraints=[TSFCMetric()], metrics=[TSFCMetric()],
    )


def test_des_vars(bleed_problem):
    problem = _get_problem(bleed_problem, ShaftChoice(), BleedChoice())
    assert len(problem.opt_des_vars) == 44
    assert len(problem.free_opt_des_vars) == 44
    assert isinstance(problem.opt_des_vars[5], IntegerDesignVariable)


def test_modify_architecture(bleed_problem):
    problem = _get_problem(bleed_problem, ShaftChoice(), BleedChoice())

    architecture, dv = problem.generate_architecture([0, 5.5, 5.5, 10500, 10500,
                                                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    assert len(architecture.get_elements_by_type(BleedInter)) == 0
    assert len(architecture.get_elements_by_type(BleedIntra)) == 0

    architecture, dv = problem.generate_architecture([0, 5.5, 5.5, 10500, 10500,
                                                      1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    assert len(architecture.get_elements_by_type(BleedInter)) == 0
    assert len(architecture.get_elements_by_type(BleedIntra)) == 0

    architecture, dv = problem.generate_architecture([0, 5.5, 5.5, 10500, 10500,
                                                      1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    assert len(architecture.get_elements_by_type(BleedInter)) == 0
    assert len(architecture.get_elements_by_type(BleedIntra)) == 0

    architecture, dv = problem.generate_architecture([0, 5.5, 5.5, 10500, 10500,
                                                      1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    assert len(architecture.get_elements_by_type(BleedInter)) == 1
    assert len(architecture.get_elements_by_type(BleedIntra)) == 0

    architecture, dv = problem.generate_architecture([2, 5.5, 5.5, 10500, 10500,
                                                      1, 1, 1, 14, 0.05, 0.02, 0.03, 0.04, 1, 14, 0.02, 0.03, 0.04, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    assert len(architecture.get_elements_by_type(BleedInter)) == 2
    assert len(architecture.get_elements_by_type(BleedIntra)) == 0

    architecture, dv = problem.generate_architecture([2, 5.5, 5.5, 10500, 10500,
                                                      1, 1, 1, 14, 0.05, 0.05, 0.05, 0.05, 1, 14, 0.05, 0.05, 0.05, 0.05, 1, 14, 0.05, 0.05, 0.05, 0.05, 1, 1, 14, 0.05, 0.05, 0.05, 0.05, 1, 14, 0.05, 0.05, 0.05, 0.05, 1, 14, 0.05, 0.05, 0.05, 0.05])
    print(architecture)
    assert len(architecture.get_elements_by_type(BleedInter)) == 3
    assert len(architecture.get_elements_by_type(BleedIntra)) == 3


def test_evaluate_architecture(bleed_problem):
    problem = _get_problem(bleed_problem, ShaftChoice(), BleedChoice())
    problem.print_results = True

    start = timeit.default_timer()
    dv_imputed, obj, con, met = problem.evaluate([2, 5.5, 5.5, 10500, 10500,
                                                  1, 1, 1, 14, 0.05, 0.02, 0.03, 0.04, 1, 14, 0.02, 0.03, 0.04, 0.025, 1, 14, 0.02, 0.03, 0.04, 0.025, 1, 1, 14, 0.05, 0.02, 0.03, 0.04, 1, 14, 0.02, 0.03, 0.04, 0.025, 1, 14, 0.02, 0.03, 0.04, 0.025])
    assert obj == [pytest.approx(26.5737, abs=5e-1)]
    assert con == [pytest.approx(26.5737, abs=5e-1)]
    assert met == [pytest.approx(26.5737, abs=5e-1)]
    time = timeit.default_timer()-start

    start_cached = timeit.default_timer()
    dv_imputed2, obj, con, met = problem.evaluate([0, 5., 1.5, 0])  # With no fan & no mixer (cached)
    assert dv_imputed2 == dv_imputed
    assert obj == [pytest.approx(26.5737, abs=5e-1)]
    assert con == [pytest.approx(26.5737, abs=5e-1)]
    assert met == [pytest.approx(26.5737, abs=5e-1)]
    time_cached = timeit.default_timer()-start_cached
    assert time_cached < time*.01

    dv_imputed, obj, con, met = problem.evaluate([0, 5., 1.5, 1])  # With no fan but mixer (should not have effect)
    assert obj == [pytest.approx(26.5737, abs=5e-1)]
    assert con == [pytest.approx(26.5737, abs=5e-1)]
    assert met == [pytest.approx(26.5737, abs=5e-1)]

    dv_imputed, obj, con, met = problem.evaluate([1, 5., 1.5, 0])  # With fan but no mixer
    assert obj == [pytest.approx(11.8247, abs=5e-1)]
    assert con == [pytest.approx(11.8247, abs=5e-1)]
    assert met == [pytest.approx(11.8247, abs=5e-1)]

    dv_imputed, obj, con, met = problem.evaluate([1, 5., 1.5, 1])  # With fan and mixer
    assert obj == [pytest.approx(11.8247, abs=5e-1)]
    assert con == [pytest.approx(11.8247, abs=5e-1)]
    assert met == [pytest.approx(11.8247, abs=5e-1)]

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
def itb_problem():
    return AnalysisProblem(DesignCondition(
        mach=1e-6, alt=0,
        thrust=20017,  # 4500 lbf
        turbine_in_temp=1314,  # 2857 degR
        balancer=DesignBalancer(init_turbine_pr=8.36),
    ))


def _get_problem(itb_problem, shaft_choice, itb_choice):
    return ArchitectingProblem(
        analysis_problem=itb_problem, choices=[shaft_choice, itb_choice],
        objectives=[TSFCMetric()], constraints=[TSFCMetric()], metrics=[TSFCMetric()],
    )


def test_des_vars(itb_problem):
    problem = _get_problem(itb_problem, ShaftChoice(), ITBChoice())
    assert len(problem.opt_des_vars) == 9
    assert len(problem.free_opt_des_vars) == 9
    assert isinstance(problem.opt_des_vars[7], DiscreteDesignVariable)


# def test_modify_architecture(itb_problem):
#     problem = _get_problem(itb_problem, ShaftChoice(), ITBChoice())
#
#     architecture, dv = problem.generate_architecture([0, 0, 0, 0, 0, 0, 0, 0, 0])
#     assert len(architecture.get_elements_by_type(Burner)) == 1
#
#     architecture, dv = problem.generate_architecture([0, 1, 0, 0, 0, 0, 0, 0, 0])
#     assert len(architecture.get_elements_by_type(Burner)) == 1
#
#     architecture, dv = problem.generate_architecture([1, 0, 0, 0, 0, 0, 0, 0, 0])
#     assert len(architecture.get_elements_by_type(Burner)) == 1
#
#     architecture, dv = problem.generate_architecture([1, 1, 0, 0, 0, 0, 0, 0, 0])
#     assert len(architecture.get_elements_by_type(Burner)) == 2
#
#     architecture, dv = problem.generate_architecture([2, 0, 0, 0, 0, 0, 0, 0, 0])
#     assert len(architecture.get_elements_by_type(Burner)) == 1
#
#     architecture, dv = problem.generate_architecture([2, 1, 0, 0, 0, 0, 0, 0, 0])
#     assert len(architecture.get_elements_by_type(Burner)) == 2


# def test_evaluate_architecture(itb_problem):
#     problem = _get_problem(itb_problem, ShaftChoice(), ITBChoice())
#     problem.print_results = True
#
#     start = timeit.default_timer()
#     dv_imputed, obj, con, met = problem.evaluate([0, 0, 0, 0, 0, 0, 0, 0, 0])  # 1 shaft & no ITB
#     assert obj == [pytest.approx(26.5737, abs=5e-1)]
#     assert con == [pytest.approx(26.5737, abs=5e-1)]
#     assert met == [pytest.approx(26.5737, abs=5e-1)]
#     time = timeit.default_timer()-start
#
#     start_cached = timeit.default_timer()
#     dv_imputed2, obj, con, met = problem.evaluate([0, 0, 0, 0, 0, 0, 0, 0, 0])  # 1 shaft & no ITB (cached)
#     assert dv_imputed2 == dv_imputed
#     assert obj == [pytest.approx(26.5737, abs=5e-1)]
#     assert con == [pytest.approx(26.5737, abs=5e-1)]
#     assert met == [pytest.approx(26.5737, abs=5e-1)]
#     time_cached = timeit.default_timer()-start_cached
#     assert time_cached < time*.01
#
#     dv_imputed, obj, con, met = problem.evaluate([0, 1, 0, 0, 0, 0, 0, 0, 0])  # 1 shaft & ITB
#     assert obj == [pytest.approx(26.41, abs=5e-1)]
#     assert con == [pytest.approx(26.41, abs=5e-1)]
#     assert met == [pytest.approx(26.41, abs=5e-1)]
#
#     dv_imputed, obj, con, met = problem.evaluate([1, 0, 0, 0, 0, 0, 0, 0, 0])  # 2 shaft & no ITB
#     assert obj == [pytest.approx(21.7541, abs=5e-1)]
#     assert con == [pytest.approx(21.7541, abs=5e-1)]
#     assert met == [pytest.approx(21.7541, abs=5e-1)]
#
#     dv_imputed, obj, con, met = problem.evaluate([1, 1, 0, 0, 0, 0, 0, 0, 0])  # 2 shaft & ITB
#     assert obj == [pytest.approx(21.7541, abs=5e-1)]
#     assert con == [pytest.approx(21.7541, abs=5e-1)]
#     assert met == [pytest.approx(21.7541, abs=5e-1)]
#
#     dv_imputed, obj, con, met = problem.evaluate([2, 0, 0, 0, 0, 0, 0, 0, 0])  # 3 shaft & no ITB
#     assert obj == [pytest.approx(7.3296, abs=5e-1)]
#     assert con == [pytest.approx(7.3296, abs=5e-1)]
#     assert met == [pytest.approx(7.3296, abs=5e-1)]
#
#     dv_imputed, obj, con, met = problem.evaluate([2, 1, 0, 0, 0, 0, 0, 0, 0])  # 3 shaft & ITB
#     assert obj == [pytest.approx(7.3296, abs=5e-1)]
#     assert con == [pytest.approx(7.3296, abs=5e-1)]
#     assert met == [pytest.approx(7.3296, abs=5e-1)]

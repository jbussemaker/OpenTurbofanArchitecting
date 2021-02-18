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
def shafts_problem():
    return AnalysisProblem(DesignCondition(
        mach=1e-6, alt=0,
        thrust=20017,  # 4500 lbf
        turbine_in_temp=1314,  # 2857 degR
        balancer=DesignBalancer(init_turbine_pr=8.36),
    ))


def _get_problem(shafts_problem, shafts_number):
    return ArchitectingProblem(
        analysis_problem=shafts_problem, choices=[shafts_number],
        objectives=[TSFCMetric()], constraints=[TSFCMetric()], metrics=[TSFCMetric()],
    )


def test_des_vars(shafts_problem):
    problem = _get_problem(shafts_problem, ShaftChoice())
    assert len(problem.opt_des_vars) == 5
    assert len(problem.free_opt_des_vars) == 5
    assert isinstance(problem.opt_des_vars[0], IntegerDesignVariable)

    full_dv, _ = problem.get_full_design_vector([0])
    assert len(full_dv) == 5


def test_modify_architecture(shafts_problem):
    problem = _get_problem(shafts_problem, ShaftChoice())

    architecture, dv = problem.generate_architecture([0, 5.5, 5.5, 10500, 10500])
    assert dv == [0, 5.5, 5.5, 10500, 10500]
    assert len(architecture.get_elements_by_type(Compressor)) == 1
    assert len(architecture.get_elements_by_type(Turbine)) == 1

    architecture, dv = problem.generate_architecture([1, 5.5, 5.5, 10500, 10500])
    assert dv == [1, 5.5, 5.5, 10500, 10500]
    assert len(architecture.get_elements_by_type(Compressor)) == 2
    assert len(architecture.get_elements_by_type(Turbine)) == 2

    architecture, _ = problem.generate_architecture([2, 5.5, 5.5, 10500, 10500])
    assert len(architecture.get_elements_by_type(Compressor)) == 3
    assert len(architecture.get_elements_by_type(Turbine)) == 3


def test_evaluate_architecture(shafts_problem):
    problem = _get_problem(shafts_problem, ShaftChoice())
    problem.print_results = True

    start = timeit.default_timer()
    dv_imputed, obj, con, met = problem.evaluate([0])  # No additional shafts
    assert obj == [pytest.approx(26.5737, abs=5e-1)]
    assert con == [pytest.approx(26.5737, abs=5e-1)]
    assert met == [pytest.approx(26.5737, abs=5e-1)]
    time = timeit.default_timer()-start

    start_cached = timeit.default_timer()
    dv_imputed2, obj, con, met = problem.evaluate([0])  # No additional shafts (cached)
    assert dv_imputed2 == dv_imputed
    assert obj == [pytest.approx(26.5737, abs=5e-1)]
    assert con == [pytest.approx(26.5737, abs=5e-1)]
    assert met == [pytest.approx(26.5737, abs=5e-1)]
    time_cached = timeit.default_timer()-start_cached
    assert time_cached < time*.01

    dv_imputed, obj, con, met = problem.evaluate([1])  # 1 additional shaft
    assert obj == [pytest.approx(21.7, abs=5e-1)]
    assert con == [pytest.approx(21.7, abs=5e-1)]
    assert met == [pytest.approx(21.7, abs=5e-1)]

    dv_imputed, obj, con, met = problem.evaluate([2])  # 2 additional shafts
    assert obj == [pytest.approx(7.3, abs=5e-1)]
    assert con == [pytest.approx(7.3, abs=5e-1)]
    assert met == [pytest.approx(7.3, abs=5e-1)]

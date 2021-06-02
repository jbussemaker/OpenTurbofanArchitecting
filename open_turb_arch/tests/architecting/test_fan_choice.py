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
def fan_an_problem():
    return AnalysisProblem(DesignCondition(
        mach=1e-6, alt=0,
        thrust=20017,  # 4500 lbf
        turbine_in_temp=1314,  # 2857 degR
        balancer=DesignBalancer(init_turbine_pr=8.36),
    ))


def _get_problem(fan_an_problem, fan_choice):
    return ArchitectingProblem(
        analysis_problem=fan_an_problem, choices=[fan_choice],
        objectives=[TSFCMetric()], constraints=[TSFCMetric()], metrics=[TSFCMetric()],
    )


def test_des_vars(fan_an_problem):
    problem = _get_problem(fan_an_problem, FanChoice())
    assert len(problem.opt_des_vars) == 3
    assert len(problem.free_opt_des_vars) == 3
    assert isinstance(problem.opt_des_vars[0], DiscreteDesignVariable)
    assert isinstance(problem.opt_des_vars[1], ContinuousDesignVariable)
    assert isinstance(problem.opt_des_vars[2], ContinuousDesignVariable)

    problem = _get_problem(fan_an_problem, FanChoice(fix_include_fan=True))
    assert len(problem.free_opt_des_vars) == 2
    assert problem.opt_des_vars[0].get_fixed_value()

    problem = _get_problem(fan_an_problem, FanChoice(fix_include_fan=False))
    assert len(problem.free_opt_des_vars) == 2
    assert not problem.opt_des_vars[0].get_fixed_value()

    problem = _get_problem(fan_an_problem, FanChoice(fixed_bpr=5., fixed_fpr=1.5))
    assert len(problem.free_opt_des_vars) == 1
    assert problem.opt_des_vars[1].get_fixed_value() == 5.
    assert problem.opt_des_vars[2].get_fixed_value() == 1.5

    full_dv, _ = problem.get_full_design_vector([0])
    assert len(full_dv) == 3
    assert full_dv[1] == 5.
    assert full_dv[2] == 1.5


def test_modify_architecture(fan_an_problem):
    problem = _get_problem(fan_an_problem, FanChoice())

    architecture, dv = problem.generate_architecture([0, 5., 1.5])
    assert len(architecture.get_elements_by_type(Compressor)) == 1
    assert dv == [0, problem.opt_des_vars[1].get_imputed_value(), problem.opt_des_vars[2].get_imputed_value()]

    architecture, dv = problem.generate_architecture([1, 5., 1.5])
    assert dv == [1, 5., 1.5]
    assert len(architecture.get_elements_by_type(Compressor)) == 2
    fan = architecture.get_elements_by_type(Compressor)[0]
    assert fan.pr == 1.5

    assert len(architecture.get_elements_by_type(Splitter)) == 1
    splitter = architecture.get_elements_by_type(Splitter)[0]
    assert splitter.bpr == 5.

    architecture, _ = problem.generate_architecture([1, 6., 1.6])
    assert len(architecture.get_elements_by_type(Compressor)) == 2
    fan = architecture.get_elements_by_type(Compressor)[0]
    assert fan.pr == 1.6

    assert len(architecture.get_elements_by_type(Splitter)) == 1
    splitter = architecture.get_elements_by_type(Splitter)[0]
    assert splitter.bpr == 6.


def test_evaluate_architecture(fan_an_problem):
    problem = _get_problem(fan_an_problem, FanChoice())
    problem.print_results = True

    start = timeit.default_timer()
    dv_imputed, obj, con, met = problem.evaluate([0, 5., 1.5])  # No fan
    assert dv_imputed == [0, problem.opt_des_vars[1].get_imputed_value(), problem.opt_des_vars[2].get_imputed_value()]
    assert obj == [pytest.approx(26.5737, abs=1e-1)]
    assert con == [pytest.approx(26.5737, abs=1e-1)]
    assert met == [pytest.approx(26.5737, abs=1e-1)]
    time = timeit.default_timer()-start

    start_cached = timeit.default_timer()
    dv_imputed2, obj, con, met = problem.evaluate([0, 6., 1.2])  # No fan (cached)
    assert dv_imputed2 == dv_imputed
    assert obj == [pytest.approx(26.5737, abs=1e-1)]
    assert con == [pytest.approx(26.5737, abs=1e-1)]
    assert met == [pytest.approx(26.5737, abs=1e-1)]
    time_cached = timeit.default_timer()-start_cached
    assert time_cached < time*.01

    dv_imputed, obj, con, met = problem.evaluate([1, 5., 1.5])  # With fan
    assert obj == [pytest.approx(11.8247, abs=1e-1)]
    assert con == [pytest.approx(11.8247, abs=1e-1)]
    assert met == [pytest.approx(11.8247, abs=1e-1)]

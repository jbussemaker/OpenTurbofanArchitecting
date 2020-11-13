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
from typing import *
from open_turb_arch.architecting.metric import *
from open_turb_arch.architecting.problem import *
from open_turb_arch.architecting.metrics import *
from open_turb_arch.architecting.opt_defs import *
from open_turb_arch.evaluation.analysis.balancer import *
from open_turb_arch.evaluation.architecture.architecture import *
from open_turb_arch.evaluation.architecture.turbomachinery import *


class CompressorPRChoice(ArchitectingChoice):

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            ContinuousDesignVariable('pr', bounds=(5., 20.)),
        ]

    def get_construction_order(self) -> int:
        """For ordering choices into the order of applying the architecture modifications."""
        return 0

    def modify_architecture(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector) \
            -> Sequence[bool]:
        """Modify the default turbojet architecture based on the given design vector. Should return for each of the
        design variables whether they are active or not."""

        pr_dv, = design_vector

        compressor = architecture.get_elements_by_type(Compressor)[0]
        compressor.pr = pr_dv

        return [True]  # is_active


def test_evaluate_architecture():
    analysis_problem = AnalysisProblem(DesignCondition(
        mach=1e-6, alt=0,
        thrust=52489,  # 11800 lbf
        turbine_in_temp=1043.5,  # 2370 degR
        balancer=DesignBalancer(init_turbine_pr=3.88),
    ), evaluate_conditions=[EvaluateCondition(
        name_='EC', mach=1e-6, alt=0,
        thrust=30000,  # 11800 lbf
        balancer=OffDesignBalancer(init_mass_flow=51.53),
    )])

    problem = ArchitectingProblem(
        analysis_problem=analysis_problem,
        choices=[CompressorPRChoice()],
        objectives=[TSFCMetric()],
        constraints=[TSFCMetric(max_tsfc=.15, condition=analysis_problem.evaluate_conditions[0])],
        metrics=[TSFCMetric()],
    )

    assert len(problem.opt_objectives) == 1
    assert problem.opt_objectives[0].dir == ObjectiveDirection.MINIMIZE

    assert len(problem.opt_constraints) == 1
    assert problem.opt_constraints[0].dir == ConstraintDirection.LOWER_EQUAL_THAN
    assert problem.opt_constraints[0].limit_value == .15

    assert len(problem.opt_metrics) == 1

    problem.print_results = True
    dv_imputed, obj, con, met = problem.evaluate([13.5])
    assert dv_imputed == [13.5]

    assert obj == [pytest.approx(22.6075, abs=1e-4)]
    assert con == [pytest.approx(20.6793, abs=1e-4)]
    assert met == [pytest.approx(22.6075, abs=1e-4)]


def test_openmdao_problem():
    analysis_problem = AnalysisProblem(DesignCondition(
        mach=1e-6, alt=0,
        thrust=52489,  # 11800 lbf
        turbine_in_temp=1043.5,  # 2370 degR
        balancer=DesignBalancer(init_turbine_pr=3.88),
    ))

    problem = ArchitectingProblem(
        analysis_problem=analysis_problem, choices=[CompressorPRChoice()],
        objectives=[TSFCMetric()], constraints=[TSFCMetric()], metrics=[TSFCMetric()],
    )

    problem.get_openmdao_component()

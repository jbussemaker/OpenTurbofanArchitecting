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
from dataclasses import dataclass
from open_turb_arch.architecting.metric import *
from open_turb_arch.architecting.problem import *
from open_turb_arch.architecting.opt_defs import *
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.analysis.balancer import *
from open_turb_arch.architecting.turbojet_architecture import *
from open_turb_arch.evaluation.architecture.architecture import *
from open_turb_arch.evaluation.architecture.turbomachinery import *
from open_turb_arch.evaluation.analysis.builder import OperatingMetrics


@pytest.fixture
def an_problem() -> AnalysisProblem:
    return AnalysisProblem(
        design_condition=DesignCondition(
            mach=1e-6, alt=0,
            thrust=52489,  # 11800 lbf
            turbine_in_temp=1043.5,  # 2370 degR
            balancer=DesignBalancer(init_turbine_pr=3.88),
        ),
        evaluate_conditions=[EvaluateCondition(
            name_='OD0',
            mach=1e-5, alt=0,
            thrust=48930.3,  # 11000 lbf
            balancer=OffDesignBalancer(init_mass_flow=66.92),
        )],
    )


def test_default_turbojet_architecture():
    architecture = get_turbojet_architecture()
    assert isinstance(architecture, TurbofanArchitecture)

    assert len(architecture.get_elements_by_type(Inlet)) == 1
    assert len(architecture.get_elements_by_type(Compressor)) == 1
    assert len(architecture.get_elements_by_type(Nozzle)) == 1

    architecture2 = get_turbojet_architecture()
    assert isinstance(architecture2, TurbofanArchitecture)
    assert architecture2 is not architecture

    assert isinstance(ArchitectingProblem._get_default_architecture(), TurbofanArchitecture)


def test_cont_des_var():
    dv = ContinuousDesignVariable('dv', bounds=(2, 4))
    assert dv.name == 'dv'
    assert dv.bounds == (2, 4)
    assert not dv.is_fixed
    assert dv.get_imputed_value() == 3

    assert dv.encode(3.5) == 3.5
    assert dv.decode(3.5) == 3.5

    for _ in range(100):
        val = dv.get_random_value()
        assert 2. <= val <= 4.

    dv_fixed = ContinuousDesignVariable('dv', bounds=(2, 4), fixed_value=3.5)
    assert dv_fixed.is_fixed
    assert dv_fixed.get_fixed_value() == 3.5


def test_int_des_var():
    dv = IntegerDesignVariable('dv', type=IntDesignVariableType.DISCRETE, values=[4, 5, 6, 7])
    assert dv.name == 'dv'
    assert dv.type == IntDesignVariableType.DISCRETE
    assert not dv.is_fixed
    assert dv.get_imputed_value() == 0

    assert dv.encode(5) == 1
    assert dv.decode(1) == 5

    with pytest.raises(ValueError):
        dv.encode(8)
    with pytest.raises(IndexError):
        dv.decode(-1)
    with pytest.raises(IndexError):
        dv.decode(4)

    for _ in range(100):
        val = dv.get_random_value()
        assert val in dv.values

        assert dv.decode(dv.encode(val)) == val

    dv_fixed = IntegerDesignVariable('dv', type=IntDesignVariableType.CATEGORICAL, values=[1, 2, 3], fixed_value=2)
    assert dv_fixed.is_fixed
    assert dv_fixed.get_fixed_value() == 2

    with pytest.raises(ValueError):
        IntegerDesignVariable('dv', type=IntDesignVariableType.CATEGORICAL, values=[2, 3, 4], fixed_value=5)\
            .get_fixed_value()


class DummyChoice(ArchitectingChoice):

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            ContinuousDesignVariable('dv1', bounds=(5., 20.)),
            IntegerDesignVariable('dv2', type=IntDesignVariableType.DISCRETE, values=[1, 2, 3, 4], fixed_value=3),
            IntegerDesignVariable('dv3', type=IntDesignVariableType.CATEGORICAL, values=[5, 4, 3]),
        ]

    def get_construction_order(self) -> int:
        """For ordering choices into the order of applying the architecture modifications."""
        return 0

    def modify_architecture(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector) \
            -> Sequence[bool]:
        """Modify the default turbojet architecture based on the given design vector. Should return for each of the
        design variables whether they are active or not."""

        dv1, dv2, dv3 = design_vector

        compressor = architecture.get_elements_by_type(Compressor)[0]
        compressor.pr = dv1

        return [True, True, False]  # is_active


@dataclass
class DummyMetric(ArchitectingMetric):

    condition: OperatingCondition = None

    def get_opt_objectives(self, choices: List[ArchitectingChoice]) -> List[Objective]:
        return [Objective('obj', dir=ObjectiveDirection.MINIMIZE)]

    def get_opt_constraints(self, choices: List[ArchitectingChoice]) -> List[Constraint]:
        return [Constraint('con', dir=ConstraintDirection.LOWER_EQUAL_THAN, limit_value=.05)]

    def get_opt_metrics(self, choices: List[ArchitectingChoice]) -> List[OutputMetric]:
        return [OutputMetric('met')]

    def extract_met(self, analysis_problem: AnalysisProblem, result: OperatingMetricsMap) -> Sequence[float]:
        condition = self.condition or analysis_problem.design_condition
        return [result[condition].tsfc]


def test_problem(an_problem):
    with pytest.raises(RuntimeError):
        ArchitectingProblem(an_problem, choices=[], objectives=[DummyMetric()])
    with pytest.raises(RuntimeError):
        ArchitectingProblem(an_problem, choices=[DummyChoice()], objectives=[])

    problem = ArchitectingProblem(
        analysis_problem=an_problem,
        choices=[DummyChoice()],
        objectives=[DummyMetric()],
        constraints=[DummyMetric(condition=an_problem.evaluate_conditions[0])],
        metrics=[DummyMetric()],
    )

    assert problem.analysis_problem is an_problem
    assert len(problem.choices) == 1
    assert len(problem.objectives) == 1
    assert len(problem.constraints) == 1
    assert len(problem.metrics) == 1

    assert len(problem.opt_des_vars) == 3
    assert all([isinstance(dv, DesignVariable) for dv in problem.opt_des_vars])
    assert len(problem.free_opt_des_vars) == 2

    assert len(problem.get_random_design_vector()) == 2

    assert len(problem.opt_objectives) == 1
    assert all([isinstance(obj, Objective) for obj in problem.opt_objectives])
    assert len(problem.opt_constraints) == 1
    assert all([isinstance(con, Constraint) for con in problem.opt_constraints])
    assert len(problem.opt_metrics) == 1
    assert all([isinstance(met, OutputMetric) for met in problem.opt_metrics])


def test_design_vector(an_problem):
    problem = ArchitectingProblem(an_problem, choices=[DummyChoice()], objectives=[DummyMetric()])
    dv1: ContinuousDesignVariable
    dv2: IntegerDesignVariable
    dv3: IntegerDesignVariable
    dv1, dv2, dv3 = problem.opt_des_vars

    for _ in range(100):
        dvs = problem.get_random_design_vector()
        assert len(dvs) == 2

        full_dv, des_value_vector = problem.get_full_design_vector(dvs)
        assert len(full_dv) == 3
        assert len(des_value_vector) == 3

        assert dv1.bounds[0] <= full_dv[0] <= dv1.bounds[1]
        assert dv2.decode(full_dv[1]) == dv2.fixed_value
        assert dv3.decode(full_dv[2]) in dv3.values

        assert dv1.bounds[0] <= des_value_vector[0] <= dv1.bounds[1]
        assert des_value_vector[1] == dv2.fixed_value
        assert des_value_vector[2] in dv3.values

        free_dv = problem.get_free_design_vector(full_dv)
        assert len(free_dv) == 2
        assert free_dv[0] == full_dv[0]
        assert free_dv[1] == full_dv[2]


def test_generate_architecture(an_problem):
    problem = ArchitectingProblem(an_problem, choices=[DummyChoice()], objectives=[DummyMetric()])

    for _ in range(100):
        dv = problem.get_random_design_vector()

        architecture, free_des_vector = problem.generate_architecture(dv)
        assert isinstance(architecture, TurbofanArchitecture)
        assert len(free_des_vector) == len(dv)

        compressor = architecture.get_elements_by_type(Compressor)[0]
        assert compressor.pr == dv[0]

        assert free_des_vector[1] == problem.free_opt_des_vars[1].get_imputed_value()


class ArchitectureProblemTester(ArchitectingProblem):

    def evaluate_architecture(self, architecture: TurbofanArchitecture) -> Dict[OperatingCondition, OperatingMetrics]:
        compressor = architecture.get_elements_by_type(Compressor)[0]
        return {
            self.analysis_problem.design_condition: OperatingMetrics(tsfc=.10*compressor.pr),
            self.analysis_problem.evaluate_conditions[0]: OperatingMetrics(tsfc=.15*compressor.pr),
        }


def test_evaluate(an_problem):
    problem = ArchitectureProblemTester(
        analysis_problem=an_problem,
        choices=[DummyChoice()],
        objectives=[DummyMetric()],
        constraints=[DummyMetric(condition=an_problem.evaluate_conditions[0])],
        metrics=[DummyMetric()],
    )

    for _ in range(100):
        dv = problem.get_random_design_vector()

        free_des_vector, obj, con, met = problem.evaluate(dv)
        assert len(free_des_vector) == len(dv)
        assert free_des_vector[1] == problem.free_opt_des_vars[1].get_imputed_value()

        assert obj == [.10*dv[0]]
        assert con == [.15*dv[0]]
        assert met == [.10*dv[0]]

        assert tuple(free_des_vector) in problem._results_cache


def test_evaluate_architecture(an_problem):
    problem = ArchitectingProblem(
        analysis_problem=AnalysisProblem(design_condition=an_problem.design_condition),
        choices=[DummyChoice()],
        objectives=[DummyMetric()],
        constraints=[DummyMetric()],
        metrics=[DummyMetric()],
    )

    dv = problem.get_random_design_vector()
    dv[0] = 13.5  # Compressor PR

    problem.print_results = True
    dv_imputed, obj, con, met = problem.evaluate(dv)
    assert len(dv_imputed) == len(dv)
    assert dv_imputed[0] == dv[0]

    assert obj == [pytest.approx(22.6075, abs=1e-4)]
    assert con == [pytest.approx(22.6075, abs=1e-4)]
    assert met == [pytest.approx(22.6075, abs=1e-4)]

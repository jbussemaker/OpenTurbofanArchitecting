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
import numpy as np
from typing import *
from dataclasses import dataclass
from open_turb_arch.architecting.pymoo import *
from open_turb_arch.architecting.metric import *
from open_turb_arch.architecting.problem import *
from open_turb_arch.architecting.opt_defs import *
from open_turb_arch.architecting.platypus import *
from open_turb_arch.architecting.openmdao import *
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
            IntegerDesignVariable('dv4', type=IntDesignVariableType.CATEGORICAL, values=[8, 7, 6]),
        ]

    def get_construction_order(self) -> int:
        """For ordering choices into the order of applying the architecture modifications."""
        return 0

    def modify_architecture(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector) \
            -> Sequence[Union[bool, DecodedValue]]:
        """Modify the default turbojet architecture based on the given design vector. Should return for each of the
        design variables whether they are active or not."""

        dv1, dv2, dv3, dv4 = design_vector

        compressor = architecture.get_elements_by_type(Compressor)[0]
        compressor.pr = dv1

        return [True, True, False, 7]  # is_active or overwrite


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

    assert len(problem.opt_des_vars) == 4
    assert all([isinstance(dv, DesignVariable) for dv in problem.opt_des_vars])
    assert len(problem.free_opt_des_vars) == 3

    assert len(problem.get_random_design_vector()) == 3

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
    dv4: IntegerDesignVariable
    dv1, dv2, dv3, dv4 = problem.opt_des_vars

    for _ in range(100):
        dvs = problem.get_random_design_vector()
        assert len(dvs) == 3

        full_dv, des_value_vector = problem.get_full_design_vector(dvs)
        assert len(full_dv) == 4
        assert len(des_value_vector) == 4

        assert dv1.bounds[0] <= full_dv[0] <= dv1.bounds[1]
        assert dv2.decode(full_dv[1]) == dv2.fixed_value
        assert dv3.decode(full_dv[2]) in dv3.values
        assert dv4.decode(full_dv[3]) in dv4.values

        assert dv1.bounds[0] <= des_value_vector[0] <= dv1.bounds[1]
        assert des_value_vector[1] == dv2.fixed_value
        assert des_value_vector[2] in dv3.values
        assert des_value_vector[3] in dv4.values

        free_dv = problem.get_free_design_vector(full_dv)
        assert len(free_dv) == 3
        assert free_dv[0] == full_dv[0]
        assert free_dv[1] == full_dv[2]
        assert free_dv[2] == full_dv[3]

    for n_cont in [5, 1]:
        n_dv = 0
        for dvs in problem.iter_design_vectors(n_cont=n_cont):
            n_dv += 1
            assert len(dvs) == 3

            full_dv, des_value_vector = problem.get_full_design_vector(dvs)
            assert len(full_dv) == 4
            assert len(des_value_vector) == 4

        assert n_dv == n_cont*3*3  # 3 for dv3 and dv4 (dv2 is fixed)


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
        assert free_des_vector[2] == problem.free_opt_des_vars[2].encode(7)

    n_dv = 0
    unique_dvs = set()
    for dv in problem.iter_design_vectors(n_cont=5):
        n_dv += 1
        architecture, imputed_dv = problem.generate_architecture(dv)
        assert isinstance(architecture, TurbofanArchitecture)
        assert len(imputed_dv) == len(dv)

        unique_dvs.add(tuple(imputed_dv))

    assert len(unique_dvs) < n_dv


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
        assert free_des_vector[2] == 1

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

    assert obj == [pytest.approx(22.6075, abs=1e-1)]
    assert con == [pytest.approx(22.6075, abs=1e-1)]
    assert met == [pytest.approx(22.6075, abs=1e-1)]


def test_platypus_problem(an_problem):
    from platypus.core import Solution
    from platypus.types import Real, Integer
    from platypus.operators import RandomGenerator

    problem = ArchitectureProblemTester(
        analysis_problem=an_problem,
        choices=[DummyChoice()],
        objectives=[DummyMetric()],
        constraints=[DummyMetric(condition=an_problem.evaluate_conditions[0])],
        metrics=[DummyMetric()],
    )

    platypus_problem = problem.get_platypus_problem()
    assert isinstance(platypus_problem, PlatypusArchitectingProblem)
    assert platypus_problem.nvars == 3
    assert platypus_problem.nobjs == 1
    assert platypus_problem.nconstrs == 1

    assert isinstance(platypus_problem.types[0], Real)
    assert platypus_problem.types[0].min_value == 5.
    assert platypus_problem.types[0].max_value == 20.

    assert isinstance(platypus_problem.types[1], Integer)
    assert platypus_problem.types[1].min_value == 0
    assert platypus_problem.types[1].max_value == 2

    assert isinstance(platypus_problem.types[2], Integer)
    assert platypus_problem.types[2].min_value == 0
    assert platypus_problem.types[2].max_value == 2

    assert platypus_problem.directions[0] == -1
    assert platypus_problem.constraints[0].op == '<=0.05'

    generator = RandomGenerator()
    for _ in range(100):
        sol: Solution = generator.generate(platypus_problem)
        dv1 = sol.variables[0]
        assert not sol.evaluated

        platypus_problem(sol)
        assert sol.evaluated
        assert platypus_problem.types[1].decode(sol.variables[1]) == 0
        assert platypus_problem.types[2].decode(sol.variables[2]) == 1

        assert sol.objectives[:] == [.10*dv1]
        assert sol.constraints[:] == [.15*dv1]


def test_openmdao_component(an_problem):
    import openmdao.api as om

    problem = ArchitectureProblemTester(
        analysis_problem=an_problem,
        choices=[DummyChoice()],
        objectives=[DummyMetric()],
        constraints=[DummyMetric(condition=an_problem.evaluate_conditions[0])],
        metrics=[DummyMetric()],
    )

    comp = problem.get_openmdao_component()
    assert isinstance(comp, ArchitectingProblemComponent)
    assert comp.des_var_names == [dv.name for dv in problem.free_opt_des_vars]
    assert comp.obj_names == [obj.name for obj in problem.opt_objectives]
    assert comp.con_names == [con.name for con in problem.opt_constraints]
    assert comp.met_names == [met.name for met in problem.opt_metrics]

    om_prob = om.Problem()
    om_prob.driver = driver = om.SimpleGADriver()
    driver.options['max_gen'] = 10
    om_prob.model = comp
    om_prob.setup()
    om_prob.final_setup()

    cont_x_names = [dv.name for dv in problem.free_opt_des_vars if isinstance(dv, ContinuousDesignVariable)]
    dis_x_names = [dv.name for dv in problem.free_opt_des_vars if isinstance(dv, IntegerDesignVariable)]
    assert len(cont_x_names) > 0
    assert len(dis_x_names) > 0

    assert {name for name in comp._outputs} == set(comp.obj_names+comp.con_names+comp.met_names+cont_x_names)
    assert {name for name in comp._var_discrete['output']} == set(dis_x_names)
    assert {name for name in comp.get_design_vars()} == set(comp.des_var_names)
    assert {name for name in comp.get_objectives()} == set(comp.obj_names)
    assert {name for name in comp.get_constraints()} == set(comp.con_names)

    i_cont = [i for i, dv in enumerate(problem.free_opt_des_vars) if isinstance(dv, ContinuousDesignVariable)]
    i_dis = [i for i in range(len(problem.free_opt_des_vars)) if i not in i_cont]

    n_imputed = 0
    for _ in range(100):
        dv = problem.get_random_design_vector()
        discrete_outputs = {name: dv[i] for i, name in enumerate(comp.des_var_names) if i in i_dis}
        orig_discrete_outputs = discrete_outputs.copy()
        outputs = {name: dv[i] for i, name in enumerate(comp.des_var_names) if i in i_cont}

        comp.compute({}, outputs, discrete_outputs=discrete_outputs)
        n_imputed += 1 if orig_discrete_outputs != discrete_outputs else 0

        assert outputs[comp.obj_names[0]] == .10*dv[0]
        assert outputs[comp.con_names[0]] == .15*dv[0]

    assert n_imputed > 0

    om_prob.run_driver()


def test_pymoo_problem(an_problem):
    from pymoo.model.evaluator import Evaluator
    from pymoo.operators.sampling.random_sampling import FloatRandomSampling

    problem = ArchitectureProblemTester(
        analysis_problem=an_problem,
        choices=[DummyChoice()],
        objectives=[DummyMetric()],
        constraints=[DummyMetric(condition=an_problem.evaluate_conditions[0])],
        metrics=[DummyMetric()],
    )

    pymoo_problem = problem.get_pymoo_problem()
    assert isinstance(pymoo_problem, PymooArchitectingProblem)
    assert pymoo_problem.n_var == 3
    assert pymoo_problem.n_obj == 1
    assert pymoo_problem.n_constr == 1

    assert list(pymoo_problem.xl) == [5., 0., 0.]
    assert list(pymoo_problem.xu) == [20., 2., 2.]
    assert pymoo_problem.mask == ['real', 'int', 'int']
    assert pymoo_problem.is_int_mask == [False, True, True]

    assert pymoo_problem.obj_is_max == [False]
    assert pymoo_problem.con_ref == [(False, .05)]

    sampling = FloatRandomSampling()
    pop = sampling.do(pymoo_problem, 100)
    assert len(pop) == 100

    evaluator = Evaluator()
    evaluator.eval(pymoo_problem, pop)

    x = pop.get('X')
    assert x.shape == (100, 3)
    dv1 = x[:, 0]
    assert np.all(x[:, 1] == 0)
    assert np.all(x[:, 2] == 1)

    assert all([pop[i].F is not None for i in range(len(pop))])
    f = pop.get('F')
    assert f.shape == (100, 1)
    assert np.all(f[:, 0] == (.10*dv1))

    g = pop.get('G')
    assert g.shape == (100, 1)
    assert np.all(g[:, 0] == (.15*dv1-.05))

    repair = pymoo_problem.get_repair()
    pop = sampling.do(pymoo_problem, 100)
    x1 = pop.get('X')[:, 1]
    assert not np.all(np.round(x1) == x1)

    pop_repaired = repair.do(pymoo_problem, pop)
    x1 = pop_repaired.get('X')[:, 1]
    assert np.all(np.round(x1) == x1)

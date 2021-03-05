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

Copyright: (c) 2021, Deutsches Zentrum fuer Luft- und Raumfahrt e.V.
Contact: jasper.bussemaker@dlr.de
"""

import numpy as np
from typing import *
from pymoo.model.repair import Repair
from pymoo.model.problem import Problem
from pymoo.model.population import Population
from open_turb_arch.architecting.problem import *
from open_turb_arch.architecting.opt_defs import *

__all__ = ['PymooArchitectingProblem', 'ArchitectingProblemRepair']


class PymooArchitectingProblem(Problem):
    """
    Pymoo (https://pymoo.org/) wrapper for an architecting problem.

    Example usage:
    ```
    from pymoo.optimize import minimize
    from pymoo.algorithms.nsga2 import NSGA2

    algorithm = NSGA2(pop_size=100)
    problem = PymooArchitectingProblem(architecting_problem)

    result = minimize(problem, algorithm, termination=('n_eval', 500))
    ```
    """

    def __init__(self, problem: ArchitectingProblem):
        self.problem = problem

        n_vars = len(problem.free_opt_des_vars)
        if n_vars == 0:
            raise ValueError('No free design variables in optimization problem!')
        n_objs = len(problem.opt_objectives)
        if n_objs == 0:
            raise ValueError('No objectives in optimization problem!')
        n_constr = len(problem.opt_constraints)

        xl, xu, self.mask, is_int_mask, is_cat_mask = self._process_des_vars(problem.free_opt_des_vars)
        self.is_int_mask = np.array(is_int_mask)
        self.is_cat_mask = np.array(is_cat_mask)
        self.is_discrete_mask = np.bitwise_or(self.is_int_mask, self.is_cat_mask)
        self.is_cont_mask = ~self.is_discrete_mask

        super(PymooArchitectingProblem, self).__init__(n_vars, n_objs, n_constr, xl=xl, xu=xu)

        self.obj_is_max = [obj.dir == ObjectiveDirection.MAXIMIZE for obj in problem.opt_objectives]
        self.con_ref = [(con.dir == ConstraintDirection.GREATER_EQUAL_THAN, con.limit_value)
                        for con in problem.opt_constraints]

    def get_repair(self) -> Repair:
        return ArchitectingProblemRepair(self.is_discrete_mask)

    @staticmethod
    def _process_des_vars(des_vars: List[DesignVariable]) -> Tuple[np.ndarray, np.ndarray, list, list, list]:
        """Determines: lower bounds, upper, bounds, mask (int or real), is_int_mask (bool)"""
        xl, xu = np.empty((len(des_vars),)), np.empty((len(des_vars),))
        mask = []
        is_int_mask = []
        is_cat_mask = []

        for i, des_var in enumerate(des_vars):
            if isinstance(des_var, DiscreteDesignVariable):
                xl[i], xu[i] = 0, len(des_var.values)-1

                if des_var.type == DiscreteDesignVariableType.INTEGER:
                    mask.append('int')
                    is_int_mask += [True]
                    is_cat_mask += [False]

                elif des_var.type == DiscreteDesignVariableType.CATEGORICAL:
                    mask.append('cat')
                    is_int_mask += [False]
                    is_cat_mask += [True]

                else:
                    raise ValueError('Unknown discrete design variable type!')

                continue

            if isinstance(des_var, ContinuousDesignVariable):
                xl[i], xu[i] = des_var.bounds
                mask.append('real')
                is_int_mask += [False]
                is_cat_mask += [False]
                continue

            raise NotImplementedError

        return xl, xu, mask, is_int_mask, is_cat_mask

    def _evaluate(self, x, out, *args, **kwargs):
        # Correct integer design variables
        is_discrete_mask = self.is_discrete_mask
        x = ArchitectingProblemRepair.correct_x(x, is_discrete_mask)

        # Evaluate the architecture
        n = x.shape[0]
        x_out = np.empty((n, self.n_var))
        f_out = np.empty((n, self.n_obj))
        g_out = np.empty((n, self.n_constr)) if self.n_constr > 0 else None

        for i in range(n):
            x_arch = [int(val) if is_discrete_mask[j] else float(val) for j, val in enumerate(x[i, :])]
            imputed_design_vector, objectives, constraints, _ = self.problem.evaluate(x_arch)

            # Correct directions of objectives to represent minimization
            objectives = [-val if self.obj_is_max[j] else val for j, val in enumerate(objectives)]

            # Correct directions and offset constraints to represent g(x) <= 0
            constraints = [(val-self.con_ref[j][1])*(-1 if self.con_ref[j][0] else 1)
                           for j, val in enumerate(constraints)]

            x_out[i, :] = [float(val) for val in imputed_design_vector]
            f_out[i, :] = objectives
            if len(constraints) > 0:
                g_out[i, :] = constraints

        # Set output
        out['X'] = x_out
        out['F'] = f_out
        if self.n_constr > 0:
            out['G'] = g_out


class ArchitectingProblemRepair(Repair):
    """Repair operating to make sure that integer variables are actually integers after sampling or mating."""

    def __init__(self, is_discrete_mask):
        super(ArchitectingProblemRepair, self).__init__()

        self.is_discrete_mask = is_discrete_mask

    def _do(self, problem: Problem, pop: Union[Population, np.ndarray], **kwargs):
        is_array = not isinstance(pop, Population)
        x = pop if is_array else pop.get("X")

        x = self.correct_x(x, self.is_discrete_mask)

        if is_array:
            return x
        pop.set("X", x)
        return pop

    @staticmethod
    def correct_x(x: np.ndarray, is_discrete_mask) -> np.ndarray:
        x = np.copy(x)
        x[:, is_discrete_mask] = np.round(x[:, is_discrete_mask].astype(np.float64)).astype(np.int)
        return x

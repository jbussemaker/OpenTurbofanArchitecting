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

from multiprocessing import current_process
from platypus.types import Type, Real, Integer
from open_turb_arch.architecting.problem import *
from open_turb_arch.architecting.opt_defs import *
from platypus.core import Problem, Constraint as PlatypusConstraint, Solution

__all__ = ['PlatypusArchitectingProblem']


class PlatypusArchitectingProblem(Problem):
    """
    Platypus (https://platypus.readthedocs.io/) wrapper for an architecting problem. This class contains all information
    for Platypus to run an optimization problem.
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
        super(PlatypusArchitectingProblem, self).__init__(n_vars, n_objs, n_constr)

        # Set design variable types
        self.types[:] = [self._get_des_var_type(des_var) for des_var in problem.free_opt_des_vars]

        # Set objective directions
        self.directions[:] = [1 if obj.dir == ObjectiveDirection.MAXIMIZE else -1 for obj in problem.opt_objectives]

        # Set constraints
        if n_constr > 0:
            self.constraints[:] = [self._get_constraint(con) for con in problem.opt_constraints]

    @staticmethod
    def _is_parallel():
        # https://stackoverflow.com/a/18298473
        return current_process().name != 'MainProcess'

    @staticmethod
    def _get_des_var_type(design_var: DesignVariable) -> Type:
        if isinstance(design_var, IntegerDesignVariable):
            return Integer(0, len(design_var.values)-1)

        elif isinstance(design_var, ContinuousDesignVariable):
            return Real(*design_var.bounds)

        raise NotImplementedError

    @staticmethod
    def _get_constraint(constraint: Constraint) -> PlatypusConstraint:
        ops = '>=' if constraint.dir == ConstraintDirection.GREATER_EQUAL_THAN else '<='
        return PlatypusConstraint(ops, value=constraint.limit_value)

    def evaluate(self, solution: Solution):
        # Evaluate architecture
        decoded_design_vector = solution.variables[:]
        imputed_design_vector, objectives, constraints, _ = self.problem.evaluate(decoded_design_vector)

        # Process results
        solution.variables[:] = imputed_design_vector
        solution.objectives[:] = objectives
        solution.constraints[:] = constraints

        # Unset the underlying problem if we are in a parallel process to save memory
        if self._is_parallel():
            self.problem = None

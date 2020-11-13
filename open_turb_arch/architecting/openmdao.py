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

import numpy as np
import openmdao.api as om
from open_turb_arch.architecting.problem import *
from open_turb_arch.architecting.opt_defs import *

__all__ = ['ArchitectingProblemComponent']


class ArchitectingProblemComponent(om.ExplicitComponent):
    """
    OpenMDAO (https://openmdao.org/) wrapper for an architecting problem. An explicit component is made and design
    variables and such are automatically declared.
    """

    def __init__(self, problem: ArchitectingProblem):
        super(ArchitectingProblemComponent, self).__init__()

        self.problem = problem

        self.des_var_names = x_names = [des_var.name for des_var in problem.free_opt_des_vars]
        if len(x_names) == 0 or len(set(x_names)) != len(x_names):
            raise ValueError('There should be at least one design variable and no duplicates: %r' % x_names)

        self.obj_names = f_names = [obj.name for obj in problem.opt_objectives]
        if len(f_names) == 0 or len(set(f_names)) != len(f_names):
            raise ValueError('There should be at least one objective and no duplicates: %r' % f_names)

        self.con_names = g_names = [con.name for con in problem.opt_constraints]
        if len(set(g_names)) != len(g_names):
            raise ValueError('Duplicate constraint names not allowed: %r' % g_names)

        self.met_names = y_names = [met.name for met in problem.opt_metrics]
        if len(set(y_names)) != len(y_names):
            raise ValueError('Duplicate output metric names not allowed: %r' % y_names)

        all_output = f_names+g_names+y_names
        if len(set(all_output)) != len(all_output):
            raise ValueError('Duplicate output names not allowed: %r' % all_output)

    def setup(self):
        self._declare_input()
        self._declare_output()

    def _declare_input(self):
        des_vars = self.problem.free_opt_des_vars
        for i, name in enumerate(self.des_var_names):
            des_var = des_vars[i]
            if isinstance(des_var, IntegerDesignVariable):
                lower, upper = 0, len(des_var.values)-1
                is_discrete = True
            elif isinstance(des_var, ContinuousDesignVariable):
                lower, upper = des_var.bounds
                is_discrete = False
            else:
                raise ValueError('Unknown des var type: %r' % des_var)

            # Add output (for imputation)
            if is_discrete:
                self.add_discrete_output(name, val=0)
            else:
                self.add_output(name, val=0)

            # Mark as design variable
            self.add_design_var(name, lower=lower, upper=upper)

    def _declare_output(self):
        objectives = self.problem.opt_objectives
        for i, name in enumerate(self.obj_names):
            obj = objectives[i]

            # Invert if maximization: OpenMDAO only supports minimization
            scaler = -1. if obj.dir == ObjectiveDirection.MAXIMIZE else 1.

            # Add output and mark as objective
            self.add_output(name)
            self.add_objective(name, scaler=scaler)

        constraints = self.problem.opt_constraints
        for i, name in enumerate(self.con_names):
            con = constraints[i]

            upper = lower = None
            if con.dir == ConstraintDirection.GREATER_EQUAL_THAN:
                lower = con.limit_value
            else:
                upper = con.limit_value

            # Add output and mark as constraint
            self.add_output(name)
            self.add_constraint(name, upper=upper, lower=lower)

        # Generic outputs
        for name in self.met_names:
            self.add_output(name)

    def compute(self, inputs, outputs, discrete_inputs=None, discrete_outputs=None):
        # Evaluate architecture
        imputed_design_vector, objective_values, constraint_values, metric_values = \
            self.problem.evaluate(self._get_design_vector(outputs, discrete_outputs))

        # Update design variables
        for i, name in enumerate(self.des_var_names):
            if name in outputs:
                outputs[name] = imputed_design_vector[i]
            else:
                discrete_outputs[name] = imputed_design_vector[i]

        # Output evaluation results
        for i, name in enumerate(self.obj_names):
            outputs[name] = objective_values[i]

        for i, name in enumerate(self.con_names):
            outputs[name] = constraint_values[i]

        for i, name in enumerate(self.met_names):
            outputs[name] = metric_values[i]

    def _get_design_vector(self, outputs, discrete_outputs) -> DesignVector:
        if discrete_outputs is None:
            discrete_outputs = {}

        design_vector = []
        for name in self.des_var_names:
            if name in outputs:
                design_vector.append(np.atleast_1d(outputs[name])[0])
            elif discrete_outputs is not None and name in discrete_outputs:
                design_vector.append(discrete_outputs[name])
            else:
                raise ValueError('Design variable not found: %s' % name)
        return design_vector

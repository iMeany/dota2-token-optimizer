
import pandas as pd
import streamlit as st
from ortools.linear_solver import pywraplp
from PIL import Image

@st.cache_data
def load_hero_token_data():
    return pd.read_csv("data/heroes.csv", index_col=0)

@st.cache_resource
def load_token_images():
    img = Image.open("assets/tokens2.png")
    sprite_size = 130
    token_images = []
    for i in range(0, img.width, sprite_size):
        for j in range(0, img.height, sprite_size):
            token = img.crop((i, j, i + sprite_size, j + sprite_size))
            token_images.append(token)
    return token_images
    
# @st.cache_data # if we dont cache we get different results on recalculation
def integer_linear_solver(val_df, requirements, cost_col, optimization_problem_type):
    """Solves the integer linear problem with the given requirements and cost column."""
    solver = pywraplp.Solver.CreateSolver(optimization_problem_type)
    if not solver:
        return
    print("Solving with " + optimization_problem_type)

    infinity = solver.infinity()

    # Variables and constraints
    variables = []
    for idx, row in val_df.iterrows():
        variables.append(solver.IntVar(0, infinity, f"{idx}"))
    constraints = []
    for i, (token, required) in enumerate(requirements):
        constraints.append(solver.Constraint(required, infinity))
        for j, row in val_df.iterrows():
            # print(i, j, variables[val_df.index.get_loc(j)], row[token])
            constraints[i].SetCoefficient(
                var=variables[val_df.index.get_loc(j)], coeff=int(row[token])
            )

    # Objective and cost
    objective = solver.Objective()
    for i, row in val_df.iterrows():
        objective.SetCoefficient(
            var=variables[val_df.index.get_loc(i)],
            coeff=float(row[cost_col]),
        )
    objective.SetMinimization()

    # Solve
    print("Number of variables = %d" % solver.NumVariables())
    print("Number of constraints = %d" % solver.NumConstraints())

    result_status = solver.Solve()

    # The problem has an optimal solution.
    assert result_status == pywraplp.Solver.OPTIMAL

    # The solution looks legit (when using solvers others than
    # GLOP_LINEAR_PROGRAMMING, verifying the solution is highly recommended!).
    assert solver.VerifySolution(1e-7, True)

    print("Problem solved in %f milliseconds" % solver.wall_time())

    # The objective value of the solution.
    print("Optimal objective value = %f" % solver.Objective().Value())

    # The value of each variable in the solution.
    result_df = pd.DataFrame(columns=["Matches"])
    for variable in variables:
        if variable.solution_value() > 0:
            print("%s = %f" % (variable.name(), variable.solution_value()))
            # all the tokens from original dataframe + matches number from solution_value
            row = val_df.loc[variable.name()].copy()
            row["Matches"] = variable.solution_value()
            result_df = pd.concat([result_df, row.to_frame().T])

    print("Advanced usage:")
    print("Problem solved in %d branch-and-bound nodes" % solver.nodes())
    print("\n")
    return result_df


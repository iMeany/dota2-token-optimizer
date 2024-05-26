
import pandas as pd
import streamlit as st
from ortools.linear_solver import pywraplp
from PIL import Image

@st.cache_data
def load_hero_token_data():
    return pd.read_csv("data/heroes.csv", index_col=0)

@st.cache_data
def load_act_images(token_order):
    act_token_images = []
    for idx, act_tokens in enumerate(token_order):
        token_images = _load_token_images(act_tokens=act_tokens, act_nr=idx+1)
        act_token_images.append(token_images)
    return act_token_images

@st.cache_data
def _load_token_images(act_tokens, act_nr=1):
    img = Image.open(f"assets/tokens{act_nr}.png")
    token_dims = [(106, 90), (101, 91)]
    sprite_h = token_dims[act_nr-1][0]
    sprite_w = token_dims[act_nr-1][1]
    token_images = []
    for i in range(0, img.height, sprite_h):
        for j in range(0, img.width, sprite_w):
            if len(token_images) >= 18:
                break
            token_images.append(img.crop((j, i, j+sprite_w, i+sprite_h)))
    return dict(zip(act_tokens, token_images))

def get_col_grid(img_per_col=9):
    columns = st.columns(spec=img_per_col)
    columns = columns + st.columns(img_per_col)
    return columns

# @st.cache_data # if we dont cache we get different results on recalculation
def integer_linear_solver(val_df, requirements, cost_col, optimization_problem_type="SAT"):
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
    # only keep requirements > 0
    requirements = [(token, required) for token, required in requirements if required > 0]
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
    if result_status != pywraplp.Solver.OPTIMAL:
        print("The problem does not have an optimal solution!")
        if result_status == pywraplp.Solver.FEASIBLE:
            print("A potentially suboptimal solution was found.")
        else:
            print(result_status)
            return pd.DataFrame()

    print("Problem solved in %f milliseconds" % solver.wall_time())

    # The objective value of the solution.
    print("Optimal objective value = %f" % solver.Objective().Value())

    # The value of each variable in the solution.
    result_df = pd.DataFrame(columns=["Matches"], dtype=int)
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


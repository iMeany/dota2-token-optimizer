import streamlit as st
import pandas as pd
from ortools.linear_solver import pywraplp

st.set_page_config(page_title="Dota2 Crownfall Token optimization", layout="wide")

# * Header
st.write("# Dota2 Crownfall Token optimization")
st.write("Optimal hero selection for gathering tokens.")

# * Editable Hero token table 
@st.cache_resource
def load_hero_token_data():
    return pd.read_csv("data/heroes.csv", index_col=0)
df = load_hero_token_data().iloc[:, :-1]
st.write("""## Heroes and tokens
This table shows the heroes and tokens you get for winning a match.  
* Normal/Ranked games give +3 tokens for a win, +1 token for a loss.  
* Turbo gives +2 out of 3 random tokens on a win, 0 on a loss.  
* The `Playability` column is the individual difficulty of the hero. The algorithm uses this as a *cost* and tries to minimize it.
* **You can edit the table and **increase** the number if you want the hero to be less likely to be chosen.**  
""")
#  You **can** edit the table below in case some tokens are mapped wrong, on refresh it reloads to default.
edited_df = st.data_editor(df, disabled=df.columns[1:].tolist())

# * Required token selection 
st.write("## Required Token selection")
unique_token_list = df.columns[1:].values.tolist()
# splitting into multiple columns/rows for smaller screens
nr_per_row = 6
token_cell = []
for i in range(0, len(unique_token_list), nr_per_row):
    if i + nr_per_row < len(unique_token_list):
        token_cell.extend(st.columns(nr_per_row))
    else:
        token_cell.extend(st.columns(len(unique_token_list) - i))

emojis = ["🛗", "💥", "🛟", "❤️", "🚶‍♂️", "🐴", "🕷️", "🏃‍♂️", "🏹", "🪽", "⛔️", "🛡️", "👊", "🗼", "🦘", "🐍", "🥷", "🥊"]
token_input = []
for idx, col in enumerate(token_cell):
    cell = col.container()
    with cell:
        with st.container(border=True):
            token_input += [
                st.number_input(
                    label=f"{emojis[idx]} {unique_token_list[idx]}",
                    min_value=0,
                    step=1,
                    help=unique_token_list[idx],
                )
            ]

required_tokens = [[token, value] for token, value in zip(unique_token_list, token_input)]

# * Optimal hero selection
st.write("### Optimal hero selection")
# TODO: replace with integer type Cpp API solver (https://github.com/google/or-tools/blob/stable/examples/notebook/examples/integer_programming.ipynb)
@st.cache_data
def linear_solver(variables_df, requirements):
    """Material optimization problem"""
    solver = pywraplp.Solver.CreateSolver("GLOP")

    print("[Variables & Constraints]")
    # Create the variables to use
    variables = []
    for idx, row in variables_df.iterrows():
        variables.append(solver.NumVar(0.0, solver.infinity(), idx))
    print("Number of variables =", solver.NumVariables())

    constraints = []
    for idx, req in enumerate(requirements):
        print("    Adding constraint", req[0], ">=", req[1])
        constraints.append(solver.Constraint(req[1], solver.infinity()))
        for j, var_row in variables_df.iterrows():
            # print(f"    Adding coefficients for {j} * {var_row[req[0]]} to constraint {req[0]} {variables_df.index.get_loc(j)}")
            if var_row[req[0]] > 0:
                constraints[idx].SetCoefficient(
                    var=variables[variables_df.index.get_loc(j)],
                    coeff=float(var_row[req[0]]),
                )
    print("Number of constraints =", solver.NumConstraints())

    # Objective function, minimize the difficulty
    objective = solver.Objective()
    for i, row in variables_df.iterrows():
        objective.SetCoefficient(
            var=variables[variables_df.index.get_loc(i)],
            coeff=float(row["Playability"]),
        )
    objective.SetMinimization()

    # Solve the system.
    status = solver.Solve()
    # Check that the problem has an optimal solution.
    print("[Solutions]")
    if status != solver.OPTIMAL:
        print("The problem does not have an optimal solution!")
        if status == solver.FEASIBLE:
            print("A potentially suboptimal solution was found.")
        else:
            print("The solver could not solve the problem.")
            return False

    # Display the amounts of matches at certain difficulty levels
    print("Total matches:")
    total_sum = 0

    row = {}
    nr_of_mats = 0
    for i, var in enumerate(variables):
        if var.solution_value() > 0.0:
            print(
                f"    {variables_df.index[i]}: {var.solution_value():.2f} matches at {variables_df.iloc[i]['Playability'] * var.solution_value():.2f} playability"
            )
            total_sum += variables_df.iloc[i]["Playability"] * var.solution_value()
            row.update({f"{variables_df.index[i]}": var.solution_value()})
            nr_of_mats += 1

    print("Total nr of matches {:.2f}".format(total_sum))
    row.update({"Nr of matches": nr_of_mats, "Total_diff": total_sum})

    print("[Advanced usage]")
    print(f"Problem solved in {solver.wall_time():d} milliseconds")
    print(f"Problem solved in {solver.iterations():d} iterations")
    print("\n")
    return row

best_solution = linear_solver(edited_df, required_tokens)
st.table(pd.DataFrame([best_solution]))

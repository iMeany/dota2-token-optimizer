import streamlit as st
import pandas as pd
from ortools.linear_solver import pywraplp

st.set_page_config(
    page_title="Dota2 Crownfall Token optimization",
    layout="wide",
    initial_sidebar_state="expanded",
)

# * Sidebar description
st.sidebar.write("# Dota2 Crownfall Token optimization")
st.sidebar.write("Optimal hero selection for min/max-ing when gathering tokens.")
st.sidebar.write("""## Heroes and tokens
This table shows the heroes and tokens you get for winning a match.  
* Normal/Ranked games give +3 tokens for a win, +1 token for a loss.  
* Turbo gives +2 out of 3 random tokens on a win, 0 on a loss.  
* The `Playability` column is the individual difficulty of the hero. The algorithm uses this as a *cost* and tries to minimize it.
* **You can edit the `Playability` and **increase** the number if you want the hero to be less likely to be chosen.**  
""")
st.sidebar.write("""## Required Token selection
This allows you to select the tokens you want to collect. Useful if trying to minimize the number of games played when farming Divine Developer offering tokens.
""")
st.sidebar.write("""## Optimal hero selection
This table shows the optimal hero selection based on the tokens you want to collect.
""")
st.sidebar.caption("""[dota2-token-optimizer](https://github.com/iMeany/dota2-token-optimizer) | 2024 MRU""")


# * Editable Hero token table
st.write("## Heroes and tokens")
st.write(
    "You can edit the `Playability` and **increase** the number if you want the hero to be less likely to be chosen."
)


@st.cache_resource
def load_hero_token_data():
    return pd.read_csv("data/heroes.csv", index_col=0)


df = load_hero_token_data().iloc[:, :-1]

edited_df = st.data_editor(df, disabled=df.columns[1:].tolist(), use_container_width=True)

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
                    step=1
                )
            ]

required_tokens = [[token, value] for token, value in zip(unique_token_list, token_input)]

# * Optimal hero selection
@st.cache_data
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
    result_df = pd.DataFrame()
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

best_solution = integer_linear_solver(edited_df, required_tokens, "Playability", "SAT")

if best_solution.empty:
    st.write("No solution found. Try to relax the constraints.")
    st.stop()
else:
    st.write("## Optimal hero selection")
    # adding totals row
    best_solution.loc["Total"] = best_solution.sum(numeric_only=True, axis=0)
    # drop cols where total is zero
    best_solution = best_solution.loc[:, (best_solution != 0).any(axis=0)]
    st.dataframe(best_solution.round(0).astype(int), use_container_width=True)
    st.caption("Remember you can increase the `Playability` value for the heroes you don't want to play.")

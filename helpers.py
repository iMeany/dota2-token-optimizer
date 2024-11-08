
import pandas as pd
import streamlit as st
from ortools.linear_solver import pywraplp
from PIL import Image
import numpy as np

@st.cache_data
def load_hero_token_data():
    df = pd.read_csv("data/heroes.csv", index_col=0)
    act_names = ['Act I: The Markets of Midgate', 'Act II: The Deserts of Druud', 'Act III: The Frosts of Icewrack', 'Act IV: The Spires of Skywrath']
    token_order = [["Walking","Running","Flying","Floating","Slithering","Mounted","Crawling","Jumping","Teleporting","Melee","Ranged","Disabler","Escape","Durable","Initiator","Nuker","Pusher","Healer"],
                   ["Strength","Agility","Intelligence","Universal","Demon","Undead","Spirit","Beast","Monster","God","Elemental","Unarmed","Blade","Polearm","Club","Wand","Ammunition"],
                   ["Flame","Frost","Storm","Tide","Nature","Void","Blood","Mystic","Armor","Helmet","Shield","Robe","Cape","Mask","Fur","Scale","Minion","Illusion","Ward","Partner"],
                   ["Pride","Gluttony","Sloth","Greed","Envy","Wrath","Lust","Discipline","Love","Mischief","Mountain","City","Plains","Desert","Tundra","Cave","Sky","Sea","Forest","Cosmos"],
                   ]
    return df, act_names, token_order

@st.cache_data
def load_all_images(token_order):
    images = {}
    for act_tokens in token_order:
        for token in act_tokens:
            images[token] = _alpha_to_gray(Image.open(f"assets/img/{token.lower()}_png.png"))
    return images

def _alpha_to_gray(img):
    """ Fixes the given image by setting the alpha channel to 255 for non-zero values, 
    and setting the RGB channels to constant gray (for both light and dark themes)."""
    img_array = np.array(img)
    alpha_channel = img_array[:, :, 3]
    alpha_channel[alpha_channel > 0] = 255
    img_array[:, :, :3] = (156, 156, 156)
    return Image.fromarray(img_array)

# @st.cache_data
# def load_act_images(token_order):
#     act_token_images = []
#     for idx, act_tokens in enumerate(token_order):
#         token_images = _load_token_images(act_tokens=act_tokens, act_nr=idx+1)
#         act_token_images.append(token_images)
#     return act_token_images

# @st.cache_data
# def _load_token_images(act_tokens, act_nr=1):
#     img = Image.open(f"assets/tokens{act_nr}.png")
#     token_dims = [(106, 90), (101, 91)]
#     sprite_h = token_dims[act_nr-1][0]
#     sprite_w = token_dims[act_nr-1][1]
#     token_images = []
#     for i in range(0, img.height, sprite_h):
#         for j in range(0, img.width, sprite_w):
#             if len(token_images) >= 18:
#                 break
#             token_images.append(img.crop((j, i, j+sprite_w, i+sprite_h)))
#     return dict(zip(act_tokens, token_images))

def get_col_grid(img_per_col=9):
    columns = st.columns(spec=img_per_col)
    columns = columns + st.columns(img_per_col)
    return columns

# @st.cache_data # if we dont cache we get different results on recalculation
def integer_linear_solver(val_df, requirements, cost_col, optimization_problem_type="SAT"):
    """Solves the integer linear problem with the given requirements and cost column."""
    # shuffling the rows so that it gives different solutions on recalculation, equivalent results are based on order of rows
    val_df = val_df.sample(frac=1)
    solver = pywraplp.Solver.CreateSolver(optimization_problem_type)
    if not solver:
        return
    print("Solving with " + optimization_problem_type)

    infinity = solver.infinity()

    # Variables and constraints
    variables = []
    for idx, row in val_df.iterrows():
        variables.append(solver.IntVar(0, infinity, str(idx)))
    constraints = []
    # only keep requirements > 0
    requirements = [(token, required) for token, required in requirements if required > 0 and token in val_df.columns]
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
    print(f"Number of variables = {solver.NumVariables()}, Number of constraints = {solver.NumConstraints()}")

    result_status = solver.Solve()

    # The problem has an optimal solution.
    if result_status != pywraplp.Solver.OPTIMAL:
        print("The problem does not have an optimal solution!")
        if result_status == pywraplp.Solver.FEASIBLE:
            print("A potentially suboptimal solution was found.")
        else:
            print(result_status)
            return pd.DataFrame()

    print(f"Problem solved in {solver.wall_time()} ms")

    # The objective value of the solution.
    print(f"Optimal objective value = {objective.Value()}:")

    # The value of each variable in the solution.
    result_df = pd.DataFrame(columns=["Matches"], dtype=int)
    for variable in variables:
        if variable.solution_value() > 0:
            print(f"  {variable.name()} = {variable.solution_value()}")
            # all the tokens from original dataframe + matches number from solution_value
            row = val_df.loc[variable.name()].copy()
            row["Matches"] = variable.solution_value()
            result_df = pd.concat([result_df, row.to_frame().T])
    print()
    return result_df


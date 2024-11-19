import streamlit as st
import numpy as np
from helpers import integer_linear_solver, load_hero_token_data, load_all_images

st.set_page_config(
    page_title="Dota2 Crownfall Token optimization",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon=":m:"
)

# * Sidebar description
st.sidebar.write("# Dota2 Crownfall Token optimization")
st.sidebar.write("Optimal hero selection for min/max-ing when gathering tokens.")
st.sidebar.write("""## Required Token selection
This allows you to select the tokens you want to collect. Useful if trying to minimize the number of games played when farming Divine Developer offering tokens.
""")
st.sidebar.write("""## Heroes and tokens
This (by default collapsed) table shows the heroes and tokens you get for winning a match.  
* Normal/Ranked games give +3 tokens for a win, +1 token for a loss.  
* Turbo gives +2 out of 3 random tokens on a win, 0 on a loss.  
* The `DifficultyScore` column is the individual difficulty of the hero. The algorithm uses this as a *cost* and tries to minimize it.
* You can edit the `DifficultyScore` and **increase** the number if you want the hero to be less likely to be chosen. 
  * Setting the value to `200` would mean that you would play 2 games with another hero or 1 game with this hero.
  * Setting the value to `101` would only mean that algorithm would choose the alternative option if available.  
* Clicking `Recalculate solutions` may give a different result if there are several equally optimal solutions.
""")
st.sidebar.write("""## Optimal hero selection
This table shows the optimal hero selection based on the tokens you want to collect.
""")
st.sidebar.caption("""[dota2-token-optimizer](https://github.com/iMeany/dota2-token-optimizer) | 2024 MRU""")

# * Setup data
df, act_names, token_order = load_hero_token_data()

# * Act and Token selection
token_col, table_col = st.columns([3, 7])
with table_col:
    act_index = int(st.query_params["act"][0]) if "act" in st.query_params else len(act_names)-1
    radio_select = st.radio("Select act", index=act_index, options=act_names, horizontal=True)
    act_idx = act_names.index(radio_select)
token_images = load_all_images(token_order)
required_tokens = {}
with token_col:
    st.write("#### Required tokens selection")
    for key in token_order[act_idx]:
        with token_col.container():
            icon_col, text_col, input_col = st.columns([2, 6, 7], vertical_alignment="center")
            icon_col.image(token_images[key], width=36)
            text_col.text(str(key))
            # read from query params
            required_tokens[key] = input_col.number_input("Amount", min_value=0,
                                                          key=f"token_{key}_input", label_visibility="collapsed")

# set query params so browser saves the state
# st.query_params.from_dict((key, value) for key, value in required_tokens.items() if value > 0)

# * Editable Hero token table
with table_col:
    token_mapping_on = st.toggle("Show Hero & Token table", value=False)
    # solution_tab, mapping_tab, heroes_pick_tab = st.tabs(["Solution", "Solution + Hero tokens & difficulty", "Heroes to pick"])
    if token_mapping_on:
        st.write("#### Hero token table")
        st.caption("You can edit the `DifficultyScore` column and **increase** the number if you want the hero to be less likely to be chosen.")
        df = st.data_editor(data=df, disabled=df.columns[1:].tolist(), use_container_width=True)

    heroes_to_pick_on = st.toggle("Show best heroes for a single game", value=True)
    if heroes_to_pick_on:
        st.write("#### Heroes to pick")
        st.caption("This shows the heroes that give the most tokens in a single game.")
        token_types_required = [key for key, value in required_tokens.items() if value > 0]
        heroes_to_pick = df[df[token_types_required].any(axis=1)]
        heroes_to_pick["Total"] = 0
        for col in token_types_required:
            heroes_to_pick["Total"] = heroes_to_pick["Total"] + np.minimum(heroes_to_pick[col], required_tokens[col])
        heroes_to_pick = heroes_to_pick.sort_values("Total", ascending=False)
        st.dataframe(heroes_to_pick[["Total"] + token_types_required], use_container_width=True)

    st.write("#### Optimal hero selection")
    st.caption("This table shows the optimal Hero selection and the number of games needed to get all the tokens you selected.")
    st.button("Recalculate solutions", type="secondary")
    # * Optimal hero selection
    try:
        best_solution = integer_linear_solver(df[['DifficultyScore'] + token_order[act_idx]], required_tokens.items(), "DifficultyScore")
    except Exception as e:
        st.write("Error occurred during optimization. Try again.")
        print(e)
        st.stop()
    if best_solution.empty:
        st.write("No solution found. Try to relax or add the constraints.")
        st.stop()
    else:
        # order by hero name
        best_solution = best_solution.sort_index()
        # adding totals row
        best_solution.loc["Total"] = best_solution.sum(numeric_only=True, axis=0)
        # drop cols where total is zero
        best_solution = best_solution.loc[:, (best_solution != 0).any(axis=0)]
        st.dataframe(best_solution.round(0).astype(int), use_container_width=True)
        st.caption("Remember that you can increase the `DifficultyScore`  value in the `Hero & Token` table for the heroes you don't want to play.")

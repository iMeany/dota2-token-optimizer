import streamlit as st

from helpers import integer_linear_solver, load_hero_token_data, load_act_images

st.set_page_config(
    page_title="Dota2 Crownfall Token optimization",
    layout="wide",
    initial_sidebar_state="expanded",
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
# shuffling the rows so that it gives different solutions on recalculation, equivalent results are based on order of rows
df = df.sample(frac=1)

# * Act and Token selection
radio_select = st.radio("Select act", index=len(act_names)-1, options=act_names, horizontal=True)
act_idx = act_names.index(radio_select)
token_images = load_act_images(token_order)
required_tokens = {}
token_col, table_col = st.columns([3, 7])
with token_col:
    st.write("#### Required tokens selection")
    for key in token_images[act_idx]:
        with token_col.container():
            icon_col, text_col, input_col = st.columns([2, 6, 7])
            icon_col.image(token_images[act_idx][key], width=34)
            text_col.text(f"{key}")
            # read from query params
            required_tokens[key] = input_col.number_input("Amount", min_value=0,
                                                          key=f"token_{key}_input", label_visibility="collapsed")

# set query params so browser saves the state
# st.query_params.from_dict((key, value) for key, value in required_tokens.items() if value > 0)

# * Editable Hero token table
with table_col:
    solution_tab, mapping_tab = st.tabs(["Solution", "Heroes and Tokens"])
    with mapping_tab:
        st.write("You can edit the `DifficultyScore` column and **increase** the number if you want the hero to be less likely to be chosen.")
        edited_df = st.data_editor(df, disabled=df.columns[1:].tolist(), use_container_width=True)

    st.button("Recalculate solutions", type="secondary")
    # * Optimal hero selection
    try:
        best_solution = integer_linear_solver(edited_df[['DifficultyScore'] + token_order[act_idx]], required_tokens.items(), "DifficultyScore")
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
        st.caption("Remember that you can increase the `DifficultyScore`  value in the `Heroes and Tokens` tab for the heroes you don't want to play.")

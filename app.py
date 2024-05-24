import streamlit as st

from helpers import integer_linear_solver, load_hero_token_data, load_act_images, get_col_grid

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
""")
st.sidebar.write("""## Optimal hero selection
This table shows the optimal hero selection based on the tokens you want to collect.
""")
st.sidebar.caption("""[dota2-token-optimizer](https://github.com/iMeany/dota2-token-optimizer) | 2024 MRU""")

# * Required token selection
st.write("## Required tokens selection")
df = load_hero_token_data().iloc[:, :]
# shuffling the rows so that it gives different solutions on recalculation, equivalent results are based on order of rows
df = df.sample(frac=1)
unique_token_list = df.columns[1:].values.tolist()
act_names = ['Act 1: The Markets of Midgate', 'Act 2: The Deserts of Druud']
# tokens in order for each act 
token_order = [["Walking","Running","Flying","Floating","Slithering","Mounted","Crawling","Jumping","Teleporting","Melee","Ranged","Disabler","Escape","Durable","Initiator","Nuker","Pusher","Healer"],
               ["Strength","Agility","Intelligence","Universal","Demon","Undead","Spirit","Beast","Monster","God","Elemental","Unarmed","Blade","Polearm","Club","Wand","Ammunition"]]

# * Token selection
radio_select = st.radio("Select act", act_names, index=1, horizontal=True)
act_idx = act_names.index(radio_select)
st.write(f"### {radio_select}")
token_images = load_act_images(token_order)
required_tokens = {}
columns = get_col_grid()
col_idx = 0
st.query_params.clear()
for key in token_images[act_idx]:
    with columns[col_idx]:
        st.text(f"{key}")
        st.image(token_images[act_idx][key], use_column_width=True)
        # read from query params
        val = int(st.query_params.get(key, "0"))
        required_tokens[key] = st.number_input("Amount", value=val, key=f"token_{key}_input", label_visibility="collapsed")
    col_idx+=1
# set query params so browser saves the state
st.query_params.update(required_tokens)

# * Editable Hero token table
with st.expander("Show hero/token table"):
    st.write("### Heroes and tokens")
    st.write("You can edit the `DifficultyScore` and **increase** the number if you want the hero to be less likely to be chosen.")
    edited_df = st.data_editor(df, disabled=df.columns[1:].tolist(), use_container_width=True)

# * Optimal hero selection
try:
    best_solution = integer_linear_solver(edited_df[['DifficultyScore'] + token_order[act_idx]], required_tokens.items(), "DifficultyScore")
except:
    st.write("Error occured during optimization. Try again.")
    st.stop()

if best_solution.empty:
    st.write("No solution found. Try to relax the constraints.")
    st.stop()
else:
    st.write("## Optimal hero selection")
    st.button("Recalculate solutions", type="secondary")
    # adding totals row
    best_solution.loc["Total"] = best_solution.sum(numeric_only=True, axis=0)
    # drop cols where total is zero
    best_solution = best_solution.loc[:, (best_solution != 0).any(axis=0)]
    st.dataframe(best_solution.round(0).astype(int), use_container_width=True)
    st.caption("Remember that you can increase the `DifficultyScore` value for the heroes you don't want to play.")
    st.caption("Clicking 'Recalculate solutions' may give a different result if there are several equally optimal solutions.")

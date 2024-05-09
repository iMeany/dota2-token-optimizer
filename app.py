import streamlit as st

from helpers import integer_linear_solver, load_hero_token_data, load_token_images

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
This table shows the heroes and tokens you get for winning a match.  
* Normal/Ranked games give +3 tokens for a win, +1 token for a loss.  
* Turbo gives +2 out of 3 random tokens on a win, 0 on a loss.  
* The `Playability` column is the individual difficulty of the hero. The algorithm uses this as a *cost* and tries to minimize it.
* **You can edit the `Playability` and **increase** the number if you want the hero to be less likely to be chosen.**  
""")
st.sidebar.write("""## Optimal hero selection
This table shows the optimal hero selection based on the tokens you want to collect.
""")
st.sidebar.caption("""[dota2-token-optimizer](https://github.com/iMeany/dota2-token-optimizer) | 2024 MRU""")

# * Required token selection
st.write("## Required tokens selection")
df = load_hero_token_data().iloc[:, :-1]
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

# * Token selection

token_images = load_token_images()
columns = st.columns(len(token_images))
for idx, img in enumerate(token_images):
    with columns[idx]:
        with st.container(border=True):
            st.image(img, caption=f"{unique_token_list[idx]}") 
            st.button("➕", key=f"token_{idx}")
            st.button("➖", key=f"tokenr_{idx}")
    # st.image(token_images[idx], caption=f"Token {idx}", width=100)


required_tokens = [[token, value] for token, value in zip(unique_token_list, token_input)]

# * Editable Hero token table
with st.expander("Show hero/token table"):
    st.write("### Heroes and tokens")
    st.write("You can edit the `Playability` and **increase** the number if you want the hero to be less likely to be chosen.")
    edited_df = st.data_editor(df, disabled=df.columns[1:].tolist(), use_container_width=True)

# * Optimal hero selection
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
    st.button("Recalculate", type="secondary")
import streamlit as st
import pandas as pd

@st.cache_data
def load_hero_token_data():
    return pd.read_csv("data/heroes.csv")

df = load_hero_token_data()

st.write("# Dota2 Crownfall Token optimization")
st.write("Optimal hero selection for tokens.")
st.dataframe(df)
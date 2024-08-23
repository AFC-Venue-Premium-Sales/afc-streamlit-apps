import streamlit as st
import pandas as pd

st.title('My Streamlit App')
st.write('Hello, world!')

data = {
    'Column 1': [1, 2, 3],
    'Column 2': [4, 5, 6]
}

df = pd.DataFrame(data)
st.write(df)

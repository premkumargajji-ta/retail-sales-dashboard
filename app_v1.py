import streamlit as st

st.title("Upload Test")

uploaded_file = st.file_uploader(
    "Upload Excel",
    type=["xlsx", "xls"]
)

if uploaded_file:
    st.success("Upload successful")
    st.write(uploaded_file.name)
    st.write(uploaded_file.size)

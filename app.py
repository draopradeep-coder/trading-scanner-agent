import streamlit as st

st.set_page_config(page_title="TraderPrp | Trading Scanner", page_icon="📈", layout="wide")

pages = {
    "Home": [st.Page("app.py", title="Home", icon="🏠", default=True)],
    "Stock Research": [
        st.Page("pages/1_Stock_Universe.py", title="Stock Universe", icon="📚"),
        st.Page("pages/2_Automatic_Scanner.py", title="Automatic Scanner", icon="🔎"),
    ],
    "Market Intelligence": [
        st.Page("pages/3_Market_Breadth.py", title="Market Breadth", icon="📊"),
        st.Page("pages/4_Sector_Rotation.py", title="Sector Rotation", icon="🏭"),
    ],
    "Tools": [st.Page("pages/5_Excel_Dashboard.py", title="Excel Dashboard", icon="📁")],
}
page = st.navigation(pages)
page.run()

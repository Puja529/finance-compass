import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
category = "categories.json"
# to activate venv :source venv/bin/activate
# import osstreamlit run app.pystreamlit run app.py
st.set_page_config(page_title="Finance Tracker",page_icon= "💰",layout="wide")
if "categories" not in st.session_state:
    st.session_state.categories = {
        "uncategorized": []
    }
if os.path.exists(category):
    with open(category, "r") as f:
        st.session_state.categories =json.load(f)

def save_categories():
    with open(category, "w") as f:
        json.dump(st.session_state.categories, f)

# if virtualfolder is not activated then type in source venv/bin/activate
# 
# Local URL: http://localhost:8501
#   Network URL: http://192.168.101.3:8501
# creating a function to load data from json file
def categorize_transcations(df):
    # loaded from load_transactions function
    df["category"]="uncategorized"
    for category,keywords in st.session_state.categories.items():
        if category == "uncategorized" or not keywords:
            continue
        lowered_keywords = [keyword.lower().strip() for keyword in keywords]
        for idx,row in df.iterrows():
            details = row["Details"].lower().strip()
            if details in lowered_keywords:
                df.at[idx,"category"]=category
    return df
            

def load_transactions(file):
     
    try:
        df=pd.read_csv(file)
        df.columns=[col.strip() for col in df.columns]
        # to standarize the amount
    
        df['Amount']=pd.to_numeric(df['Amount'].str.replace(',', '').astype(float))
        df['Date']=pd.to_datetime(df['Date'],format="%d %b %Y")
        # to handle different bank format realted to debit/credit
        if "Debit/Credit" in df.columns:
            pass
        elif "Withdraw" in df.columns and "Deposit" in df.columns:
            df["Debit/Credit"]=df.apply(lambda row: "Debit" if row["Withdraw"]>0  else "Credit", axis=1)
            df["Amount"]=df.apply(lambda row: row["Withdraw"] if row["Withdraw"]>0 else row["Deposit"], axis=1)
          
        # st.write(df)
        return categorize_transcations(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None
def add_keyword_to_category(category,keyword):
    keyword = keyword.lower().strip()
    # use .get to avoid KeyError if category doesn't exist
    if keyword and keyword not in st.session_state.categories.get(category, []):
        st.session_state.categories.setdefault(category, []).append(keyword)
        save_categories()
        return True
    return False

    

def main():
    st.title("Personal Finance Dashboard")
    st.sidebar.title("Finance Tracker")
    uploaded_file = st.sidebar.file_uploader("Upload your Finance Data", type=["csv"])
    if uploaded_file is not None:
        df=load_transactions(uploaded_file)
        if df is not None:
            debits_df = df[df["Debit/Credit"] == "Debit"].copy()
            credits_df = df[df["Debit/Credit"] == "Credit"].copy()
            col1,col2 = st.columns(2)
            with col1:
                st.metric("Total Expenses", f"NRS {debits_df['Amount'].sum():,.2f}")
            with col2:
                st.metric("Total Payments", f"NRS {credits_df['Amount'].sum():,.2f}")
            st.session_state.debits_df = debits_df.copy()
            tab1,tab2 = st.tabs(["Expenses(Debits)","Payments(Credits)"])
            with tab1:
                # managing categories
                st.subheader("Manage Categories")
                new_category = st.text_input("Add new category")
                add_button = st.button("Add Category")
                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.success(f"Added new category: {new_category}")
                        st.rerun()
                st.subheader("Your Expenses")
                # for expense table
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date","Details","Amount","category"]],
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f NRS"),
                        "category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )
                save_button = st.button("Apply Changes", type="primary")
                # to update the category in the main dataframe and also add the details as keyword to the category
                if save_button:
                    for idx, row in edited_df.iterrows():
                        if row["category"] == st.session_state.debits_df.at[idx,"category"]:
                            continue
                        details = row["Details"]
                        st.session_state.debits_df.at[idx,"category"] = row["category"]
                        add_keyword_to_category(row["category"], details)
                # category summary
                st.subheader("Category Spending")
                category_totals = (
                    st.session_state.debits_df
                    .groupby("category")["Amount"]
                    .sum()
                    .reset_index()
                    .sort_values(by="Amount", ascending=False)
                )
                st.dataframe(
                    category_totals,
                    column_config={
                        "Amount": st.column_config.NumberColumn("Amount", format="NRS %.2f")
                    },
                    hide_index=True,
                    use_container_width=True
                )
                # pie chart
                fig = px.pie(
                    category_totals,
                    values="Amount",
                    names="category",
                    title="Expense Distribution by Category"
                )
                st.plotly_chart(fig, use_container_width=True)
                # monthly trend
                st.subheader("Monthly Expense Trend")   
                monthly_df = st.session_state.debits_df.copy()
                monthly_df["Month"] = monthly_df["Date"].dt.to_period("M").astype(str)
                monthly_totals = (
                    monthly_df.groupby("Month")["Amount"]
                    .sum()
                    .reset_index()
                )
                fig_trend = px.line(
                    monthly_totals,
                    x="Month",
                    y="Amount",
                    markers=True,
                    title="Monthly Spending Trend"
                )
                st.plotly_chart(fig_trend, use_container_width=True)
                # budget monitor
                st.subheader("Budget Monitor")

                budget = st.number_input(
                    "Set your monthly budget (NRS)",
                    min_value=0.0,
                    step=500.0
                )
                current_spending = st.session_state.debits_df["Amount"].sum()
                if budget > 0:
                    if current_spending > budget:
                        st.error(f"⚠️ Budget exceeded! You spent NRS {current_spending:,.2f}")
                    elif current_spending > budget * 0.8:
                        st.warning(f"⚠️ You used {current_spending/budget:.0%} of your budget")
                    else:
                        st.success("✅ Spending is within budget")

             
            with tab2:
                st.subheader("Payment Summary")
                total_payments = credits_df["Amount"].sum()
                st.metric("Total payments", f"NRS {total_payments:,.2f}")


    


main()
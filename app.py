import streamlit as st
import pandas as pd
import plotly.express as px

# Set page configuration
st.set_page_config(page_title="Retail Sales Intelligence", layout="wide")
st.title("📊 Retail Sales Intelligence Dashboard")

# --- STEP 1: DATA INTEGRATION & CLEANING ---
st.sidebar.header("1. Upload Data")
sales_file = st.sidebar.file_uploader("Upload retail_weekly_sales.xlsx", type=['xlsx'])
stores_file = st.sidebar.file_uploader("Upload store_master.xlsx", type=['xlsx'])

if sales_file and stores_file:
    try:
        # Load datasets
        df_sales = pd.read_excel(sales_file)
        df_stores = pd.read_excel(stores_file)
        
        # Merge datasets on lowercase 'store_id'
        df = pd.merge(df_sales, df_stores, on="store_id", how="left")
        
        # --- DATA CLEANING FIX ---
        # Ensure KPI columns are purely numeric (removes $, commas, and handles text errors)
        numeric_cols = ["net_sales", "sales_target", "transactions", "returns_amount", 
                        "discount_amount", "gross_sales", "units_sold", "inventory_on_hand"]
        
        for col in numeric_cols:
            if col in df.columns:
                # If the column is read as an object (string), clean it first
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
                # Force to numeric, turn errors into NaN, then fill NaN with 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)


        # --- STEP 2: SIDEBAR FILTERS ---
        st.sidebar.header("2. Filters")
        
        def multiselect_filter(col_name, label):
            options = df[col_name].dropna().unique().tolist()
            selected = st.sidebar.multiselect(label, options, default=options)
            return selected

        # Generate Filters
        weeks = multiselect_filter("week_start_date", "Select Week(s)")
        regions = multiselect_filter("region_x", "Select Region(s)") 
        stores = multiselect_filter("store_name_x", "Select Store(s)") 
        cities = multiselect_filter("city_x", "Select City/Cities")
        formats = multiselect_filter("store_format_x", "Select Store Format(s)")
        categories = multiselect_filter("product_category", "Select Category")

        # Apply Filters
        filtered_df = df[
            (df["week_start_date"].isin(weeks)) &
            (df["region_x"].isin(regions)) &
            (df["store_name_x"].isin(stores)) &
            (df["city_x"].isin(cities)) &
            (df["store_format_x"].isin(formats)) &
            (df["product_category"].isin(categories))
        ]

        # --- STEP 3: KPI CALCULATIONS ---
        total_net_sales = filtered_df["net_sales"].sum()
        total_target = filtered_df["sales_target"].sum()
        target_achieved = (total_net_sales / total_target * 100) if total_target > 0 else 0
        
        total_transactions = filtered_df["transactions"].sum()
        atv = (total_net_sales / total_transactions) if total_transactions > 0 else 0
        
        total_return_amount = filtered_df["returns_amount"].sum()
        return_rate = (total_return_amount / total_net_sales * 100) if total_net_sales > 0 else 0
        
        total_discount = filtered_df["discount_amount"].sum()
        total_gross_sales = filtered_df["gross_sales"].sum()
        discount_rate = (total_discount / total_gross_sales * 100) if total_gross_sales > 0 else 0

        # Render KPI Cards
        st.markdown("### Key Performance Indicators")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Net Sales", f"${total_net_sales:,.2f}")
        col2.metric("Target Achievement", f"{target_achieved:.1f}%")
        col3.metric("Avg Transaction Value (ATV)", f"${atv:.2f}")
        col4.metric("Return Rate", f"{return_rate:.1f}%")
        col5.metric("Discount Rate", f"{discount_rate:.1f}%")
        st.markdown("---")

        # --- STEP 4: VISUAL ANALYTICS ---
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("**Weekly Sales Trend**")
            trend_data = filtered_df.groupby("week_start_date")["net_sales"].sum().reset_index()
            fig_trend = px.line(trend_data, x="week_start_date", y="net_sales", markers=True)
            st.plotly_chart(fig_trend, use_container_width=True)

            st.markdown("**Category Performance**")
            cat_data = filtered_df.groupby("product_category")["net_sales"].sum().reset_index()
            fig_cat = px.pie(cat_data, values="net_sales", names="product_category", hole=0.4)
            st.plotly_chart(fig_cat, use_container_width=True)

        with col_chart2:
            st.markdown("**Sales by Region**")
            region_data = filtered_df.groupby("region_x")["net_sales"].sum().reset_index()
            fig_region = px.bar(region_data, x="region_x", y="net_sales", color="region_x")
            st.plotly_chart(fig_region, use_container_width=True)

            st.markdown("**Stockout Risk (Low Inventory vs High Sales)**")
            fig_stock = px.scatter(filtered_df, x="units_sold", y="inventory_on_hand", 
                                   color="product_category", hover_data=["store_name_x"])
            st.plotly_chart(fig_stock, use_container_width=True)

        st.markdown("**Top 10 Stores Leaderboard**")
        store_leaders = filtered_df.groupby("store_name_x")["net_sales"].sum().reset_index()
        store_leaders = store_leaders.sort_values(by="net_sales", ascending=False).head(10)
        store_leaders.rename(columns={"store_name_x": "Store Name", "net_sales": "Net Sales"}, inplace=True)
        st.dataframe(store_leaders, use_container_width=True)
        st.markdown("---")

        # --- STEP 5: BUSINESS INSIGHT SUMMARY ---
        st.markdown("### Business Insights Summary")
        
        if not region_data.empty:
            best_region = region_data.loc[region_data['net_sales'].idxmax()]['region_x']
            worst_region = region_data.loc[region_data['net_sales'].idxmin()]['region_x']
            st.info(f"**Top Performing Region:** {best_region} | **Lowest Performing Region:** {worst_region}")
        
        # Stores Missing Target
        store_targets = filtered_df.groupby("store_name_x")[["net_sales", "sales_target"]].sum()
        # Avoid division by zero warnings
        store_targets["Achievement"] = store_targets.apply(
            lambda row: row["net_sales"] / row["sales_target"] if row["sales_target"] > 0 else 0, axis=1
        )
        missing_targets = store_targets[store_targets["Achievement"] < 1.0].index.tolist()
        st.warning(f"**Stores Missing Target:** {', '.join(missing_targets) if missing_targets else 'None'}")
        
        # High Return Categories
        cat_returns = filtered_df.groupby("product_category")[["returns_amount", "net_sales"]].sum()
        cat_returns["Return_Rate"] = cat_returns.apply(
            lambda row: row["returns_amount"] / row["net_sales"] if row["net_sales"] > 0 else 0, axis=1
        )
        high_return_cats = cat_returns.sort_values(by="Return_Rate", ascending=False).head(3).index.tolist()
        st.error(f"**Categories with Highest Return Rates:** {', '.join(high_return_cats) if high_return_cats else 'None'}")

        # --- STEP 6: EXPORT FUNCTIONALITY ---
        st.markdown("### Export Data")
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv,
            file_name='filtered_retail_sales.csv',
            mime='text/csv',
        )

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("Please upload both 'retail_weekly_sales.xlsx' and 'store_master.xlsx' in the sidebar to view the dashboard.")
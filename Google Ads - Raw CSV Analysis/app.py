import streamlit as st
import pandas as pd
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import gspread
from datetime import datetime
import plotly.express as px
import numpy as np

# Set page configuration
st.set_page_config(
    page_title="Google Ads Campaign Analyzer",
    page_icon="📊",
    layout="wide"
)

def load_google_sheet(sheet_url):
    try:
        # Use service account credentials
        credentials = service_account.Credentials.from_service_account_file(
            'perfect-impulse-447907-s9-e1c34e3f9ffc.json',  # You'll need to replace this with your credentials file
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
        )
        
        client = gspread.authorize(credentials)
        
        # Extract sheet ID from URL
        sheet_id = sheet_url.split('/')[5]
        sheet = client.open_by_key(sheet_id).sheet1
        
        # Get all values and convert to DataFrame
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Error loading sheet: {str(e)}")
        return None

def analyze_campaign(df):
    try:
        # Initialize all variables at the start
        summary = ""
        recommendations = []
        monthly_performance = None
        best_month = None
        worst_month = None
        campaign_performance = None
        
        # Get currency at the beginning
        currency = df['Currency code'].iloc[0] if 'Currency code' in df.columns else 'CHF'
        
        # Initialize session state for selections if they don't exist
        if 'selections_made' not in st.session_state:
            st.session_state.selections_made = False
            
        if 'cost_col' not in st.session_state:
            st.session_state.cost_col = 'Cost' if 'Cost' in df.columns else df.columns[0]
        if 'conv_col' not in st.session_state:
            st.session_state.conv_col = 'All conv.' if 'All conv.' in df.columns else 'Conversions' if 'Conversions' in df.columns else df.columns[0]
        if 'clicks_col' not in st.session_state:
            st.session_state.clicks_col = 'Clicks' if 'Clicks' in df.columns else df.columns[0]
        if 'imp_col' not in st.session_state:
            st.session_state.imp_col = 'Impressions' if 'Impressions' in df.columns else df.columns[0]
            
        # Column selection section
        st.subheader("1. Map Your Data Columns")
        col1, col2 = st.columns(2)
        
        with col1:
            cost_col = st.selectbox(
                "Column for Cost:",
                df.columns,
                index=df.columns.get_loc(st.session_state.cost_col)
            )
            conversions_col = st.selectbox(
                "Column for Conversions:",
                df.columns,
                index=df.columns.get_loc(st.session_state.conv_col)
            )
        
        with col2:
            clicks_col = st.selectbox(
                "Column for Clicks:",
                df.columns,
                index=df.columns.get_loc(st.session_state.clicks_col)
            )
            impressions_col = st.selectbox(
                "Column for Impressions:",
                df.columns,
                index=df.columns.get_loc(st.session_state.imp_col)
            )

        # Update session state with selected values
        st.session_state.cost_col = cost_col
        st.session_state.conv_col = conversions_col
        st.session_state.clicks_col = clicks_col
        st.session_state.imp_col = impressions_col

        # Add a button to confirm selections
        if st.button("Confirm Selections and Analyze"):
            st.session_state.selections_made = True

        # Only proceed with analysis if selections are confirmed
        if st.session_state.selections_made:
            try:
                # Data preprocessing
                df[cost_col] = pd.to_numeric(df[cost_col], errors='coerce').fillna(0)
                df[conversions_col] = pd.to_numeric(df[conversions_col], errors='coerce').fillna(0)
                df[clicks_col] = pd.to_numeric(df[clicks_col], errors='coerce').fillna(0)
                df[impressions_col] = pd.to_numeric(df[impressions_col], errors='coerce').fillna(0)
                
                # Campaign level analysis first (required for summary)
                campaign_performance = df.groupby('Campaign').agg({
                    cost_col: 'sum',
                    conversions_col: 'sum',
                    clicks_col: 'sum',
                    impressions_col: 'sum'
                }).reset_index()
                
                campaign_performance['CTR'] = (campaign_performance[clicks_col] / campaign_performance[impressions_col] * 100)
                campaign_performance['CPA'] = campaign_performance[cost_col] / campaign_performance[conversions_col].replace(0, np.inf)
                campaign_performance['Conv_Rate'] = (campaign_performance[conversions_col] / campaign_performance[clicks_col] * 100)
                
                # Time-based analysis
                if 'Month' in df.columns:
                    monthly_performance = df.groupby('Month').agg({
                        cost_col: 'sum',
                        conversions_col: 'sum',
                        clicks_col: 'sum',
                        impressions_col: 'sum'
                    }).reset_index()
                    
                    monthly_performance['CTR'] = (monthly_performance[clicks_col] / monthly_performance[impressions_col] * 100)
                    monthly_performance['CPA'] = monthly_performance[cost_col] / monthly_performance[conversions_col].replace(0, np.inf)
                    monthly_performance['Conv_Rate'] = (monthly_performance[conversions_col] / monthly_performance[clicks_col] * 100)
                    
                    best_month = monthly_performance.loc[monthly_performance['Conv_Rate'].idxmax()]
                    worst_month = monthly_performance.loc[monthly_performance['Conv_Rate'].idxmin()]

                    # Visualization section
                    st.subheader("4. Performance Trends Visualization")
                    
                    # Create trend chart for Clicks and Cost
                    fig1 = px.line(monthly_performance, x='Month', y=[clicks_col, cost_col],
                                 title='Clicks and Cost Trends Over Time',
                                 labels={
                                     'Month': 'Time Period',
                                     'value': 'Count/Cost',
                                     'variable': 'Metric'
                                 })
                    
                    # Update legend labels
                    fig1.update_traces(name='Clicks', selector=dict(name=clicks_col))
                    fig1.update_traces(name='Cost', selector=dict(name=cost_col))
                    
                    # Add secondary y-axis for cost
                    fig1.update_layout(
                        yaxis2=dict(
                            title='Cost',
                            overlaying='y',
                            side='right'
                        ),
                        yaxis_title='Clicks',
                        legend_title='Metrics',
                        height=500
                    )
                    
                    # Show the plot
                    st.plotly_chart(fig1, use_container_width=True)
                    
                    # Create trend chart for CTR and Conversion Rate
                    fig2 = px.line(monthly_performance, x='Month', 
                                 y=['CTR', 'Conv_Rate'],
                                 title='CTR and Conversion Rate Trends',
                                 labels={
                                     'Month': 'Time Period',
                                     'value': 'Rate (%)',
                                     'variable': 'Metric'
                                 })
                    
                    fig2.update_layout(
                        yaxis_title='Rate (%)',
                        legend_title='Metrics',
                        height=500
                    )
                    
                    # Show the plot
                    st.plotly_chart(fig2, use_container_width=True)
                    
                    # Add insights about trends
                    st.subheader("Trend Insights")
                    
                    # Calculate month-over-month changes
                    monthly_performance['Clicks_Change'] = monthly_performance[clicks_col].pct_change() * 100
                    monthly_performance['Cost_Change'] = monthly_performance[cost_col].pct_change() * 100
                    
                    latest_month = monthly_performance.iloc[-1]
                    previous_month = monthly_performance.iloc[-2]
                    
                    st.write(f"""
                    📈 Latest Trends (comparing {latest_month['Month']} to previous month):
                    - Clicks: {latest_month[clicks_col]:.0f} ({latest_month['Clicks_Change']:+.1f}% change)
                    - Cost: {currency} {latest_month[cost_col]:.2f} ({latest_month['Cost_Change']:+.1f}% change)
                    - CTR: {latest_month['CTR']:.2f}%
                    - Conversion Rate: {latest_month['Conv_Rate']:.2f}%
                    """)
                
                # Generate comprehensive summary
                st.subheader("2. Campaign Performance Analysis")
                
                summary = f"""
                📊 Campaign Performance Deep Dive:

                💰 Overall Performance:
                - Total Spend: {currency} {df[cost_col].sum():,.2f}
                - Total Conversions: {int(df[conversions_col].sum())}
                - Overall CTR: {(df[clicks_col].sum() / df[impressions_col].sum() * 100):.2f}%
                - Average CPA: {currency} {(df[cost_col].sum() / df[conversions_col].sum()):.2f}
                
                🏆 Top Performing Campaign:
                - {campaign_performance.loc[campaign_performance['Conv_Rate'].idxmax()]['Campaign']}
                - Conversion Rate: {campaign_performance['Conv_Rate'].max():.2f}%
                """
                
                if 'Month' in df.columns and best_month is not None and worst_month is not None:
                    summary += f"""
                    📈 Monthly Trend:
                    - Best Month: {best_month['Month']} (Conv. Rate: {best_month['Conv_Rate']:.2f}%)
                    - Worst Month: {worst_month['Month']} (Conv. Rate: {worst_month['Conv_Rate']:.2f}%)
                    """
                
                st.write(summary)
                
                # Generate recommendations
                st.subheader("3. Recommendations")
                
                # Budget recommendations
                top_campaign = campaign_performance.loc[campaign_performance['Conv_Rate'].idxmax()]
                recommendations.append(f"💰 Budget Optimization: Increase budget allocation to '{top_campaign['Campaign']}' which shows the highest conversion rate of {top_campaign['Conv_Rate']:.2f}%")
                
                # Performance recommendations
                low_performing = campaign_performance[campaign_performance['CTR'] < 1]
                if not low_performing.empty:
                    recommendations.append(f"📉 Performance Alert: Campaigns {', '.join(low_performing['Campaign'].tolist())} have CTR below 1%. Review ad copy and targeting.")
                
                # Display recommendations
                for i, rec in enumerate(recommendations, 1):
                    st.write(f"{i}. {rec}")
                
                # Show detailed performance tables
                if st.checkbox("Show Detailed Performance Data"):
                    st.subheader("Campaign Performance Details")
                    st.dataframe(campaign_performance.sort_values('Conv_Rate', ascending=False))
                    
                    if monthly_performance is not None:
                        st.subheader("Monthly Performance Trends")
                        st.dataframe(monthly_performance.sort_values('Month'))
                        
            except Exception as e:
                st.error(f"Error in analysis calculations: {str(e)}")
                return "Error in calculations", ["An error occurred during analysis"]

        return summary, recommendations
            
    except Exception as e:
        st.error(f"Analysis error: {str(e)}")
        return "Error in analysis", ["An unexpected error occurred"]

def main():
    st.title("Google Ads Campaign Analyzer 📊")
    
    st.write("""
    ### Instructions
    1. Enter your Google Sheets URL containing the Google Ads data
    2. Map your columns to the required metrics
    3. The analysis will provide a campaign summary and optimization recommendations
    """)
    
    sheet_url = st.text_input("Enter Google Sheets URL:")
    
    if sheet_url:
        df = load_google_sheet(sheet_url)
        if df is not None:
            analyze_campaign(df)

if __name__ == "__main__":
    main() 
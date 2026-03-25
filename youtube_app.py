import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

def audience_simple(country):
    """Show top represented countries"""
    if country == 'US':
        return 'USA'
    elif country == 'IN':
        return 'India'
    else:
        return 'Other'

def style_negative(v, props=''):
    """ Style negative values in dataframe"""
    try:
        return props if v < 0 else None
    except:
        pass

def style_positive(v, props=''):
    """Style positive values in dataframe"""
    try:
        return props if v > 0 else None
    except:
        pass

    # load data
@st.cache_data
def load_data():
    df_agg = pd.read_csv("data/Aggregated_Metrics_By_Video.csv").iloc[1:,:] # skip first row
    df_agg_sub = pd.read_csv("data/Aggregated_Metrics_By_Country_And_Subscriber_Status.csv")
    df_comments = pd.read_csv("data/All_Comments_Final.csv")
    df_time = pd.read_csv("data/Video_Performance_Over_Time.csv")

    # data adjustments
    df_agg.columns = ['Video', 'Video title', 'Video publish time', 'Comments added', 'Shares', 'Dislikes', 'Likes',
                      'Subscribers lost', 'Subscribers gained', 'RPM(USD)','CPM(USD)',
                      'Average % viewed' ,'Average view duration',
                      'Views' ,'Watch time (hours)' ,'Subscribers',
                      'Your estimated revenue (USD)' ,'Impressions' ,'Impressions ctr(%)']
    df_agg['Video publish time'] = pd.to_datetime(df_agg['Video publish time'], format="%b %d, %Y")
    df_agg['Average view duration'] = df_agg['Average view duration'].apply(lambda x: datetime.strptime(x,'%H:%M:%S'))
    df_agg['Avg_duration_sec'] = df_agg['Average view duration'].apply(lambda x: x.second + x.minute*60 + x.hour*3600)
    df_agg['Engagement_ratio'] = (df_agg['Comments added'] + df_agg['Shares'] + df_agg['Dislikes'] + df_agg['Likes']) / df_agg.Views
    df_agg['Views / sub gained'] = df_agg['Views'] / df_agg['Subscribers gained']
    df_agg.sort_values('Video publish time', ascending=False, inplace=True)
    df_time['Date'] = df_time['Date'].apply(lambda x: x.replace("Sept", "Sep"))
    df_time['Date'] = pd.to_datetime(df_time['Date'], format="%d %b %Y")

    return df_agg, df_agg_sub, df_comments, df_time

# data
df_agg, df_agg_sub, df_comments, df_time = load_data()

# difference to median (last 12 months)
df_agg_diff = df_agg.copy()
metric_date_12months = df_agg_diff['Video publish time'].max() - pd.DateOffset(months=12)
median_agg = df_agg_diff[df_agg_diff['Video publish time'] >= metric_date_12months].select_dtypes(include='number').median()
numeric_cols = np.array((df_agg_diff.dtypes == 'float64') | (df_agg_diff.dtypes == 'int64'))
df_agg_diff.iloc[:,numeric_cols] = (df_agg_diff.iloc[:,numeric_cols] - median_agg).div(median_agg)

# daily views (first 30, median & percentiles (last 12 months))
df_time_diff = pd.merge(df_time, df_agg[['Video','Video publish time']], left_on ='External Video ID', right_on = 'Video')
df_time_diff['days_published'] = (df_time_diff['Date'] - df_time_diff['Video publish time']).dt.days
date_12months = df_agg['Video publish time'].max() - pd.DateOffset(months=12)
df_time_diff_yr = df_time_diff[df_time_diff['Video publish time'] >= date_12months]

views_days = pd.pivot_table(df_time_diff_yr, index='days_published', values='Views', aggfunc=[
    np.mean,
    np.median,
    lambda x: np.percentile(x, 80),
    lambda x: np.percentile(x, 20)
]).reset_index()
views_days.columns = ['days_published', 'mean_views', 'median_views', '80pct_views', '20pct_views']
views_days = views_days[views_days['days_published'].between(0, 30)]
views_cumulative = views_days.loc[:,['days_published','median_views','80pct_views','20pct_views']]
views_cumulative.loc[:,['median_views','80pct_views','20pct_views']] = views_cumulative.loc[:,['median_views','80pct_views','20pct_views']].cumsum()

# dashboard
selection = st.sidebar.selectbox('Aggregate or Individual Video', ['Aggregate Metrics','Individual Video Analysis'])
if selection == 'Aggregate Metrics':
    # metrics
    df_agg_metrics = df_agg[['Video publish time', 'Views', 'Likes','Subscribers', 'Shares', 'Comments added',
                             'RPM(USD)','Average % viewed', 'Avg_duration_sec',
                             'Engagement_ratio', 'Views / sub gained']]
    metric_date_6months = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months=6)
    metric_date_12months = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months=12)
    metric_medians6months = df_agg_metrics[df_agg_metrics['Video publish time'] >= metric_date_6months].select_dtypes(include='number').median()
    metric_medians12months = df_agg_metrics[df_agg_metrics['Video publish time'] >= metric_date_12months].select_dtypes(include='number').median()

    col1, col2, col3, col4, col5 = st.columns(5)
    columns = [col1, col2, col3, col4, col5]
    count = 0
    for i in metric_medians6months.index:
        with columns[count]:
            delta = (metric_medians6months[i] - metric_medians12months[i]) / metric_medians12months[i]
            st.metric(label=i, value=round(metric_medians6months[i], 1), delta="{:.2%}".format(delta))
            count += 1
            count %= 5

    # list
    df_agg_diff['Publish_date'] = df_agg_diff['Video publish time'].apply(lambda x: x.date())
    df_agg_diff_final = df_agg_diff[['Video title', 'Publish_date', 'Views', 'Likes', 'Subscribers', 'Shares',
                                     'Comments added','RPM(USD)','Average % viewed',
                                     'Avg_duration_sec', 'Engagement_ratio','Views / sub gained']]

    numeric_cols = np.array((df_agg_diff.dtypes == 'float64') | (df_agg_diff.dtypes == 'int64'))
    st.dataframe(df_agg_diff_final.style.hide()
                 .map(style_negative, props='color: red;')
                 .map(style_positive, props='color: green;')
                 .format({col: "{:.1%}" for col in df_agg_diff_final.select_dtypes(include="number").columns})
                 )

if selection == 'Individual Video Analysis':
    videos = df_agg["Video title"]
    selected_video = st.selectbox("Pick a video", videos)

    # views - subscribe chart colored by country
    agg_filtered = df_agg[df_agg["Video title"] == selected_video]
    agg_sub_filtered = df_agg_sub[df_agg_sub["Video Title"] == selected_video]
    agg_sub_filtered['Country'] = agg_sub_filtered['Country Code'].apply(audience_simple)
    agg_sub_filtered.sort_values('Is Subscribed', inplace=True)
    fig = px.bar(agg_sub_filtered, x ='Views', y='Is Subscribed', color ='Country', orientation ='h')
    st.plotly_chart(fig)


    agg_time_filtered = df_time_diff[df_time_diff['Video Title'] == selected_video]
    first_30 = agg_time_filtered[agg_time_filtered['days_published'].between(0, 30)]
    first_30 = first_30.sort_values('days_published')

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['20pct_views'],
                              mode='lines',
                              name='20th percentile', line=dict(color='purple', dash='dash')))

    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['median_views'],
                              mode='lines',
                              name='50th percentile', line=dict(color='white', dash='dash')))

    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['80pct_views'],
                              mode='lines',
                              name='80th percentile', line=dict(color='royalblue', dash ='dash')))

    fig2.add_trace(go.Scatter(x=first_30['days_published'], y=first_30['Views'].cumsum(),
                              mode='lines',
                              name='Current Video' ,line=dict(color='firebrick', width=8)))

    fig2.update_layout(title='View comparison first 30 days',
                       xaxis_title='Days Since Published',
                       yaxis_title='Cumulative views')

    st.plotly_chart(fig2)

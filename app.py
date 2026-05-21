from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st


APP_TITLE = "Career Leads Dashboard"
DEFAULT_DATA_PATH = Path("/Users/tylerstahl/Downloads/Lead Tracker_ CoS-AI - Sheet1.csv")
DATE_COLUMNS = ["Logged At", "Last Contact Date", "Follow-up By"]
CATEGORICAL_COLUMNS = ["Lead Type", "Relationship Status", "Channel"]
TEXT_COLUMNS = ["Contact Name", "Organization", "Next Action", "Source / URL", "Notes"]


st.set_page_config(page_title=APP_TITLE, page_icon="📌", layout="wide")


@st.cache_data(show_spinner=False)
def load_leads(uploaded_file, default_path_text: str) -> pd.DataFrame:
    source = uploaded_file if uploaded_file is not None else Path(default_path_text)
    df = pd.read_csv(source)
    df.columns = [str(column).strip() for column in df.columns]

    for column in DATE_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce", format="mixed", utc=True).dt.tz_localize(None)

    for column in df.columns:
        if pd.api.types.is_object_dtype(df[column]) or pd.api.types.is_string_dtype(df[column]):
            df[column] = df[column].fillna("").astype(str).str.strip()

    return df


def filter_by_multiselect(df: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    if column not in df.columns:
        return df

    options = sorted(value for value in df[column].dropna().unique() if str(value).strip())
    selected = st.sidebar.multiselect(label, options=options, default=options)
    if selected:
        return df[df[column].isin(selected)]
    return df.iloc[0:0]


def filter_by_date_range(df: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    if column not in df.columns or df[column].dropna().empty:
        return df

    dates = df[column].dropna()
    min_date = dates.min().date()
    max_date = dates.max().date()
    selected_start, selected_end = st.sidebar.date_input(
        label,
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    start = pd.Timestamp(selected_start)
    end = pd.Timestamp(selected_end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    return df[df[column].isna() | df[column].between(start, end)]


def apply_text_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query:
        return df

    searchable_columns = [column for column in TEXT_COLUMNS if column in df.columns]
    if not searchable_columns:
        return df

    normalized_query = query.casefold()
    mask = df[searchable_columns].apply(
        lambda row: row.astype(str).str.casefold().str.contains(normalized_query, regex=False).any(),
        axis=1,
    )
    return df[mask]


def sort_dataframe(df: pd.DataFrame, column: str, ascending: bool) -> pd.DataFrame:
    if column not in df.columns:
        return df

    helper = df[column].isna() if pd.api.types.is_datetime64_any_dtype(df[column]) else df[column].eq("")
    return (
        df.assign(_blank_sort=helper)
        .sort_values(by=["_blank_sort", column], ascending=[True, ascending], kind="mergesort")
        .drop(columns="_blank_sort")
    )


def frame_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Filtered Leads")
    return output.getvalue()


def metric_value(df: pd.DataFrame, column: str, value: str) -> int:
    if column not in df.columns:
        return 0
    return int(df[column].astype(str).str.casefold().eq(value.casefold()).sum())


st.title(APP_TITLE)

uploaded_file = st.sidebar.file_uploader("Upload a CSV", type=["csv"])

try:
    leads = load_leads(uploaded_file, str(DEFAULT_DATA_PATH))
except FileNotFoundError:
    st.error(f"Could not find the default CSV at {DEFAULT_DATA_PATH}. Upload a CSV to continue.")
    st.stop()
except Exception as error:
    st.error(f"Could not load the leads spreadsheet: {error}")
    st.stop()

if leads.empty:
    st.warning("The selected leads spreadsheet is empty.")
    st.stop()

filtered = leads.copy()

st.sidebar.header("Filters")
search_query = st.sidebar.text_input("Search names, organizations, actions, sources, and notes")
filtered = apply_text_search(filtered, search_query)

for categorical_column in CATEGORICAL_COLUMNS:
    filtered = filter_by_multiselect(filtered, categorical_column, categorical_column)

filtered = filter_by_date_range(filtered, "Follow-up By", "Follow-up due window")
filtered = filter_by_date_range(filtered, "Last Contact Date", "Last contact window")

st.sidebar.header("Sort")
sort_options = list(filtered.columns if len(filtered.columns) else leads.columns)
default_sort_index = sort_options.index("Follow-up By") if "Follow-up By" in sort_options else 0
sort_column = st.sidebar.selectbox("Sort by", options=sort_options, index=default_sort_index)
sort_direction = st.sidebar.radio("Direction", options=["Ascending", "Descending"], horizontal=True)
filtered = sort_dataframe(filtered, sort_column, sort_direction == "Ascending")

total_leads = len(leads)
visible_leads = len(filtered)
due_this_week = 0
overdue = 0
if "Follow-up By" in leads.columns:
    today = pd.Timestamp.today().normalize()
    due_dates = filtered["Follow-up By"].dropna()
    due_this_week = int(due_dates.between(today, today + pd.Timedelta(days=7)).sum())
    overdue = int((due_dates < today).sum())

metrics = st.columns(5)
metrics[0].metric("Visible leads", f"{visible_leads:,}", f"of {total_leads:,}")
metrics[1].metric("Warm", metric_value(filtered, "Relationship Status", "warm"))
metrics[2].metric("Recruiters", metric_value(filtered, "Lead Type", "recruiter"))
metrics[3].metric("Due next 7 days", due_this_week)
metrics[4].metric("Overdue", overdue)

tab_table, tab_summary, tab_export = st.tabs(["Leads", "Summary", "Export"])

with tab_table:
    st.dataframe(
        filtered,
        width="stretch",
        hide_index=True,
        column_config={
            "Source / URL": st.column_config.LinkColumn("Source / URL", display_text="Open link"),
            "Logged At": st.column_config.DatetimeColumn("Logged At", format="YYYY-MM-DD HH:mm"),
            "Last Contact Date": st.column_config.DateColumn("Last Contact Date", format="YYYY-MM-DD"),
            "Follow-up By": st.column_config.DateColumn("Follow-up By", format="YYYY-MM-DD"),
        },
    )

with tab_summary:
    summary_columns = st.columns(3)
    for idx, column in enumerate(CATEGORICAL_COLUMNS):
        with summary_columns[idx]:
            st.subheader(column)
            if column in filtered.columns and not filtered.empty:
                counts = filtered[column].replace("", "(blank)").value_counts().rename_axis(column).reset_index(name="Count")
                st.bar_chart(counts, x=column, y="Count", width="stretch")
                st.dataframe(counts, hide_index=True, width="stretch")
            else:
                st.caption("No data for the current filters.")

    if "Follow-up By" in filtered.columns:
        st.subheader("Upcoming Follow-ups")
        upcoming = (
            filtered.dropna(subset=["Follow-up By"])
            .sort_values("Follow-up By")
            .loc[:, [column for column in ["Follow-up By", "Contact Name", "Organization", "Next Action"] if column in filtered.columns]]
            .head(10)
        )
        st.dataframe(upcoming, hide_index=True, width="stretch")

with tab_export:
    st.write(f"Exporting {visible_leads:,} filtered lead{'s' if visible_leads != 1 else ''}.")
    st.download_button(
        "Download filtered CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="career_leads_filtered.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download filtered Excel workbook",
        data=frame_to_excel_bytes(filtered),
        file_name="career_leads_filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

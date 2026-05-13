"""
WAEC Education Analytics — Performance Report Generator
Connects to SQL Server, runs performance queries, generates PDF report
Filtered to:
- ExamYear: 2015 to 2025
- State: Oyo
"""

import os
import io
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image
)


# ─────────────────────────────────────────────
# 1. DATABASE CONNECTION
# ─────────────────────────────────────────────
def get_connection():
    """Connect to WAECDBEdustat SQL Server database."""
    import pyodbc

    server = '10.2.2.19,1433'
    database = 'WAECDBEdustat'
    username = 'eduuser'
    password = 'eduaccess@123'

    conn_str = (
        f'DRIVER={{SQL Server}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={username};'
        f'PWD={password};'
        f'TrustServerCertificate=yes;'
    )

    return pyodbc.connect(conn_str)


# ─────────────────────────────────────────────
# 2. LOAD DATA
# ─────────────────────────────────────────────
def load_data():
    query = """
        SELECT
            ExamYear,
            ExamNum,
            centre,
            State,
            Subject,
            Grade,
            Status,
            LGA
        FROM dbo.data_client
    """

    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    return df


# ─────────────────────────────────────────────
# 3. PREPARE DATA
# ─────────────────────────────────────────────
def prepare_data(df):
    df = df.copy()

    text_cols = ['centre', 'State', 'Subject', 'Grade', 'Status', 'LGA']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str).str.strip()

    df['subject_clean'] = df['Subject'].str.lower().str.strip()
    df['status_clean'] = df['Status'].str.lower().str.strip()
    df['is_credit'] = (df['status_clean'] == 'credit').astype(int)

    return df


# ─────────────────────────────────────────────
# 4. SUMMARY STATISTICS
# ─────────────────────────────────────────────
def generate_summary_statistics(df):
    """
    High-level summary stats for the report front page.
    """
    total_subject_rows = int(len(df))
    total_candidates = int(df['ExamNum'].nunique())
    total_centres = int(df['centre'].nunique())
    total_lgas = int(df['LGA'].nunique())
    year_min = int(df['ExamYear'].min())
    year_max = int(df['ExamYear'].max())

    overall_credit_rate = round(df['is_credit'].mean() * 100, 2) if len(df) else 0.0

    candidate_summary = build_candidate_summary(df)
    five_credit_rate = round(candidate_summary['qualified_5_credits'].mean() * 100, 2) if len(candidate_summary) else 0.0

    top_lga_by_candidates = (
        df.groupby('LGA')['ExamNum']
        .nunique()
        .sort_values(ascending=False)
    )
    top_lga_name = top_lga_by_candidates.index[0] if not top_lga_by_candidates.empty else 'N/A'
    top_lga_candidates = int(top_lga_by_candidates.iloc[0]) if not top_lga_by_candidates.empty else 0

    yearly_candidates = (
        df.groupby('ExamYear')['ExamNum']
        .nunique()
        .reset_index(name='CandidateCount')
        .sort_values('CandidateCount', ascending=False)
    )
    peak_year = int(yearly_candidates.iloc[0]['ExamYear']) if not yearly_candidates.empty else None
    peak_year_candidates = int(yearly_candidates.iloc[0]['CandidateCount']) if not yearly_candidates.empty else 0

    summary_df = pd.DataFrame([
        ['Reporting Period', f'{year_min} - {year_max}'],
        ['Total Subject Records', f'{total_subject_rows:,}'],
        ['Total Candidates', f'{total_candidates:,}'],
        ['Total Centres', f'{total_centres:,}'],
        ['Total LGAs', f'{total_lgas:,}'],
        ['Overall Subject Credit Rate (%)', f'{overall_credit_rate:.2f}'],
        ['5 Credits incl. English & Maths (%)', f'{five_credit_rate:.2f}'],
        ['Top LGA by Candidate Count', f'{top_lga_name} ({top_lga_candidates:,})'],
        ['Peak Candidate Year', f'{peak_year} ({peak_year_candidates:,})' if peak_year else 'N/A'],
    ], columns=['Metric', 'Value'])

    return summary_df


# ─────────────────────────────────────────────
# 5. SCHOOL PERFORMANCE TREND
# ─────────────────────────────────────────────
def school_performance_trend(df):
    grouped = (
        df.groupby(['ExamYear', 'centre', 'LGA'], as_index=False)
          .agg(
              total_records=('ExamNum', 'count'),
              credit_records=('is_credit', 'sum')
          )
    )

    grouped['percentage_performance'] = (
        grouped['credit_records'] / grouped['total_records'] * 100
    ).round(2)

    return grouped.sort_values(['LGA', 'centre', 'ExamYear'])


# ─────────────────────────────────────────────
# 6. LGA PERFORMANCE TREND
# ─────────────────────────────────────────────
def lga_performance_trend(df):
    grouped = (
        df.groupby(['ExamYear', 'LGA'], as_index=False)
          .agg(
              total_records=('ExamNum', 'count'),
              credit_records=('is_credit', 'sum')
          )
    )

    grouped['percentage_performance'] = (
        grouped['credit_records'] / grouped['total_records'] * 100
    ).round(2)

    return grouped.sort_values(['LGA', 'ExamYear'])


# ─────────────────────────────────────────────
# 7. CANDIDATE COUNTS
# ─────────────────────────────────────────────
def candidate_count_by_lga(df):
    out = (
        df.groupby('LGA', as_index=False)
          .agg(CandidateCount=('ExamNum', 'nunique'))
          .sort_values('CandidateCount', ascending=False)
    )
    return out


def candidate_trend_by_year_lga(df):
    out = (
        df.groupby(['ExamYear', 'LGA'], as_index=False)
          .agg(CandidateCount=('ExamNum', 'nunique'))
          .sort_values(['LGA', 'ExamYear'])
    )
    return out


# ─────────────────────────────────────────────
# 8. 5 CREDITS INCLUDING ENGLISH & MATHS
# ─────────────────────────────────────────────
def build_candidate_summary(df):
    candidate_subjects = df.copy()

    candidate_subjects['is_english_credit'] = (
        candidate_subjects['subject_clean'].eq('english language') &
        candidate_subjects['status_clean'].eq('credit')
    ).astype(int)

    maths_names = ['mathematics', 'general mathematics']
    candidate_subjects['is_maths_credit'] = (
        candidate_subjects['subject_clean'].isin(maths_names) &
        candidate_subjects['status_clean'].eq('credit')
    ).astype(int)

    candidate_summary = (
        candidate_subjects.groupby(
            ['ExamYear', 'ExamNum', 'centre', 'LGA'],
            as_index=False
        )
        .agg(
            total_credit_subjects=('is_credit', 'sum'),
            english_credit=('is_english_credit', 'max'),
            maths_credit=('is_maths_credit', 'max')
        )
    )

    candidate_summary['qualified_5_credits'] = (
        (candidate_summary['total_credit_subjects'] >= 5) &
        (candidate_summary['english_credit'] == 1) &
        (candidate_summary['maths_credit'] == 1)
    ).astype(int)

    return candidate_summary


def five_credits_with_english_maths(df):
    candidate_summary = build_candidate_summary(df)

    yearly = (
        candidate_summary.groupby('ExamYear', as_index=False)
        .agg(
            total_students=('ExamNum', 'count'),
            qualified_students=('qualified_5_credits', 'sum')
        )
    )
    yearly['percentage_performance'] = (
        yearly['qualified_students'] / yearly['total_students'] * 100
    ).round(2)

    school_yearly = (
        candidate_summary.groupby(['ExamYear', 'centre', 'LGA'], as_index=False)
        .agg(
            total_students=('ExamNum', 'count'),
            qualified_students=('qualified_5_credits', 'sum')
        )
    )
    school_yearly['percentage_performance'] = (
        school_yearly['qualified_students'] / school_yearly['total_students'] * 100
    ).round(2)

    lga_yearly = (
        candidate_summary.groupby(['ExamYear', 'LGA'], as_index=False)
        .agg(
            total_students=('ExamNum', 'count'),
            qualified_students=('qualified_5_credits', 'sum')
        )
    )
    lga_yearly['percentage_performance'] = (
        lga_yearly['qualified_students'] / lga_yearly['total_students'] * 100
    ).round(2)

    return candidate_summary, yearly, school_yearly, lga_yearly


# ─────────────────────────────────────────────
# 9. TOP PERFORMERS
# ─────────────────────────────────────────────
def top_average_performance(df_grouped, group_col, top_n=10):
    summary = (
        df_grouped.groupby(group_col, as_index=False)['percentage_performance']
        .mean()
        .rename(columns={'percentage_performance': 'avg_percentage_performance'})
        .sort_values('avg_percentage_performance', ascending=False)
        .head(top_n)
    )

    summary['avg_percentage_performance'] = summary['avg_percentage_performance'].round(2)
    return summary


# ─────────────────────────────────────────────
# 10. CHART HELPERS
# ─────────────────────────────────────────────
def plot_line_chart(df, x_col, y_col, group_col, title, top_n=5):
    top_groups = (
        df.groupby(group_col)[y_col]
          .mean()
          .sort_values(ascending=False)
          .head(top_n)
          .index
          .tolist()
    )

    plot_df = df[df[group_col].isin(top_groups)].copy()

    plt.figure(figsize=(10, 5))
    for name, g in plot_df.groupby(group_col):
        g = g.sort_values(x_col)
        plt.plot(g[x_col], g[y_col], marker='o', label=str(name))

    plt.title(title)
    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.ylim(0, 100)
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.legend(fontsize=8, loc='best')
    plt.tight_layout()

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=200, bbox_inches='tight')
    plt.close()
    img_buffer.seek(0)
    return img_buffer


def plot_bar_chart(df, category_col, value_col, title):
    plt.figure(figsize=(10, 5))
    plt.bar(df[category_col].astype(str), df[value_col])
    plt.title(title)
    plt.xlabel(category_col)
    plt.ylabel(value_col)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=200, bbox_inches='tight')
    plt.close()
    img_buffer.seek(0)
    return img_buffer


# ─────────────────────────────────────────────
# 11. WATERMARK
# ─────────────────────────────────────────────
def add_watermark(canvas, doc, watermark_path=None):
    canvas.saveState()
    page_width, page_height = A4

    if watermark_path and os.path.exists(watermark_path):
        try:
            img = ImageReader(watermark_path)
            img_width = 12 * cm
            img_height = 12 * cm
            x = (page_width - img_width) / 2
            y = (page_height - img_height) / 2

            if hasattr(canvas, "setFillAlpha"):
                canvas.setFillAlpha(0.08)

            canvas.drawImage(
                img,
                x,
                y,
                width=img_width,
                height=img_height,
                preserveAspectRatio=True,
                mask='auto'
            )

            if hasattr(canvas, "setFillAlpha"):
                canvas.setFillAlpha(1)
        except Exception:
            pass
    else:
        if hasattr(canvas, "setFillAlpha"):
            canvas.setFillAlpha(0.08)

        canvas.setFont("Helvetica-Bold", 40)
        canvas.setFillColor(colors.grey)
        canvas.translate(page_width / 2, page_height / 2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, "CONFIDENTIAL")

        if hasattr(canvas, "setFillAlpha"):
            canvas.setFillAlpha(1)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(2 * cm, 1 * cm, "WAEC Education Analytics Report - Oyo State")
    canvas.drawRightString(
        page_width - 2 * cm,
        1 * cm,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    canvas.restoreState()


# ─────────────────────────────────────────────
# 12. TABLE FORMATTER
# ─────────────────────────────────────────────
def dataframe_to_table(df, max_rows=20, col_widths=None):
    if df.empty:
        table = Table([["No data available"]], colWidths=[16 * cm])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        return table

    display_df = df.head(max_rows).copy()
    data = [list(display_df.columns)] + display_df.values.tolist()

    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return table


# ─────────────────────────────────────────────
# 13. PDF REPORT BUILDER
# ─────────────────────────────────────────────
def build_pdf_report(
    output_path,
    summary_stats,
    candidate_by_lga,
    school_trend,
    lga_trend,
    five_credit_yearly,
    top_schools,
    top_lgas,
    school_chart,
    lga_chart,
    five_credit_chart,
    candidate_chart,
    watermark_path=None
):
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#12344D"),
        spaceAfter=12
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor("#1F4E78"),
        alignment=TA_LEFT,
        spaceAfter=6,
        spaceBefore=6
    )

    normal_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        leading=13
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    story = []

    story.append(Paragraph("WAEC Education Analytics Performance Report", title_style))
    story.append(Paragraph("State: Oyo | Scope: Top 5 LGAs | Reporting Period: 2015 to 2025", normal_style))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Executive Summary", heading_style))
    story.append(Paragraph(
        "This report summarizes candidate distribution, school performance, "
        "LGA performance, and the percentage of students who achieved five credits "
        "including English Language and Mathematics.",
        normal_style
    ))
    story.append(Spacer(1, 0.2 * cm))
    story.append(dataframe_to_table(summary_stats, max_rows=len(summary_stats), col_widths=[8 * cm, 8 * cm]))
    story.append(PageBreak())

    story.append(Paragraph("Candidate Distribution by LGA", heading_style))
    story.append(Image(candidate_chart, width=17 * cm, height=8.5 * cm))
    story.append(Spacer(1, 0.3 * cm))
    story.append(dataframe_to_table(candidate_by_lga, max_rows=10))
    story.append(PageBreak())

    story.append(Paragraph("Top 10 Schools by Average Performance", heading_style))
    story.append(dataframe_to_table(top_schools))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Top LGAs by Average Performance", heading_style))
    story.append(dataframe_to_table(top_lgas))
    story.append(PageBreak())

    story.append(Paragraph("School Performance Trend (Top 5 Schools)", heading_style))
    story.append(Image(school_chart, width=17 * cm, height=8.5 * cm))
    story.append(Spacer(1, 0.3 * cm))
    story.append(dataframe_to_table(
        school_trend[['ExamYear', 'centre', 'LGA', 'percentage_performance']].head(20)
    ))
    story.append(PageBreak())

    story.append(Paragraph("LGA Performance Trend", heading_style))
    story.append(Image(lga_chart, width=17 * cm, height=8.5 * cm))
    story.append(Spacer(1, 0.3 * cm))
    story.append(dataframe_to_table(
        lga_trend[['ExamYear', 'LGA', 'percentage_performance']].head(20)
    ))
    story.append(PageBreak())

    story.append(Paragraph("Students with 5 Credits Including English and Mathematics", heading_style))
    story.append(Image(five_credit_chart, width=17 * cm, height=8.5 * cm))
    story.append(Spacer(1, 0.3 * cm))
    story.append(dataframe_to_table(five_credit_yearly))

    doc.build(
        story,
        onFirstPage=lambda canvas, doc: add_watermark(canvas, doc, watermark_path),
        onLaterPages=lambda canvas, doc: add_watermark(canvas, doc, watermark_path)
    )


# ─────────────────────────────────────────────
# 14. MAIN
# ─────────────────────────────────────────────
def main():
    print("Loading data from SQL Server...")
    df = load_data()
    print(f"Rows loaded: {len(df):,}")

    print("Preparing data...")
    df = prepare_data(df)

    if df.empty:
        raise ValueError("No data found in dbo.data_client.")

    print("Generating summary statistics...")
    summary_stats = generate_summary_statistics(df)

    print("Calculating candidate counts...")
    candidate_by_lga = candidate_count_by_lga(df)

    print("Calculating school performance trend...")
    school_trend = school_performance_trend(df)

    print("Calculating LGA performance trend...")
    lga_trend = lga_performance_trend(df)

    print("Calculating 5 credits including English and Maths...")
    _, five_credit_yearly, five_credit_school, five_credit_lga = five_credits_with_english_maths(df)

    print("Calculating top schools and top LGAs...")
    top_schools = top_average_performance(school_trend, 'centre', top_n=10)
    top_lgas = top_average_performance(lga_trend, 'LGA', top_n=10)

    print("Generating charts...")
    candidate_chart = plot_bar_chart(
        candidate_by_lga,
        category_col='LGA',
        value_col='CandidateCount',
        title='Candidate Distribution Across Top 5 LGAs'
    )

    school_chart = plot_line_chart(
        school_trend,
        x_col='ExamYear',
        y_col='percentage_performance',
        group_col='centre',
        title='School Performance Trend (Top 5 Schools by Average Performance)',
        top_n=5
    )

    lga_chart = plot_line_chart(
        lga_trend,
        x_col='ExamYear',
        y_col='percentage_performance',
        group_col='LGA',
        title='LGA Performance Trend',
        top_n=5
    )

    five_credit_chart = plot_bar_chart(
        five_credit_yearly,
        category_col='ExamYear',
        value_col='percentage_performance',
        title='Percentage of Students with 5 Credits Including English and Mathematics'
    )

    output_pdf = "waec_performance_report_oyo_top5_lga_2015_2025.pdf"
    watermark_path = r"C:\Users\uludoh\Downloads\image 2.jpg"

    print("Building PDF...")
    build_pdf_report(
        output_path=output_pdf,
        summary_stats=summary_stats,
        candidate_by_lga=candidate_by_lga,
        school_trend=school_trend,
        lga_trend=lga_trend,
        five_credit_yearly=five_credit_yearly,
        top_schools=top_schools,
        top_lgas=top_lgas,
        school_chart=school_chart,
        lga_chart=lga_chart,
        five_credit_chart=five_credit_chart,
        candidate_chart=candidate_chart,
        watermark_path=watermark_path
    )

    print(f"Done. Report saved as: {output_pdf}")


if __name__ == "__main__":
    main()
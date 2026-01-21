def generate_report_summary(
    report_group: str,
    total_records: int,
    metrics: dict,
    applied_filters: dict
) -> str:
    """
    Returns a professional summary paragraph based on report group and metrics.
    """

    base_intro = (
        "This report presents an analytical overview of candidate participation under the "
        f"<b>{report_group}</b> category. "
        f"The analysis covers a total of <b>{total_records:,} candidates</b>, "
    )

    # ===================== GROUP-SPECIFIC TEXT =====================

    if report_group == "Demographic Analysis":
        summary = (
            base_intro +
            "evaluated across key demographic attributes including "
            "<b>sex, age, disability status, and examination year</b>. "
            f"The modal age observed in the dataset is <b>{metrics.get('modal_age')}</b>, "
            f"with <b>{metrics.get('female_pct')}%</b> female participation. "
        )

    elif report_group == "Geographic & Institutional Insights":
        summary = (
            base_intro +
            "focused on <b>state-level and examination centre participation</b>. "
            f"The highest participation was recorded in <b>{metrics.get('top_state')}</b>, "
            f"with <b>{metrics.get('top_state_count'):,}</b> candidates. "
            "This report highlights geographic concentration and institutional demand patterns."
        )

    elif report_group == "Equity & Sponsorship":
        summary = (
            base_intro +
            "examining <b>sponsorship types and equity indicators</b>. "
            f"<b>{metrics.get('sponsored_pct')}%</b> of candidates were sponsored, "
            "providing insight into access, funding support, and inclusion outcomes."
        )

    elif report_group == "Temporal & Progression Trends":
        summary = (
            base_intro +
            "tracking <b>year-on-year participation trends</b>. "
            f"The highest candidate volume was recorded in <b>{metrics.get('peak_year')}</b>, "
            "indicating significant temporal growth and participation shifts over time."
        )

    else:
        summary = (
            base_intro +
            "based on the selected filters and dimensions. "
            "The report provides a structured summary of participation patterns across the dataset."
        )

    return summary
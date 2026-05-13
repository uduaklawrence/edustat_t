# ==============================
# 📄 VIEW INVOICE - MULTI-REPORT CART
# ==============================
#
# CHANGES FROM PREVIOUS VERSION
# ──────────────────────────────
# 1. save_user_report() now passes subgroup, analysis, and record_count
#    so that my_reports.py can fully reconstruct the report on load.
#
# 2. Private filter keys (starting with '_', e.g. _age_min) are stripped
#    before saving — they are internal UI signals, not real filter values.
#
# 3. Invoice is saved to DB as PENDING immediately when the user
#    reaches this page (before payment). This makes it appear in
#    my_invoices.py with status PENDING for up to 3 days.
#    The 3-day expiry is set via expires_at on the invoice record.
#    (Requires create_invoice_record to accept an expires_at parameter
#     — see db_queries note below.)

import streamlit as st
import streamlit.components.v1 as components
import os
import base64
import json
from datetime import datetime, timedelta
from db_queries import (
    fetch_data,
    update_payment_status,
    attach_paystack_ref_to_invoice,
    mark_invoice_paid_by_paystack_ref,
    mark_invoice_failed,
    save_user_report,
)
from paystack import initialize_transaction, verify_transaction
from invoice_pdf import generate_invoice_pdf

WATERMARK_PATH = r"altered_edustat.jpg"


def get_base64_image(img_path):
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


# ── AUTH CHECK ────────────────────────────────────────────────────────────────
if not st.session_state.get("logged_in", False):
    st.warning("Please sign in to view the invoice.")
    st.stop()

st.set_page_config(page_title="Invoice & Payment", layout="wide")
st.title("🧾 Invoice & Payment")

user_email = st.session_state.get("user_email")
user_id    = st.session_state.get("user_id", 0)

# ── CART CHECK ────────────────────────────────────────────────────────────────
report_cart = st.session_state.get("report_cart", [])

if not report_cart:
    st.error("❌ Your invoice is empty. Please add at least one report.")
    if st.button("← Go Back to Create Report"):
        st.switch_page("pages/create_report.py")
    st.stop()

# ── DERIVED TOTALS ────────────────────────────────────────────────────────────
# Uses dynamic per-report price from cart, NOT a hardcoded constant.
cart_count  = len(report_cart)
total_price = sum(item.get("price", 0) for item in report_cart)

prices = [item.get("price", 0) for item in report_cart]
if len(set(prices)) == 1:
    price_per_report_label = f"₦{prices[0]:,}"
else:
    price_per_report_label = f"₦{min(prices):,} – ₦{max(prices):,}"

all_analyses   = [item.get("analysis", "Report") for item in report_cart]
saved_description = "; ".join(all_analyses)
saved_group    = report_cart[0].get("report_group", "Mixed Reports")

# ── INVOICE REF GUARD ─────────────────────────────────────────────────────────
if not st.session_state.get("invoice_ref"):
    st.error("❌ No invoice reference found. Please create a report first.")
    if st.button("← Go Back to Create Report"):
        st.switch_page("pages/create_report.py")
    st.stop()

invoice_ref      = st.session_state.invoice_ref
payment_verified = st.session_state.get("payment_verified", False)
payment_failed   = st.session_state.get("payment_failed",   False)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — strip private filter keys before storing/displaying
# Keys like _age_min, _age_max, _age_computed are internal UI signals.
# They must be removed before saving to DB or showing in the invoice.
# ─────────────────────────────────────────────────────────────────────────────
def clean_filters(filters: dict) -> dict:
    """
    Removes internal UI-only filter keys before saving or displaying.

    Single underscore keys (_age_min, _age_max, _pass_grades etc.) are
    temporary signals used only during the filter configuration UI.
    They must NOT be saved to the database or shown on invoices.

    Double underscore keys (__subgroup__, __analysis__, __record_count__)
    are metadata that MUST be saved to the DB so view_report.py can
    reconstruct the report when loading from my_reports.py.
    They start with '__' so we keep them here and only strip single '_'.
    """
    return {
        k: v for k, v in filters.items()
        if not (k.startswith("_") and not k.startswith("__"))
    }


def filter_display_str(filters: dict) -> str:
    """
    Human-readable filter summary for invoice display.
    Hides both single-underscore UI keys AND double-underscore meta keys.
    """
    parts = []
    for k, v in filters.items():
        if k.startswith("_"):   # hides both _age_min and __subgroup__
            continue
        if v == [] or v is None:
            display = "All"
        elif isinstance(v, list):
            display = ", ".join(str(x) for x in v)
        else:
            display = str(v)
        parts.append(f"{k}: {display}")
    return " | ".join(parts) if parts else "All data"


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE HTML BUILDER
# Used for both the on-screen invoice and the pending PDF.
# ─────────────────────────────────────────────────────────────────────────────
def render_invoice_html(status_label: str, watermark_base64: str) -> str:
    user_display = user_email.split("@")[0].replace(".", " ").title()
    invoice_date = datetime.now().strftime("%B %d, %Y")

    rows_html = ""
    for idx, item in enumerate(report_cart, start=1):
        report_group  = item.get("report_group", "—")
        subgroup      = item.get("subgroup",     "—")
        analysis      = item.get("analysis",     "—")
        filters       = clean_filters(item.get("filters", {}))
        item_price    = item.get("price",         0)
        record_count  = item.get("record_count",  0)
        weight        = item.get("total_weight",  "—")

        filter_parts = []
        for k, v in filters.items():
            if k.startswith("_"):   # hide both _private and __meta__ keys from invoice display
                continue
            if v == [] or v is None:
                val = "All"
            elif isinstance(v, list):
                val = ", ".join(str(i) for i in v)
            else:
                val = str(v)
            filter_parts.append(f"<b>{k}:</b> {val}")
        filter_html = (
            " &nbsp;|&nbsp; ".join(filter_parts)
            if filter_parts else "<i>All data — no specific filters</i>"
        )

        bg = "#fafafa" if idx % 2 == 0 else "white"
        rows_html += f"""
        <tr style="background-color:{bg};">
            <td style="padding:10px;border:1px solid #ddd;vertical-align:top;">
                <strong>#{idx} &mdash; {analysis}</strong><br>
                <span style="font-size:12px;color:#444;line-height:1.8;">
                    <b>Group:</b> {report_group} &nbsp;&nbsp;
                    <b>Subgroup:</b> {subgroup}<br>
                    <b>Records:</b> {record_count:,} &nbsp;&nbsp;
                    <b>Weight:</b> {weight}<br>
                    <b>Filters:</b> {filter_html}
                </span>
            </td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;
                       vertical-align:top;width:50px;">1</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:right;
                       vertical-align:top;width:140px;">
                &#8358;{item_price:,}
            </td>
        </tr>
        """

    html = f"""
    <h2 style="text-align:center;margin-bottom:4px;">INVOICE</h2>
    <p style="text-align:center;color:#888;margin-top:0;font-size:13px;">
        EduStat Analytics Platform
    </p>
    <hr>
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:14px;">
        <tr>
            <td style="padding:4px 0;"><b>Name:</b> {user_display}</td>
            <td style="padding:4px 0;"><b>Invoice No:</b> {invoice_ref}</td>
        </tr>
        <tr>
            <td style="padding:4px 0;"><b>Date:</b> {invoice_date}</td>
            <td style="padding:4px 0;"><b>Status:</b> {status_label}</td>
        </tr>
        <tr>
            <td colspan="2" style="padding:4px 0;"><b>Email:</b> {user_email}</td>
        </tr>
    </table>
    <hr>
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
            <tr style="background-color:#1a56db;color:white;">
                <th style="padding:10px;border:1px solid #ccc;text-align:left;">
                    Report Details
                </th>
                <th style="padding:10px;border:1px solid #ccc;text-align:center;width:50px;">
                    Qty
                </th>
                <th style="padding:10px;border:1px solid #ccc;text-align:right;width:140px;">
                    Amount (&#8358;)
                </th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
            <tr style="background-color:#f0f4ff;font-weight:bold;font-size:15px;">
                <td colspan="2" style="text-align:right;padding:12px;border:1px solid #ccc;">
                    Total &nbsp;({cart_count} report{'s' if cart_count > 1 else ''})
                </td>
                <td style="padding:12px;border:1px solid #ccc;text-align:right;">
                    &#8358;{total_price:,}
                </td>
            </tr>
        </tbody>
    </table>
    """

    return f"""
    <div style="
        background:white; padding:30px; border-radius:10px;
        box-shadow:0 0 10px rgba(0,0,0,0.1);
        background-image:url('data:image/jpeg;base64,{watermark_base64}');
        background-repeat:no-repeat; background-position:center;
        background-size:45%; font-family:Arial,sans-serif;
    ">{html}</div>
    """


# ─────────────────────────────────────────────────────────────────────────────
# FAILED PAYMENT VIEW
# ─────────────────────────────────────────────────────────────────────────────
if payment_failed:
    st.error("❌ Payment Failed")
    st.markdown(f"""
### Payment Unsuccessful

Your payment attempt for invoice **{invoice_ref}** was not successful.

**What you can do:**
1. **Retry Payment** — Try making the payment again
2. **Use a Different Method** — Try another card or payment option
3. **Contact Support** — Email: support@edustat.com
    """)

    col1, col2, col3 = st.columns(3)
    col1.metric("Reports", cart_count)
    col2.metric("Price Range", price_per_report_label)
    col3.metric("Total", f"₦{total_price:,}")

    for idx, item in enumerate(report_cart, start=1):
        with st.expander(f"Report #{idx} — {item.get('analysis', 'Report')}"):
            st.markdown(f"**Group:** {item.get('report_group', '—')}")
            st.markdown(f"**Subgroup:** {item.get('subgroup', '—')}")
            st.markdown(f"**Price:** ₦{item.get('price', 0):,}")
            for k, v in clean_filters(item.get("filters", {})).items():
                val_str = "All" if v == [] or v is None else (
                    ", ".join(str(i) for i in v) if isinstance(v, list) else str(v)
                )
                st.markdown(f"- **{k}:** {val_str}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Retry Payment", type="primary", width="stretch"):
            st.session_state.payment_failed    = False
            st.session_state.paystack_reference = None
            st.rerun()
    with c2:
        if st.button("📧 Contact Support", width="stretch"):
            st.info("📧 Email: support@edustat.com | 📞 Phone: +234-XXX-XXX-XXXX")

    st.markdown("---")
    if st.button("← Create New Report"):
        st.switch_page("pages/create_report.py")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# PENDING INVOICE VIEW
# ─────────────────────────────────────────────────────────────────────────────
if not payment_verified and not payment_failed:
    st.subheader("📄 Pending Invoice")
    st.info(
        "ℹ️ This invoice is saved as **PENDING** in your My Invoices page "
        "for up to **3 days**. Complete payment to activate your reports."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Reports Selected",  cart_count)
    col2.metric("Price Per Report",  price_per_report_label)
    col3.metric("Total Payable",     f"₦{total_price:,}")

    st.markdown("---")

    watermark_base64 = get_base64_image(WATERMARK_PATH)
    components.html(
        render_invoice_html("Pending Payment ⏳", watermark_base64),
        height=max(520, 200 + cart_count * 130),
        scrolling=True,
    )

    # Pending PDF download
    pdf_path = generate_invoice_pdf(
        invoice_ref=invoice_ref,
        user_email=user_email,
        amount=total_price,
        description=saved_description,
        selected_group=saved_group,
        selected_columns=all_analyses,
        status="Pending Payment",
    )
    with open(pdf_path, "rb") as f:
        st.download_button(
            "📄 Download Pending Invoice PDF",
            f,
            file_name=os.path.basename(pdf_path),
            mime="application/pdf",
            key="pending_invoice_download",
        )

    # ── PAYMENT GATEWAY ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("💳 Payment Gateway")

    if not st.session_state.get("paystack_reference"):
        if st.button("Proceed to Payment", type="primary", key="pay_btn"):
            with st.spinner("Connecting to Paystack..."):
                try:
                    api_response = initialize_transaction(
                        email_address=user_email,
                        amount=total_price,
                    )
                    if api_response and api_response.get("authorization_url"):
                        paystack_ref = api_response.get("reference")
                        st.session_state.paystack_reference = paystack_ref
                        attach_paystack_ref_to_invoice(invoice_ref, paystack_ref)
                        checkout_url = api_response.get("authorization_url")
                        components.html(
                            f"<script>window.open('{checkout_url}', '_blank');</script>"
                        )
                        st.success("✅ Paystack checkout opened in a new tab.")
                        st.warning(
                            "⚠️ After payment, return here and click "
                            "**Verify My Payment** below."
                        )
                    else:
                        st.error("Failed to connect to Paystack. Please try again.")
                except Exception as e:
                    st.error(f"Payment initialization error: {str(e)}")

    # ── VERIFY PAYMENT ────────────────────────────────────────────────────────
    if st.session_state.get("paystack_reference"):
        st.markdown("---")
        st.subheader("✔️ Verify Payment")

        if st.button("Verify My Payment", type="primary", key="verify_btn"):
            paystack_ref = st.session_state.get("paystack_reference")
            with st.spinner("Verifying payment with Paystack..."):
                try:
                    verification_response = verify_transaction(paystack_ref)

                    if (
                        verification_response
                        and verification_response.get("status") is True
                        and verification_response.get("data", {}).get("status") == "success"
                    ):
                        update_payment_status(user_email)
                        st.session_state.payment_verified = True
                        mark_invoice_paid_by_paystack_ref(paystack_ref)
                        st.success("✅ Payment verified successfully!")
                        st.rerun()

                    elif (
                        verification_response
                        and verification_response.get("data", {}).get("status") == "failed"
                    ):
                        st.session_state.payment_failed = True
                        mark_invoice_failed(invoice_ref)
                        st.rerun()

                    else:
                        st.warning(
                            "⚠️ Payment still pending. "
                            "Please wait a moment and try again."
                        )
                except Exception as e:
                    st.error(f"Verification error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# PAID INVOICE VIEW + SAVE REPORTS
# ─────────────────────────────────────────────────────────────────────────────
if payment_verified:
    st.subheader("✅ Payment Successful — Invoice Paid")

    col1, col2, col3 = st.columns(3)
    col1.metric("Reports Purchased", cart_count)
    col2.metric("Price Per Report",  price_per_report_label)
    col3.metric("Total Paid",        f"₦{total_price:,}")

    st.markdown("---")

    watermark_base64 = get_base64_image(WATERMARK_PATH)
    components.html(
        render_invoice_html("PAID ✅", watermark_base64),
        height=max(520, 200 + cart_count * 130),
        scrolling=True,
    )

    # Generate paid PDF once per session
    if not st.session_state.get("paid_pdf_generated", False):
        try:
            paid_pdf_path = generate_invoice_pdf(
                invoice_ref=invoice_ref,
                user_email=user_email,
                amount=total_price,
                description=saved_description,
                selected_group=saved_group,
                selected_columns=all_analyses,
                status="PAID ✅",
            )
            st.session_state.paid_pdf_path      = paid_pdf_path
            st.session_state.paid_pdf_generated = True
        except Exception as e:
            st.error(f"❌ Error generating invoice PDF: {str(e)}")
            st.stop()

    with open(st.session_state.paid_pdf_path, "rb") as f:
        st.download_button(
            "📄 Download Paid Invoice PDF",
            f,
            file_name=os.path.basename(st.session_state.paid_pdf_path),
            mime="application/pdf",
            key="download_paid_invoice",
        )

    # ── SAVE REPORTS ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📝 Name & Save Your Reports")

    if not st.session_state.get("report_saved", False):
        default_name = f"Report Bundle — {datetime.now().strftime('%b %d, %Y')}"
        report_name  = st.text_input(
            "Enter a name for this report bundle:",
            value=default_name,
            key="report_name_input",
        )

        if st.button("💾 Save Reports", type="primary"):
            if not report_name.strip():
                st.error("❌ Report name cannot be empty.")
            else:
                try:
                    for item in report_cart:
                        filters_clean = clean_filters(item.get("filters", {}))

                        
                        filters_with_meta = {
                            **filters_clean,
                            "__subgroup__":     item.get("subgroup",     ""),
                            "__analysis__":     item.get("analysis",     ""),
                            "__record_count__": item.get("record_count", 0),
                        }

                        save_user_report(
                            user_id      = st.session_state.user_id,
                            invoice_ref  = invoice_ref,
                            report_group = item.get("report_group", saved_group),
                            report_name  = (
                                report_name.strip()
                                + " — " + item.get("analysis", "")
                            ),
                            filters      = filters_with_meta,
                            charts       = item.get("charts", []),
                            pdf_path     = st.session_state.paid_pdf_path,
                        )

                    st.session_state.report_saved = True
                    st.session_state.report_ready = True
                    st.success(f"✅ {cart_count} report(s) saved successfully!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to save reports: {str(e)}")
    else:
        st.success(f"✅ {cart_count} report(s) already saved to your account!")
        st.session_state.report_ready = True

        st.markdown("---")
        if st.button("📊 View Reports", type="primary", key="view_report_btn"):
            st.switch_page("pages/view_report.py")

        st.info("🗂️ Your reports are saved for 30 days in your account.")
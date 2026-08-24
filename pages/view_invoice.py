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
    create_invoice_record,
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
# ── INVOICE REF GUARD — create if not yet created ────────────────────────────
if not st.session_state.get("invoice_ref"):
    if not report_cart:
        st.error("❌ No invoice reference found. Please create a report first.")
        if st.button("← Go Back to Create Report"):
            st.switch_page("pages/create_report.py")
        st.stop()
    else:
        # Cart exists but invoice not yet saved — create it now
        try:
            data_dict = {
                "reports": [
                    {
                        "report_group": item.get("report_group"),
                        "subgroup":     item.get("subgroup"),
                        "analysis":     item.get("analysis"),
                        "filters":      item.get("filters", {}),
                        "record_count": item.get("record_count", 0),
                        "price":        item.get("price"),
                        "total_weight": item.get("total_weight"),
                    }
                    for item in report_cart
                ]
            }
            invoice_ref = create_invoice_record(
                user_id=user_id,
                total=total_price,
                data_dict=data_dict,
            )
            if invoice_ref:
                st.session_state.invoice_ref = invoice_ref
            else:
                st.error("❌ Failed to create invoice. Please try again.")
                st.stop()
        except Exception as e:
            st.error(f"❌ Failed to create invoice: {str(e)}")
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

def render_invoice_html(status_label: str, watermark_base64: str) -> str:
    user_display = user_email.split("@")[0].replace(".", " ").title()
    invoice_date = datetime.now().strftime("%B %d, %Y")
    
    COLOR_NAVY = "#5D768D"
    COLOR_TOTAL_BAR = "#4B6584"
    COLOR_LIGHT_GRAY = "#F4F7F9"

    rows_html = ""
    for idx, item in enumerate(report_cart, start=1):
        bg = COLOR_LIGHT_GRAY if idx % 2 == 0 else "white"
        rows_html += f"""
        <tr style="background-color:{bg};">
            <td style="padding:18px; border-bottom:1px solid #eee;">
                <b style="color:#333; font-size: 15px;">{item.get('analysis', 'Report')}</b><br>
                <small style="color:#666;">Group: {item.get('report_group', '—')} | Subgroup: {item.get('subgroup', '—')}</small>
            </td>
            <td style="padding:18px; text-align:center; border-bottom:1px solid #eee; color:#333;">1</td>
            <td style="padding:18px; text-align:right; border-bottom:1px solid #eee; color:#333; font-weight:bold;">₦{item.get('price', 0):,}</td>
        </tr>
        """

    html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; padding: 50px; background: white; border-radius: 15px; position: relative; overflow: hidden; min-height: 700px; border: 1px solid #ddd;">
        
        <!-- FIXED WATERMARK: Higher opacity + Blending fix -->
        <div style="position: absolute; top: 45%; left: 50%; transform: translate(-50%, -50%) rotate(-45deg); opacity: 0.15; pointer-events: none; z-index: 0;">
            <img src='data:image/jpeg;base64,{watermark_base64}' style='width: 700px; mix-blend-mode: multiply;'/>
        </div>

        <div style="position: relative; z-index: 1;">
            <!-- Header Section -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 50px;">
                <div>
                    <h2 style="margin: 0; color: #1e293b; letter-spacing: 1px; font-size: 26px; font-weight: 800;">EDUSTAT REPORTING SYSTEM</h2>
                    <p style="margin: 0; color: #888; font-size: 14px; font-style: italic;">Powered by Sidmach</p>
                </div>
                <h1 style="margin: 0; font-size: 75px; color: {COLOR_NAVY}; font-weight: 900; letter-spacing: -2px;">INVOICE</h1>
            </div>

            <!-- Customer & Invoice Info -->
            <div style="display: flex; justify-content: space-between; margin-bottom: 50px; font-size: 15px;">
                <div style="line-height: 1.8;">
                    <span style="color: #888; text-transform: uppercase; font-size: 12px; font-weight: bold;">Customer Details</span><br>
                    <b style="font-size: 18px;">{user_display}</b><br>
                    {user_email}<br>
                    +234 XXX XXX XXXX
                </div>
                <div style="text-align: right; line-height: 1.8;">
                    <span style="color: #888; text-transform: uppercase; font-size: 12px; font-weight: bold;">Invoice Information</span><br>
                    <b>REF:</b> {invoice_ref}<br>
                    <b>DATE:</b> {invoice_date}
                </div>
            </div>

            <!-- Main Items Table -->
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 0px;">
                <thead>
                    <tr style="background-color: {COLOR_NAVY}; color: white; text-transform: uppercase; font-size: 13px; letter-spacing: 1px;">
                        <th style="padding: 15px; text-align: left;">Report Groups</th>
                        <th style="padding: 15px; text-align: center; width: 60px;">Qty</th>
                        <th style="padding: 15px; text-align: right; width: 150px;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <!-- The Large Total Bar -->
            <div style="background-color: {COLOR_TOTAL_BAR}; color: white; display: flex; justify-content: space-between; align-items: center; padding: 25px 40px; margin-top: 0px;">
                <span style="font-size: 30px; font-weight: 800; letter-spacing: 2px;">TOTAL</span>
                <span style="font-size: 35px; font-weight: 800;">₦{total_price:,.2f}</span>
            </div>

            <!-- Status -->
            <div style="margin-top: 30px; font-size: 16px;">
                <b>STATUS:</b> &nbsp;&nbsp;&nbsp; 
                <span style="color: {'#16a34a' if 'PAID' in status_label.upper() else '#dc2626'}; font-weight: bold; background: {'#dcfce7' if 'PAID' in status_label.upper() else '#fee2e2'}; padding: 5px 15px; border-radius: 5px;">
                    {status_label.upper()}
                </span>
            </div>

            <!-- Description -->
            <div style="margin-top: 40px; border-top: 1px solid #eee; padding-top: 20px;">
                <b style="font-size: 14px; text-transform: uppercase; color: #888;">Description:</b>
                <p style="color: #555; font-size: 14px; line-height: 1.7; margin-top: 10px;">
                    This invoice covers the professional data analysis and reporting services provided by the Edustat Platform. 
                    The reports generated include deep-dive analytics into student performance and demographic trends for {invoice_ref}.
                </p>
            </div>
        </div>
    </div>
    """
    return html


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

     # ── Remove report option ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**📋 Reports in this Invoice**")
    for r_idx, r_item in enumerate(report_cart):
        r_col1, r_col2 = st.columns([5, 1])
        with r_col1:
            st.markdown(
                f"**{r_idx + 1}.** {r_item.get('analysis', '—')} — "
                f"₦{r_item.get('price', 0):,} "
                f"({r_item.get('record_count', 0):,} records)"
            )
        with r_col2:
            if st.button("🗑 Remove", key=f"remove_report_{r_idx}"):
                st.session_state.report_cart.pop(r_idx)
                st.session_state.invoice_ref = None
                st.rerun()
                
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
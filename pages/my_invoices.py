import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from db_queries import fetch_data
from invoice_pdf import generate_invoice_pdf

if not st.session_state.get("logged_in", False):
    st.warning("⚠️ Please sign in to view your invoices.")
    st.stop()

st.set_page_config(page_title="My Invoices", layout="wide")

# ============================================================
# HEADER
# ============================================================
st.title("My Invoice")
st.caption("Access and manage your invoices")

user_email = st.session_state.get("user_email")
user_id = st.session_state.get("user_id", 0)

# ============================================================
# FETCH USER INVOICES
# ============================================================
try:
    query = f"""
        SELECT 
            ref,
            invoice_data,
            total,
            data,
            created_at
        FROM invoices 
        WHERE user_id = {user_id}
        ORDER BY created_at DESC
    """
    invoices_df = fetch_data(query)
except Exception as e:
    st.error(f"❌ Error loading invoices: {str(e)}")
    st.stop()

# ============================================================
# CHECK IF USER HAS INVOICES
# ============================================================
if invoices_df.empty:
    st.info("📭 You have no invoices yet. Create your first report!")
    if st.button("➕ Create Report"):
        st.switch_page("pages/create_report.py")
    st.stop()

# ============================================================
# PROCESS INVOICE DATA
# ============================================================
invoices_df['created_at'] = pd.to_datetime(invoices_df['created_at'])
invoices_df['expiry_date'] = invoices_df['created_at'] + timedelta(days=30)
invoices_df['days_left'] = (invoices_df['expiry_date'] - datetime.now()).dt.days

# Extract status from invoice_data JSON
def get_status(invoice_data):
    try:
        data_dict = json.loads(invoice_data) if isinstance(invoice_data, str) else invoice_data
        return data_dict.get('status', 'PENDING')
    except:
        return 'PENDING'

# Extract report type from data JSON
def get_report_type(data):
    try:
        data_dict = json.loads(data) if isinstance(data, str) else data
        return data_dict.get('report_group', 'General Report')
    except:
        return 'N/A'

invoices_df['status'] = invoices_df['invoice_data'].apply(get_status)
invoices_df['report_type'] = invoices_df['data'].apply(get_report_type)

# ============================================================
# STYLED TABLE WITH INLINE ACTIONS
# ============================================================
st.markdown("---")
st.subheader("All Invoices")

# Create column headers
col_headers = st.columns([1.5, 2.5, 1.5, 1.5, 1.5, 1.5])
col_headers[0].markdown("**Invoice ID**")
col_headers[1].markdown("**Report Type**")
col_headers[2].markdown("**Date**")
col_headers[3].markdown("**Amount**")
col_headers[4].markdown("**Expiry Date**")
col_headers[5].markdown("**Action**")

st.markdown("---")

# ============================================================
# DISPLAY EACH INVOICE AS A ROW
# ============================================================
for idx, row in invoices_df.iterrows():
    ref = row['ref']
    status = row['status']
    report_type = row['report_type']
    created_date = row['created_at'].strftime('%d/%m/%Y')
    amount = row['total']
    days_left = row['days_left']
    
    # Format expiry
    if days_left > 0:
        expiry_text = f"{days_left} days left"
        expiry_color = "#28a745" if days_left > 7 else "#ffc107"
    else:
        expiry_text = "Expired"
        expiry_color = "#dc3545"
    
    # Create row columns
    cols = st.columns([1.5, 2.5, 1.5, 1.5, 1.5, 1.5])
    
    # Invoice ID
    cols[0].markdown(f"**{ref}**")
    
    # Report Type
    cols[1].markdown(report_type)
    
    # Date
    cols[2].markdown(created_date)
    
    # Amount
    cols[3].markdown(f"₦{amount:,.0f}")
    
    # Expiry Date with color
    cols[4].markdown(f"<span style='color:{expiry_color};font-weight:bold;'>{expiry_text}</span>", unsafe_allow_html=True)
    
    # Action Buttons (Icons)
    with cols[5]:
        action_cols = st.columns([1, 1, 1])
        
        # 👁️ View Details
        with action_cols[0]:
            if st.button("👁️", key=f"view_{ref}", help="View Details"):
                st.session_state[f"show_details_{ref}"] = True
        
        # 📥 Download PDF
        with action_cols[1]:
            try:
                pdf_path = generate_invoice_pdf(
                    invoice_ref=ref,
                    user_email=user_email,
                    amount=amount,
                    description=f"Custom Report - {report_type}",
                    selected_group=report_type,
                    selected_columns=[],
                    status=status,
                )
                
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        "📥",
                        pdf_file,
                        file_name=f"Invoice_{ref}.pdf",
                        mime="application/pdf",
                        key=f"download_{ref}",
                        help="Download PDF"
                    )
            except:
                st.markdown("📥", help="PDF unavailable")
        
        # 🗑️ Delete (or alternate action based on status)
        with action_cols[2]:
            if status == 'PENDING':
                if st.button("💳", key=f"pay_{ref}", help="Continue to Payment", type="primary"):
                    st.session_state.invoice_ref = ref
                    st.session_state.pending_invoice_saved = True
                    
                    try:
                        data_dict = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
                        st.session_state.saved_group = data_dict.get('report_group')
                        st.session_state.saved_filters = data_dict.get('filters', {})
                        st.session_state.saved_charts = data_dict.get('charts', [])
                    except:
                        pass
                    
                    st.switch_page("pages/create_report.py")
            
            elif status == 'PAID':
                if st.button("📊", key=f"report_{ref}", help="View Report", type="primary"):
                    st.session_state.invoice_ref = ref
                    st.session_state.payment_verified = True
                    st.session_state.report_ready = True
                    
                    try:
                        data_dict = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
                        st.session_state.saved_group = data_dict.get('report_group')
                        st.session_state.saved_filters = data_dict.get('filters', {})
                        st.session_state.saved_charts = data_dict.get('charts', [])
                    except:
                        pass
                    
                    st.switch_page("pages/view_report.py")
    
    # Show details popup if clicked
    if st.session_state.get(f"show_details_{ref}", False):
        with st.expander(f"📄 Details for {ref}", expanded=True):
            st.json({
                "Invoice ID": ref,
                "Report Type": report_type,
                "Amount": f"₦{amount:,.2f}",
                "Status": status,
                "Created": created_date,
                "Days Left": days_left
            })
            
            if st.button("✖️ Close", key=f"close_{ref}"):
                st.session_state[f"show_details_{ref}"] = False
                st.rerun()
    
    st.markdown("---")

# ============================================================
# NAVIGATION
# ============================================================
st.markdown("")
if st.button("➕ Create New Report", type="primary"):
    st.switch_page("pages/create_report.py")
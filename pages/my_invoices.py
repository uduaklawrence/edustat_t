import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from db_queries import fetch_data, delete_invoice

st.set_page_config(page_title="My Invoices", layout="wide")

# Load your existing CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Additional CSS for the invoices table
st.markdown("""
<style>
    .invoices-container {
        background: var(--card-white);
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid var(--border-light);
    }
    
    .invoices-header {
        margin-bottom: 32px;
    }
    
    .invoices-title {
        font-size: 32px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 8px;
    }
    
    .invoices-subtitle {
        font-size: 16px;
        color: var(--text-secondary);
    }
    
    .invoices-table-header {
        background-color: var(--background-gray);
        padding: 16px;
        font-weight: 600;
        color: var(--text-secondary);
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 2px solid var(--border-light);
    }
    
    .invoices-table-row {
        padding: 16px;
        border-bottom: 1px solid var(--border-light);
        transition: background-color 0.2s;
    }
    
    .invoices-table-row:hover {
        background-color: var(--background-gray);
    }
    
    .invoice-id {
        font-family: monospace;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    
    .status-paid {
        background-color: #d1fae5;
        color: #065f46;
    }
    
    .status-pending {
        background-color: #fef3c7;
        color: #92400e;
    }
    
    /* Action buttons */
    div[data-testid="stButton"] button.action-btn {
        background: transparent !important;
        border: 1px solid var(--border-light) !important;
        padding: 8px 12px !important;
        border-radius: 6px !important;
        color: var(--text-secondary) !important;
        font-size: 18px !important;
        transition: all 0.2s ease !important;
        min-width: 40px !important;
        height: 40px !important;
    }
    
    div[data-testid="stButton"] button.action-btn:hover {
        background: var(--background-gray) !important;
        border-color: var(--primary-blue) !important;
        color: var(--primary-blue) !important;
    }
    
    div[data-testid="stButton"] button.action-btn-delete:hover {
        border-color: #dc2626 !important;
        color: #dc2626 !important;
    }
    
    div[data-testid="stButton"] button.action-btn-primary {
        background: var(--primary-navy) !important;
        border: none !important;
        padding: 8px 12px !important;
        border-radius: 6px !important;
        color: white !important;
        font-size: 18px !important;
        min-width: 40px !important;
        height: 40px !important;
    }
    
    div[data-testid="stButton"] button.action-btn-primary:hover {
        background: var(--primary-blue) !important;
    }
    
    /* Search input */
    .stTextInput input {
        border-radius: 8px !important;
        border: 2px solid var(--border-light) !important;
        padding: 12px 16px !important;
        font-size: 15px !important;
    }
    
    .stTextInput input:focus {
        border-color: var(--primary-blue) !important;
    }
    
    .stSelectbox select {
        border-radius: 8px !important;
        border: 2px solid var(--border-light) !important;
        padding: 12px 16px !important;
    }
</style>
""", unsafe_allow_html=True)

# Check authentication
if not st.session_state.get("logged_in", False):
    st.warning("⚠️ Please sign in to view your invoices.")
    st.stop()

# Page header
st.markdown("""
<div class="invoices-header">
    <div class="invoices-title">My Invoices</div>
    <div class="invoices-subtitle">Access and manage your invoices</div>
</div>
""", unsafe_allow_html=True)

user_email = st.session_state.get("user_email")
user_id = st.session_state.get("user_id", 0)

# Fetch user invoices
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

# Check if user has invoices
if invoices_df.empty:
    st.info("📭 You have no invoices yet. Create your first report!")
    if st.button("➕ Create Report"):
        st.switch_page("pages/create_report.py")
    st.stop()

# Process invoice data
invoices_df['created_at'] = pd.to_datetime(invoices_df['created_at'])

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

# Search and filter section
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input("", placeholder="🔍 Search invoices...", label_visibility="collapsed")

with col2:
    status_options = ["All Status", "paid", "PENDING"]
    selected_status = st.selectbox("", status_options, label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

# Filter invoices
filtered_invoices = invoices_df.copy()

if search_query:
    filtered_invoices = filtered_invoices[
        filtered_invoices["ref"].str.contains(search_query, case=False, na=False) |
        filtered_invoices["report_type"].str.contains(search_query, case=False, na=False)
    ]

if selected_status != "All Status":
    filtered_invoices = filtered_invoices[filtered_invoices["status"] == selected_status]

# Create table
st.markdown('<div class="invoices-container">', unsafe_allow_html=True)

# Table header
header_cols = st.columns([1.5, 2.5, 1.5, 1.5, 1.5])
headers = ["Invoice ID", "Report Type", "Date", "Amount", "Actions"]

for col, header in zip(header_cols, headers):
    with col:
        st.markdown(f'<div class="invoices-table-header">{header}</div>', unsafe_allow_html=True)

# Data rows
for idx, row in filtered_invoices.iterrows():
    ref = row['ref']
    status = row['status']
    report_type = row['report_type']
    created_date = row['created_at'].strftime('%d/%m/%Y')
    amount = row['total']
    
    row_cols = st.columns([1.5, 2.5, 1.5, 1.5, 1.5])
    
    # Invoice ID with status badge - Clickable
    with row_cols[0]:
        status_class = "status-paid" if status == "PAID" else "status-pending"
        if st.button(f"{ref}", key=f"invoice_id_{ref}", help="Click to view invoice"):
            st.session_state.invoice_ref = ref
            st.session_state.pending_invoice_saved = True
            
            try:
                data_dict = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
                st.session_state.saved_group = data_dict.get('report_group')
                st.session_state.saved_filters = data_dict.get('filters', {})
                st.session_state.saved_charts = data_dict.get('charts', [])
            except:
                pass
            
            if status == 'PENDING':
                st.session_state.payment_verified = False
                st.switch_page("pages/view_invoice.py")
            else:
                st.session_state.payment_verified = True
                st.switch_page("pages/view_invoice.py")
        
        st.markdown(f'<span class="status-badge {status_class}" style="margin-left: 8px;">{status}</span>', unsafe_allow_html=True)
    
    # Report Type - Clickable
    with row_cols[1]:
        if st.button(report_type, key=f"report_type_{ref}", help="Click to view invoice", type="secondary"):
            st.session_state.invoice_ref = ref
            st.session_state.pending_invoice_saved = True
            
            try:
                data_dict = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
                st.session_state.saved_group = data_dict.get('report_group')
                st.session_state.saved_filters = data_dict.get('filters', {})
                st.session_state.saved_charts = data_dict.get('charts', [])
            except:
                pass
            
            if status == 'PENDING':
                st.session_state.payment_verified = False
                st.switch_page("pages/view_invoice.py")
            else:
                st.session_state.payment_verified = True
                st.switch_page("pages/view_invoice.py")
    
    # Date
    with row_cols[2]:
        st.markdown(f'<div style="padding: 16px; color: var(--text-primary);">{created_date}</div>', unsafe_allow_html=True)
    
    # Amount
    with row_cols[3]:
        st.markdown(f'<div style="padding: 16px; color: var(--text-primary); font-weight: 600;">₦{amount:,.0f}</div>', unsafe_allow_html=True)
    
    # Action buttons
    with row_cols[4]:
        action_cols = st.columns(4)
        
        # View Details - Opens full invoice page
        with action_cols[0]:
            if st.button("👁️", key=f"view_{ref}", help="View Invoice Details"):
                st.session_state.invoice_ref = ref
                st.session_state.pending_invoice_saved = True
                
                try:
                    data_dict = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
                    st.session_state.saved_group = data_dict.get('report_group')
                    st.session_state.saved_filters = data_dict.get('filters', {})
                    st.session_state.saved_charts = data_dict.get('charts', [])
                    st.session_state.saved_columns = data_dict.get('columns', [])
                    st.session_state.saved_description = data_dict.get('description', f"Custom Report - {data_dict.get('report_group', 'N/A')}")
                except:
                    st.session_state.saved_columns = []
                    st.session_state.saved_description = f"Custom Report - {report_type}"
                
                # Set payment status based on invoice status
                if status == 'PENDING':
                    st.session_state.payment_verified = False
                else:
                    st.session_state.payment_verified = True
                
                st.switch_page("pages/view_invoice.py")
        
        # Download PDF
        with action_cols[1]:
            try:
                from invoice_pdf import generate_invoice_pdf
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
        
        # Action button based on status
        with action_cols[2]:
            if status == 'PENDING':
                if st.button("💳", key=f"pay_{ref}", help="Continue to Payment"):
                    st.session_state.invoice_ref = ref
                    st.session_state.pending_invoice_saved = True
                    
                    try:
                        data_dict = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
                        st.session_state.saved_group = data_dict.get('report_group')
                        st.session_state.saved_filters = data_dict.get('filters', {})
                        st.session_state.saved_charts = data_dict.get('charts', [])
                    except:
                        pass
                    
                    st.switch_page("pages/view_invoice.py")
            
            elif status == 'PAID':
                if st.button("📊", key=f"report_{ref}", help="View Report"):
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
        
        # Delete button
        with action_cols[3]:
            if st.button("🗑️", key=f"delete_{ref}", help="Delete invoice"):
                if st.session_state.get(f"confirm_delete_{ref}", False):
                    try:
                        # Add your delete function here
                        # delete_invoice(ref)
                        st.success(f"Deleted invoice {ref}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {str(e)}")
                else:
                    st.session_state[f"confirm_delete_{ref}"] = True
                    st.warning("⚠️ Click again to confirm deletion")
    
    # Show details popup if clicked
    if st.session_state.get(f"show_details_{ref}", False):
        with st.expander(f"📄 Details for {ref}", expanded=True):
            st.json({
                "Invoice ID": ref,
                "Report Type": report_type,
                "Amount": f"₦{amount:,.2f}",
                "Status": status,
                "Created": created_date
            })
            
            if st.button("✖️ Close", key=f"close_{ref}"):
                st.session_state[f"show_details_{ref}"] = False
                st.rerun()
    
    st.markdown("<hr style='margin: 0; border: none; border-bottom: 1px solid var(--border-light);'>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Show message if no results
if filtered_invoices.empty:
    st.info("No invoices found matching your search criteria.")

# Navigation
st.markdown("<br>", unsafe_allow_html=True)
if st.button("➕ Create New Report", type="primary"):
    st.switch_page("pages/create_report.py")
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import glob
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="Material Planning Assistant",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .status-ready {
        color: #28a745;
        font-weight: bold;
    }
    .status-partial {
        color: #ffc107;
        font-weight: bold;
    }
    .status-critical {
        color: #dc3545;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data(file_path):
    """Load the Material Study Excel file"""
    try:
        df = pd.read_excel(file_path, sheet_name="Study")
        # Convert date columns
        date_cols = ['availability_date', 'ROH delivery', 'SEC delivery', 'Asn Expected Date', 'Asn Creation Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

def get_latest_study_file():
    """Find the most recent Material Study file"""
    try:
        files = glob.glob("MV_Material_Study-*.xlsx")
        if not files:
            # Also try without the pattern in case the file is named differently
            files = glob.glob("*.xlsx")
            files = [f for f in files if 'Material' in f or 'material' in f or 'Study' in f or 'study' in f]
        if not files:
            return None
        return max(files, key=os.path.getctime)
    except Exception as e:
        return None

def calculate_project_status(df, project):
    """Calculate comprehensive status for a project"""
    proj_data = df[df['SEC order'] == project].copy()
    
    if proj_data.empty:
        return None
    
    total_items = len(proj_data)
    total_req = proj_data['req_qty'].sum()
    total_allocated = proj_data['allocated_qty'].sum()
    total_balance = proj_data['balance'].sum()
    
    # Status categorization
    ready = len(proj_data[proj_data['balance'] == 0])
    partial = len(proj_data[(proj_data['balance'] > 0) & (proj_data['allocated_qty'] > 0)])
    missing = len(proj_data[proj_data['allocated_qty'] == 0])
    
    # Delay analysis
    delayed_items = proj_data[proj_data['delay'] != 0]
    max_delay = delayed_items['delay'].max() if not delayed_items.empty else 0
    
    # Supply type breakdown
    supply_breakdown = proj_data.groupby('supply_type')['allocated_qty'].sum().to_dict()
    
    # Overall status
    if total_balance == 0:
        status = "🟢 Ready"
        status_class = "status-ready"
    elif missing > 0 or max_delay == 'late':
        status = "🔴 Critical"
        status_class = "status-critical"
    else:
        status = "🟡 Partial"
        status_class = "status-partial"
    
    return {
        'status': status,
        'status_class': status_class,
        'total_items': total_items,
        'ready_items': ready,
        'partial_items': partial,
        'missing_items': missing,
        'total_req': total_req,
        'total_allocated': total_allocated,
        'total_balance': total_balance,
        'fulfillment_pct': (total_allocated / total_req * 100) if total_req > 0 else 0,
        'max_delay': max_delay,
        'supply_breakdown': supply_breakdown,
        'sec_delivery': proj_data['SEC delivery'].min(),
        'roh_delivery': proj_data['ROH delivery'].min()
    }

def material_inquiry(df, item_code):
    """Get comprehensive information about a material"""
    item_data = df[df['item'] == item_code].copy()
    
    if item_data.empty:
        return None
    
    total_req = item_data['req_qty'].sum()
    total_allocated = item_data['allocated_qty'].sum()
    total_balance = item_data['balance'].sum()
    
    # Where is it allocated?
    allocation_by_project = item_data.groupby('SEC order').agg({
        'req_qty': 'sum',
        'allocated_qty': 'sum',
        'balance': 'sum'
    }).reset_index()
    
    # Supply sources
    supply_sources = item_data.groupby(['supply_type', 'source']).agg({
        'allocated_qty': 'sum'
    }).reset_index()
    
    # Blocking issues
    blocking_issues = []
    
    qc_items = item_data[item_data['supply_type'] == 'QC']
    if not qc_items.empty:
        blocking_issues.append(f"⚠️ {qc_items['allocated_qty'].sum():.0f} units stuck in QC")
    
    gr_items = item_data[item_data['supply_type'] == 'GR_in_process']
    if not gr_items.empty:
        blocking_issues.append(f"⚠️ {gr_items['allocated_qty'].sum():.0f} units in GR process")
    
    po_late = item_data[(item_data['supply_type'] == 'PO') & (item_data['delay'] == 'late')]
    if not po_late.empty:
        blocking_issues.append(f"🔴 {po_late['allocated_qty'].sum():.0f} units on delayed POs")
    
    pr_items = item_data[item_data['supply_type'] == 'PR']
    if not pr_items.empty:
        blocking_issues.append(f"📝 {pr_items['balance'].sum():.0f} units need PR creation")
    
    return {
        'description': item_data['description'].iloc[0],
        'total_req': total_req,
        'total_allocated': total_allocated,
        'total_balance': total_balance,
        'allocation_by_project': allocation_by_project,
        'supply_sources': supply_sources,
        'blocking_issues': blocking_issues,
        'item_data': item_data
    }

def supplier_performance(df):
    """Analyze supplier performance and delays"""
    supplier_data = df[df['supplier'].notna()].copy()
    
    if supplier_data.empty:
        return None
    
    # Calculate delays by supplier
    delayed = supplier_data[supplier_data['delay'] != 0].copy()
    
    supplier_stats = delayed.groupby('supplier').agg({
        'delay': ['count', 'mean', 'max'],
        'allocated_qty': 'sum'
    }).reset_index()
    
    supplier_stats.columns = ['supplier', 'delayed_items', 'avg_delay_days', 'max_delay_days', 'total_qty_delayed']
    supplier_stats = supplier_stats.sort_values('avg_delay_days', ascending=False)
    
    return supplier_stats

def production_readiness(df):
    """Identify projects ready for production"""
    projects = df['SEC order'].unique()
    
    readiness_list = []
    
    for project in projects:
        status_info = calculate_project_status(df, project)
        if status_info:
            readiness_list.append({
                'Project': project,
                'Status': status_info['status'],
                'Fulfillment %': status_info['fulfillment_pct'],
                'Missing Items': status_info['missing_items'],
                'Max Delay': status_info['max_delay'],
                'SEC Delivery': status_info['sec_delivery']
            })
    
    readiness_df = pd.DataFrame(readiness_list)
    readiness_df = readiness_df.sort_values('Fulfillment %', ascending=False)
    
    return readiness_df

# Main App
def main():
    st.markdown('<p class="main-header">📦 Material Planning Assistant</p>', unsafe_allow_html=True)
    
    # File upload or auto-detect
    st.sidebar.header("Data Source")
    
    latest_file = get_latest_study_file()
    
    if latest_file:
        st.sidebar.success(f"📄 Auto-detected: {os.path.basename(latest_file)}")
        use_latest = st.sidebar.checkbox("Use this file", value=True, key="use_auto_file")
        if use_latest:
            uploaded_file = latest_file
        else:
            uploaded_file = st.sidebar.file_uploader("Upload a different file", type=['xlsx'], key="manual_upload")
    else:
        st.sidebar.warning("⚠️ No Material Study file found in directory")
        # Show available files for debugging
        all_xlsx = glob.glob("*.xlsx")
        if all_xlsx:
            st.sidebar.info(f"Available Excel files: {', '.join([os.path.basename(f) for f in all_xlsx])}")
        uploaded_file = st.sidebar.file_uploader("Upload Material Study", type=['xlsx'], key="file_upload")
    
    if uploaded_file is None:
        st.info("👈 Please upload a Material Study file from the sidebar")
        st.markdown("""
        ### Welcome to Material Planning Assistant! 
        
        This tool helps you answer questions like:
        - ✅ Do we have enough stock for Project X?
        - 🔍 Why can't we issue material Y to production?
        - 📊 What's the material availability for Project Z?
        - 🚚 Which suppliers are delaying materials?
        - ⚠️ What are my critical projects?
        - 🏭 Which projects can I push to production now?
        
        **Get started by uploading your Material Study Excel file using the sidebar!**
        
        ### 📋 Expected File Format:
        - Excel file (.xlsx)
        - Should contain a sheet named "Study"
        - Recommended filename: `MV_Material_Study-*.xlsx`
        """)
        return
    
    # Load data
    df = load_data(uploaded_file)
    
    if df is None:
        st.error("Failed to load data. Please check the file format.")
        return
    
    # Sidebar navigation
    st.sidebar.header("Navigation")
    page = st.sidebar.radio(
        "Select View",
        ["🏠 Dashboard Overview", "📊 Project Health", "🔍 Material Inquiry", 
         "🚚 Supplier Performance", "⚠️ Critical Projects", "✅ Production Readiness",
         "🏭 Push to Production"]
    )
    
    # Page routing
    if page == "🏠 Dashboard Overview":
        show_dashboard_overview(df)
    elif page == "📊 Project Health":
        show_project_health(df)
    elif page == "🔍 Material Inquiry":
        show_material_inquiry(df)
    elif page == "🚚 Supplier Performance":
        show_supplier_performance(df)
    elif page == "⚠️ Critical Projects":
        show_critical_projects(df)
    elif page == "✅ Production Readiness":
        show_production_readiness(df)
    elif page == "🏭 Push to Production":
        show_push_to_production(df)

def show_dashboard_overview(df):
    st.header("Dashboard Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_projects = df['SEC order'].nunique()
    total_items = len(df)
    total_req = df['req_qty'].sum()
    total_allocated = df['allocated_qty'].sum()
    overall_fulfillment = (total_allocated / total_req * 100) if total_req > 0 else 0
    
    col1.metric("Total Projects", total_projects)
    col2.metric("Total Line Items", total_items)
    col3.metric("Overall Fulfillment", f"{overall_fulfillment:.1f}%")
    col4.metric("Total Balance", f"{df['balance'].sum():.0f} units")
    
    st.markdown("---")
    
    # Quick Stats
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Supply Type Distribution")
        supply_dist = df.groupby('supply_type')['allocated_qty'].sum().reset_index()
        fig = px.pie(supply_dist, values='allocated_qty', names='supply_type', 
                     title="Material Allocation by Source")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Project Status Summary")
        projects = df['SEC order'].unique()
        status_counts = {'Ready': 0, 'Partial': 0, 'Critical': 0}
        
        for project in projects:
            status_info = calculate_project_status(df, project)
            if status_info:
                if '🟢' in status_info['status']:
                    status_counts['Ready'] += 1
                elif '🟡' in status_info['status']:
                    status_counts['Partial'] += 1
                else:
                    status_counts['Critical'] += 1
        
        fig = go.Figure(data=[go.Bar(
            x=list(status_counts.keys()),
            y=list(status_counts.values()),
            marker_color=['#28a745', '#ffc107', '#dc3545']
        )])
        fig.update_layout(title="Projects by Status", xaxis_title="Status", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent delays
    st.subheader("⚠️ Items with Delays")
    delayed = df[df['delay'] != 0].copy()
    if not delayed.empty:
        delayed_display = delayed[['SEC order', 'item', 'description', 'delay', 'supplier', 'availability_date']].head(10)
        st.dataframe(delayed_display, width="stretch")
    else:
        st.success("No delayed items!")

def show_project_health(df):
    st.header("📊 Project Health Monitor")
    
    projects = sorted(df['SEC order'].unique())
    selected_project = st.selectbox("Select Project", projects)
    
    if selected_project:
        status_info = calculate_project_status(df, selected_project)
        
        if status_info:
            # Status header
            st.markdown(f"## {selected_project}")
            st.markdown(f'<p class="{status_info["status_class"]}" style="font-size: 1.5rem;">{status_info["status"]}</p>', 
                       unsafe_allow_html=True)
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Fulfillment", f"{status_info['fulfillment_pct']:.1f}%")
            col2.metric("Total Items", status_info['total_items'])
            col3.metric("Missing Items", status_info['missing_items'])
            col4.metric("Max Delay", f"{status_info['max_delay']} days" if isinstance(status_info['max_delay'], (int, float)) else status_info['max_delay'])
            
            st.markdown("---")
            
            # Progress bars
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Item Status Breakdown")
                st.write(f"✅ Ready: {status_info['ready_items']}")
                st.write(f"🟡 Partial: {status_info['partial_items']}")
                st.write(f"🔴 Missing: {status_info['missing_items']}")
            
            with col2:
                st.subheader("Key Dates")
                st.write(f"📅 SEC Delivery: {status_info['sec_delivery'].strftime('%Y-%m-%d') if pd.notna(status_info['sec_delivery']) else 'N/A'}")
                st.write(f"📦 ROH Required: {status_info['roh_delivery'].strftime('%Y-%m-%d') if pd.notna(status_info['roh_delivery']) else 'N/A'}")
            
            # Detailed breakdown
            st.subheader("Material Details")
            proj_data = df[df['SEC order'] == selected_project]
            
            # Add status column
            def get_item_status(row):
                if row['balance'] == 0:
                    return "✅ Ready"
                elif row['allocated_qty'] == 0:
                    return "🔴 Missing"
                else:
                    return "🟡 Partial"
            
            proj_data_display = proj_data.copy()
            proj_data_display['Status'] = proj_data_display.apply(get_item_status, axis=1)
            
            display_cols = ['Status', 'item', 'description', 'req_qty', 'allocated_qty', 'balance', 
                          'supply_type', 'source', 'availability_date', 'delay']
            
            st.dataframe(proj_data_display[display_cols], width="stretch", height=400)
            
            # Blocking issues
            blocking = []
            if status_info['missing_items'] > 0:
                blocking.append(f"🔴 {status_info['missing_items']} items completely missing")
            
            qc_items = proj_data[proj_data['supply_type'] == 'QC']
            if not qc_items.empty:
                blocking.append(f"⚠️ {len(qc_items)} items stuck in QC")
            
            gr_items = proj_data[proj_data['supply_type'] == 'GR_in_process']
            if not gr_items.empty:
                blocking.append(f"⚠️ {len(gr_items)} items in GR process")
            
            if blocking:
                st.subheader("🚫 Blocking Issues")
                for issue in blocking:
                    st.warning(issue)

def show_material_inquiry(df):
    st.header("🔍 Material Inquiry")
    
    st.markdown("Search for any material to see its complete status across all projects")
    
    # Search box
    all_items = sorted(df['item'].unique())
    selected_item = st.selectbox("Enter or select item code", all_items)
    
    if selected_item:
        info = material_inquiry(df, selected_item)
        
        if info:
            st.markdown(f"## {selected_item}")
            st.markdown(f"**Description:** {info['description']}")
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Required", f"{info['total_req']:.0f}")
            col2.metric("Total Allocated", f"{info['total_allocated']:.0f}")
            col3.metric("Balance", f"{info['total_balance']:.0f}")
            
            st.markdown("---")
            
            # Blocking issues
            if info['blocking_issues']:
                st.subheader("🚫 Why Can't We Issue?")
                for issue in info['blocking_issues']:
                    st.error(issue)
            else:
                st.success("✅ No blocking issues - material is available!")
            
            st.markdown("---")
            
            # Allocation by project
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Allocation by Project")
                st.dataframe(info['allocation_by_project'], width="stretch")
            
            with col2:
                st.subheader("Supply Sources")
                st.dataframe(info['supply_sources'], width="stretch")
            
            # Full details
            st.subheader("Complete Details")
            display_cols = ['SEC order', 'SEC Number', 'req_qty', 'allocated_qty', 'balance', 
                          'supply_type', 'source', 'locater', 'availability_date', 'delay', 'supplier']
            available_cols = [col for col in display_cols if col in info['item_data'].columns]
            st.dataframe(info['item_data'][available_cols], width="stretch", height=400)

def show_supplier_performance(df):
    st.header("🚚 Supplier Performance Analysis")
    
    supplier_stats = supplier_performance(df)
    
    if supplier_stats is not None and not supplier_stats.empty:
        st.subheader("Supplier Delay Rankings")
        st.markdown("**Suppliers sorted by average delay (worst first)**")
        
        # Display table
        st.dataframe(supplier_stats, width="stretch")
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(supplier_stats.head(10), x='supplier', y='avg_delay_days',
                        title="Top 10 Suppliers by Average Delay",
                        labels={'avg_delay_days': 'Average Delay (days)', 'supplier': 'Supplier'})
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(supplier_stats.head(10), x='supplier', y='delayed_items',
                        title="Top 10 Suppliers by Number of Delayed Items",
                        labels={'delayed_items': 'Delayed Items', 'supplier': 'Supplier'})
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed delayed items
        st.subheader("Delayed Items by Supplier")
        selected_supplier = st.selectbox("Select Supplier", supplier_stats['supplier'].tolist())
        
        if selected_supplier:
            supplier_items = df[(df['supplier'] == selected_supplier) & (df['delay'] != 0)]
            display_cols = ['SEC order', 'item', 'description', 'allocated_qty', 'delay', 
                          'availability_date', 'ROH delivery', 'locater']
            available_cols = [col for col in display_cols if col in supplier_items.columns]
            st.dataframe(supplier_items[available_cols], width="stretch", height=400)
    else:
        st.info("No supplier delay data available")

def show_critical_projects(df):
    st.header("⚠️ Critical Projects")
    
    st.markdown("Projects sorted by criticality (missing items, delays, and urgency)")
    
    projects = df['SEC order'].unique()
    critical_list = []
    
    for project in projects:
        status_info = calculate_project_status(df, project)
        if status_info and '🔴' in status_info['status']:
            days_to_delivery = (status_info['sec_delivery'] - pd.Timestamp.now()).days if pd.notna(status_info['sec_delivery']) else 999
            
            critical_list.append({
                'Project': project,
                'Status': status_info['status'],
                'Fulfillment %': status_info['fulfillment_pct'],
                'Missing Items': status_info['missing_items'],
                'Max Delay': status_info['max_delay'],
                'Days to SEC Delivery': days_to_delivery,
                'SEC Delivery': status_info['sec_delivery']
            })
    
    if critical_list:
        critical_df = pd.DataFrame(critical_list)
        critical_df = critical_df.sort_values(['Days to SEC Delivery', 'Missing Items'], ascending=[True, False])
        
        st.dataframe(critical_df, width="stretch")
        
        # Select project for details
        st.markdown("---")
        st.subheader("Project Deep Dive")
        selected = st.selectbox("Select project for details", critical_df['Project'].tolist())
        
        if selected:
            proj_data = df[df['SEC order'] == selected]
            
            # Show missing/delayed items
            problem_items = proj_data[(proj_data['balance'] > 0) | (proj_data['delay'] != 0)]
            
            st.markdown(f"### Problem Items for {selected}")
            display_cols = ['item', 'description', 'req_qty', 'allocated_qty', 'balance', 
                          'supply_type', 'delay', 'availability_date', 'supplier']
            available_cols = [col for col in display_cols if col in problem_items.columns]
            st.dataframe(problem_items[available_cols], width="stretch", height=400)
    else:
        st.success("🎉 No critical projects! Everything is on track.")

def show_production_readiness(df):
    st.header("✅ Production Readiness Check")
    
    st.markdown("Shows which projects have 100% material ready and can be pushed to production")
    
    readiness_df = production_readiness(df)
    
    if readiness_df is not None and not readiness_df.empty:
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            min_fulfillment = st.slider("Minimum Fulfillment %", 0, 100, 100)
        with col2:
            show_only_ready = st.checkbox("Show only 100% ready", value=True)
        
        if show_only_ready:
            filtered_df = readiness_df[readiness_df['Fulfillment %'] == 100]
        else:
            filtered_df = readiness_df[readiness_df['Fulfillment %'] >= min_fulfillment]
        
        st.subheader(f"Projects Ready for Production: {len(filtered_df[filtered_df['Fulfillment %'] == 100])}")
        
        # Color code the dataframe
        def color_fulfillment(val):
            if val == 100:
                return 'background-color: #d4edda'
            elif val >= 90:
                return 'background-color: #fff3cd'
            else:
                return 'background-color: #f8d7da'
        
        styled_df = filtered_df.style.applymap(color_fulfillment, subset=['Fulfillment %'])
        st.dataframe(styled_df, width="stretch", height=500)
        
        # Quick actions
        if len(filtered_df[filtered_df['Fulfillment %'] == 100]) > 0:
            st.success(f"✅ {len(filtered_df[filtered_df['Fulfillment %'] == 100])} projects ready to start production!")
            
            ready_projects = filtered_df[filtered_df['Fulfillment %'] == 100]['Project'].tolist()
            st.markdown("**Ready Projects:**")
            for proj in ready_projects:
                st.markdown(f"- {proj}")

def show_push_to_production(df):
    st.header("🏭 Push to Production")
    
    st.markdown("""
    **Action-oriented view for production planners**  
    Get actionable lists of materials to clear bottlenecks before production start.
    """)
    
    # Filter options at the top
    st.subheader("🔍 Select Project(s)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_type = st.radio("Filter by:", ["SEC Order", "SEC Number", "Product"])
    
    with col2:
        if filter_type == "SEC Order":
            options = sorted(df['SEC order'].unique())
            selected = st.multiselect("Select SEC Order(s)", options, default=[options[0]] if options else [])
            filtered_df = df[df['SEC order'].isin(selected)].copy() if selected else pd.DataFrame()
        elif filter_type == "SEC Number":
            options = sorted(df['SEC Number'].unique())
            selected = st.multiselect("Select SEC Number(s)", options, default=[options[0]] if options else [])
            filtered_df = df[df['SEC Number'].isin(selected)].copy() if selected else pd.DataFrame()
        else:  # Product
            options = sorted(df['product'].dropna().unique())
            selected = st.multiselect("Select Product(s)", options, default=[options[0]] if options else [])
            filtered_df = df[df['product'].isin(selected)].copy() if selected else pd.DataFrame()
    
    with col3:
        st.metric("Total Items", len(filtered_df) if not filtered_df.empty else 0)
        if not filtered_df.empty and filtered_df['req_qty'].sum() > 0:
            fulfillment = (filtered_df['allocated_qty'].sum() / filtered_df['req_qty'].sum() * 100)
            st.metric("Fulfillment", f"{fulfillment:.1f}%")
        else:
            st.metric("Fulfillment", "N/A")
    
    # Create file name suffix from selections
    if selected:
        if len(selected) == 1:
            file_suffix = selected[0]
        elif len(selected) <= 3:
            file_suffix = "_".join(selected)
        else:
            file_suffix = f"{len(selected)}_items"
    else:
        file_suffix = "export"
    
    if filtered_df.empty or not selected:
        st.info("ℹ️ Please select at least one item from the filter above to view the production action plan.")
        return
    
    st.markdown("---")
    
    # === 1. Materials Stopped at QC ===
    st.subheader("⚠️ Materials Stopped at QC")
    st.markdown("*These materials are delivered but awaiting quality approval*")
    
    qc_items = filtered_df[filtered_df['supply_type'] == 'QC'].copy()
    
    if not qc_items.empty:
        st.error(f"🚫 **{len(qc_items)} items stuck in QC - Priority action required!**")
        
        qc_display = qc_items[['item', 'description', 'allocated_qty', 'locater', 'supplier', 'availability_date']].copy()
        qc_display.columns = ['Item Code', 'Description', 'Qty in QC', 'PO-Line', 'Supplier', 'Received Date']
        st.dataframe(qc_display, width="stretch", height=300)
        
        # Action button
        buffer = BytesIO()
        qc_display.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        
        st.download_button(
            label="📋 Export QC Items to Excel",
            data=buffer,
            file_name=f"QC_Items_{file_suffix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_qc"
        )
    else:
        st.success("✅ No items stuck in QC")
    
    st.markdown("---")
    
    # === 2. Materials Pending GR (Goods Receipt) ===
    st.subheader("📦 Materials Pending GR (Goods Receipt)")
    st.markdown("*These materials are received but not yet in system inventory*")
    
    gr_items = filtered_df[filtered_df['supply_type'] == 'GR_in_process'].copy()
    
    if not gr_items.empty:
        st.warning(f"⏳ **{len(gr_items)} items pending GR processing**")
        
        gr_display = gr_items[['item', 'description', 'allocated_qty', 'locater', 'supplier', 'availability_date']].copy()
        gr_display.columns = ['Item Code', 'Description', 'Qty Pending GR', 'PO-Line', 'Supplier', 'Receipt Date']
        st.dataframe(gr_display, width="stretch", height=300)
        
        # Action button
        buffer = BytesIO()
        gr_display.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        
        st.download_button(
            label="📋 Export GR Items to Excel",
            data=buffer,
            file_name=f"GR_Pending_{file_suffix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_gr"
        )
    else:
        st.success("✅ No items pending GR")
    
    st.markdown("---")
    
    # === 3. Materials in WIP (Work in Progress) ===
    st.subheader("🔧 Materials Available in WIP")
    st.markdown("*Materials under locater 1-1-1-1 - available in production, ready to issue*")
    
    wip_items = filtered_df[filtered_df['locater'] == '1-1-1-1'].copy()
    
    if not wip_items.empty:
        st.info(f"🔧 **{len(wip_items)} items available in WIP - Please issue from production**")
        
        wip_display = wip_items[['item', 'description', 'allocated_qty', 'source', 'locater']].copy()
        wip_display.columns = ['Item Code', 'Description', 'Available Qty', 'Source Job', 'Locater']
        st.dataframe(wip_display, width="stretch", height=300)
        
        # Action button
        buffer = BytesIO()
        wip_display.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        
        st.download_button(
            label="📋 Export WIP Items to Excel",
            data=buffer,
            file_name=f"WIP_Materials_{file_suffix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_wip"
        )
    else:
        st.info("ℹ️ No items in WIP locater")
    
    st.markdown("---")
    
    # === 4. Materials to Allocate (from Other Jobs) ===
    st.subheader("🔄 Materials to Allocate from Other Jobs")
    st.markdown("*On-hand inventory allocated to other projects - requires reallocation approval*")
    
    # Materials that are:
    # - On-hand (inventory type)
    # - Not free stock
    # - Source job is NOT the same as the requirement (SEC order)
    
    allocate_items = filtered_df[
        (filtered_df['supply_type'] == 'inventory') &
        (filtered_df['source'] != 'free_stock') &
        (~filtered_df['source'].isin(selected if selected else []))
    ].copy()
    
    if not allocate_items.empty:
        st.warning(f"🔄 **{len(allocate_items)} items need reallocation from other jobs**")
        
        # Use only columns that exist in the dataframe
        base_cols = ['item', 'description', 'allocated_qty', 'SEC order', 'source', 'locater']
        display_cols = [col for col in base_cols if col in allocate_items.columns]
        
        allocate_display = allocate_items[display_cols].copy()
        
        # Rename columns for better readability
        col_rename = {
            'item': 'Item Code',
            'description': 'Description',
            'allocated_qty': 'Qty to Reallocate',
            'SEC order': 'Project',
            'source': 'Source Project',
            'locater': 'Locater'
        }
        allocate_display.columns = [col_rename.get(col, col) for col in allocate_display.columns]
        
        # Add a column showing if reallocation is easy or needs approval
        if 'Source Project' in allocate_display.columns:
            allocate_display['Action Required'] = allocate_display['Source Project'].apply(
                lambda x: '⚠️ Needs Approval' if x not in ['free_stock', '-'] else '✅ Can Reallocate'
            )
        
        st.dataframe(allocate_display, width="stretch", height=300)
        
        # Action button
        buffer = BytesIO()
        allocate_display.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        
        st.download_button(
            label="📋 Export Reallocation List to Excel",
            data=buffer,
            file_name=f"Reallocation_Needed_{file_suffix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_realloc"
        )
    else:
        st.success("✅ No reallocation needed")
    
    st.markdown("---")
    
    # === 5. Missing Materials (PRs Required) ===
    st.subheader("🚨 Missing Materials - PRs Required")
    st.markdown("*Materials with no allocation - need immediate procurement*")
    
    missing_items = filtered_df[
        (filtered_df['balance'] > 0) & 
        (filtered_df['allocated_qty'] == 0)
    ].copy()
    
    if not missing_items.empty:
        st.error(f"🚨 **{len(missing_items)} items completely missing - Create PRs immediately!**")
        
        missing_display = missing_items[['item', 'description', 'req_qty', 'balance']].copy()
        missing_display.columns = ['Item Code', 'Description', 'Required Qty', 'Missing Qty']
        st.dataframe(missing_display, width="stretch", height=300)
        
        # Action button
        buffer = BytesIO()
        missing_display.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        
        st.download_button(
            label="📋 Export Missing Items to Excel",
            data=buffer,
            file_name=f"Missing_Materials_{file_suffix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_missing"
        )
    else:
        st.success("✅ No missing materials")
    
    st.markdown("---")
    
    # === Summary Action Panel ===
    st.subheader("📊 Action Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.metric("QC Items", len(qc_items) if not qc_items.empty else 0)
    col2.metric("GR Pending", len(gr_items) if not gr_items.empty else 0)
    col3.metric("WIP Items", len(wip_items) if not wip_items.empty else 0)
    col4.metric("To Reallocate", len(allocate_items) if not allocate_items.empty else 0)
    col5.metric("Missing", len(missing_items) if not missing_items.empty else 0)
    
    # Overall readiness assessment
    total_blocking = len(qc_items) + len(gr_items) + len(missing_items)
    
    st.markdown("---")
    
    if total_blocking == 0 and fulfillment >= 100:
        st.success("🎉 **ALL CLEAR! This project is ready to push to production!**")
    elif total_blocking <= 3 and fulfillment >= 90:
        st.warning(f"⚠️ **ALMOST READY**: Clear {total_blocking} blocking items to proceed")
    else:
        st.error(f"🚫 **NOT READY**: {total_blocking} critical blockers need resolution")
    
    # Master export button
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        if not qc_items.empty:
            qc_display.to_excel(writer, sheet_name="QC Items", index=False)
        if not gr_items.empty:
            gr_display.to_excel(writer, sheet_name="GR Pending", index=False)
        if not wip_items.empty:
            wip_display.to_excel(writer, sheet_name="WIP Materials", index=False)
        if not allocate_items.empty:
            allocate_display.to_excel(writer, sheet_name="Reallocation Needed", index=False)
        if not missing_items.empty:
            missing_display.to_excel(writer, sheet_name="Missing Materials", index=False)
        
        # Summary sheet
        summary_data = {
            'Category': ['QC Items', 'GR Pending', 'WIP Items', 'To Reallocate', 'Missing Materials'],
            'Count': [
                len(qc_items) if not qc_items.empty else 0,
                len(gr_items) if not gr_items.empty else 0,
                len(wip_items) if not wip_items.empty else 0,
                len(allocate_items) if not allocate_items.empty else 0,
                len(missing_items) if not missing_items.empty else 0
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
    
    buffer.seek(0)
    
    st.download_button(
        label="📦 Export Complete Action Report",
        data=buffer,
        file_name=f"Production_Action_Report_{file_suffix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="export_all"
    )

if __name__ == "__main__":
    main()
import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
import json
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="TPL QA/QC Tracker", layout="centered", page_icon="⚡")

DB_FILE = "tpl_jobs_database.json"
PHOTOS_DIR = "uploaded_photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

# LIVE APP URL FOR SCANNING
LIVE_APP_URL = "https://epaiqfnt5gkqh8brx.streamlit.app"

# 1. DATABASE LOAD & SAVE
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return [
        {
            "job_id": "TPL-GEN-001",
            "desc": "Soundproof canopy 250kVA - Base frame welding & acoustic panel cutting",
            "worker": "Kamal Silva",
            "start_time": "2026-09-14 08:30 AM",
            "status": "In Progress",
            "qc_defect": "Weld undercut at base plate corner",
            "defect_rectified": False,
            "rectification_note": "Grinded and re-welded with E7018 rod",
            "qc_photo_path": ""
        }
    ]

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

if "jobs_db" not in st.session_state:
    st.session_state.jobs_db = load_data()

# 2. DIGITAL CERTIFICATE VIEW (RENDERED CLEANLY)
query_params = st.query_params
if "verify_job" in query_params:
    verified_id = query_params["verify_job"]
    matched = [j for j in st.session_state.jobs_db if j["job_id"] == verified_id]
    
    if matched:
        job = matched[0]
        
        # Header Banner
        st.markdown("""
        <div style="background-color: #003366; color: white; padding: 20px; border-radius: 10px; text-align: center;">
            <h2 style="margin: 0; color: white; letter-spacing: 1px;">TRADE PROMOTERS LIMITED</h2>
            <p style="margin: 5px 0 0 0; font-size: 13px; color: #cbd5e1;">GENERATOR FABRICATION &amp; QA/QC CLEARANCE CERTIFICATE</p>
            <div style="margin-top: 12px;">
                <span style="background-color: #22c55e; color: white; padding: 5px 16px; border-radius: 20px; font-weight: bold; font-size: 13px;">
                    ✓ QUALITY VERIFIED &amp; COMPLETED
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        
        # Key Details Grid
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Job ID:** {job['job_id']}\n\n**Worker:** {job['worker']}")
        with col2:
            st.info(f"**Started At:** {job['start_time']}\n\n**Status:** Completed")

        # Job Scope Card
        st.markdown("#### 📋 Fabrication Scope")
        st.markdown(f"""
        <div style="background-color: #f8fafc; border-left: 5px solid #003366; padding: 12px; border-radius: 4px;">
            {job['desc']}
        </div>
        """, unsafe_allow_html=True)
        
        # QC Defect Card
        st.markdown("#### 🔍 QC Inspection Details")
        qc_txt = job['qc_defect'] if job['qc_defect'] else "None (Passed initial inspection)"
        st.markdown(f"""
        <div style="background-color: #fffbeb; border-left: 5px solid #f59e0b; padding: 12px; border-radius: 4px; color: #78350f;">
            {qc_txt}
        </div>
        """, unsafe_allow_html=True)

        # Rectification Card
        st.markdown("#### 🛠️ Rectification & Verification")
        rect_txt = job['rectification_note'] if job['rectification_note'] else "Fabricated according to factory standard tolerances."
        st.markdown(f"""
        <div style="background-color: #f0fdf4; border-left: 5px solid #22c55e; padding: 12px; border-radius: 4px; color: #14532d;">
            {rect_txt}
        </div>
        """, unsafe_allow_html=True)

        # Photo Display
        if job.get("qc_photo_path") and os.path.exists(job["qc_photo_path"]):
            st.write("---")
            st.markdown("#### 📷 QC Inspection Photo")
            st.image(job["qc_photo_path"], use_container_width=True)

        st.caption("This digital record is authenticated and maintained by Trade Promoters Limited Quality Control.")
        
        st.write("")
        if st.button("⬅️ Open Workshop System"):
            st.query_params.clear()
            st.rerun()
        st.stop()
    else:
        st.error(f"Job Record '{verified_id}' not found.")
        if st.button("⬅️ Back"):
            st.query_params.clear()
            st.rerun()
        st.stop()

# 3. PDF GENERATOR
def create_pdf(job, qr_link_url):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor("#003366"), fontSize=18, spaceAfter=4)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], alignment=1, textColor=colors.HexColor("#555555"), fontSize=10, spaceAfter=14)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, leading=12)
    header_cell = ParagraphStyle('HeaderCellStyle', parent=styles['Normal'], fontSize=9, leading=12, fontName="Helvetica-Bold")

    elements.append(Paragraph("TRADE PROMOTERS LIMITED", title_style))
    elements.append(Paragraph("GENERATOR FABRICATION &amp; QA/QC CLEARANCE REPORT", sub_style))

    job_info = [
        [Paragraph(f"<b>Job ID:</b> {job['job_id']}", cell_style), Paragraph(f"<b>Start Date/Time:</b> {job['start_time']}", cell_style)],
        [Paragraph(f"<b>Fabrication Worker:</b> {job['worker']}", cell_style), Paragraph("<b>Final Status:</b> <font color='green'><b>COMPLETED</b></font>", cell_style)]
    ]
    t1 = Table(job_info, colWidths=[270, 270])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F4F6F8")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D2D6DC"))
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 10))

    qc_defect_txt = job['qc_defect'] if job['qc_defect'] else "None (No defects reported)"
    rect_txt = job['rectification_note'] if job['rectification_note'] else "Completed to engineering standard"
    rect_status = "Rectified &amp; Cleared" if job['defect_rectified'] else "Not Applicable"

    body_info = [
        [Paragraph("<b>Job Scope / Description:</b>", header_cell)],
        [Paragraph(job['desc'], cell_style)],
        [Paragraph("<b>QC Reported Defects:</b>", header_cell)],
        [Paragraph(qc_defect_txt, cell_style)],
        [Paragraph("<b>Rectification Done by Floor Worker:</b>", header_cell)],
        [Paragraph(f"{rect_txt} (Status: {rect_status})", cell_style)]
    ]
    t2 = Table(body_info, colWidths=[540])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor("#FEF3C7")),
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor("#DCFCE7")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB"))
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 12))

    # Dynamic QR Code targeting the live URL
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(qr_link_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    sig_info = [
        [RLImage(qr_buf, width=80, height=80), 
         Paragraph("_______________________<br/><b>Fabrication Engineer</b>", cell_style),
         Paragraph("_______________________<br/><b>Authorized QC Sign</b>", cell_style)]
    ]
    t3 = Table(sig_info, colWidths=[120, 210, 210])
    t3.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    elements.append(t3)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==========================================
# MAIN APP INTERFACE
# ==========================================
st.title("⚡ TPL Generator Fabrication & QA/QC")

tab1, tab2 = st.tabs(["🛠️ Workshop (Assign, Rectify & Complete)", "🔍 QC Inspector (Report Defects)"])

# TAB 1: WORKSHOP
with tab1:
    st.subheader("1. Assign New Fabrication Job")
    
    # Auto Current Date & Time
    current_now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    with st.form("assign_job_form", clear_on_submit=True):
        new_job_id = st.text_input("Job ID", placeholder="e.g. TPL-GEN-002")
        new_desc = st.text_area("Job Scope / Fabrication Details", placeholder="Specify dimensions, gauge, welding...")
        new_worker = st.text_input("Assigned Employee Name")
        
        # Display auto date/time (Read only so users don't have to type)
        st.text(f"Auto Timestamp: {current_now_str}")
        
        assign_btn = st.form_submit_button("Assign Job")
        
        if assign_btn and new_job_id and new_desc and new_worker:
            st.session_state.jobs_db.append({
                "job_id": new_job_id.strip(),
                "desc": new_desc.strip(),
                "worker": new_worker.strip(),
                "start_time": current_now_str, # Auto assigned
                "status": "In Progress",
                "qc_defect": "",
                "defect_rectified": False,
                "rectification_note": "",
                "qc_photo_path": ""
            })
            save_data(st.session_state.jobs_db)
            st.success(f"Job {new_job_id} assigned at {current_now_str}!")
            st.rerun()

    st.write("---")
    st.subheader("2. Active Jobs: Fix Defects & Mark as Completed")
    
    active_jobs = [j for j in st.session_state.jobs_db if j["status"] != "Completed"]
    if not active_jobs:
        st.info("No active jobs currently in progress.")
    else:
        for idx, job in enumerate(active_jobs):
            status_color = "🔴" if job["qc_defect"] and not job["defect_rectified"] else "🟡"
            with st.expander(f"{status_color} {job['job_id']} - {job['worker']} [{job['status']}]", expanded=True):
                st.write(f"**Work Details:** {job['desc']}")
                st.caption(f"Started on: {job['start_time']}")
                
                if job["qc_defect"]:
                    st.error(f"⚠️ **QC Reported Defect:** {job['qc_defect']}")
                    if job.get("qc_photo_path") and os.path.exists(job["qc_photo_path"]):
                        st.image(job["qc_photo_path"], caption="QC Defect Photo", width=220)
                    
                    is_rect = st.checkbox(f"Defect Fixed / Rectified? ({job['job_id']})", value=job["defect_rectified"], key=f"rect_chk_{job['job_id']}")
                    rect_note = st.text_input(f"Action Taken to Fix ({job['job_id']})", value=job["rectification_note"], key=f"rect_note_{job['job_id']}", placeholder="e.g. Grinded down and re-welded")
                    job["defect_rectified"] = is_rect
                    job["rectification_note"] = rect_note
                    save_data(st.session_state.jobs_db)
                else:
                    st.success("No defects reported by QC yet.")

                st.write("---")
                is_comp = st.checkbox(f"✅ Mark Job as COMPLETED ({job['job_id']})", key=f"comp_{job['job_id']}")
                
                if st.button(f"Submit Final Job ({job['job_id']})", key=f"sub_{job['job_id']}"):
                    if is_comp:
                        job["status"] = "Completed"
                        save_data(st.session_state.jobs_db)
                        st.success(f"Job {job['job_id']} marked as COMPLETED!")
                        st.rerun()
                    else:
                        st.warning("Please tick the 'Mark Job as COMPLETED' box before submitting.")

    # COMPLETED JOBS ARCHIVE
    st.write("---")
    st.subheader("3. Completed Jobs Archive")
    
    completed_jobs = [j for j in st.session_state.jobs_db if j["status"] == "Completed"]
    if not completed_jobs:
        st.caption("No completed jobs yet.")
    else:
        for c_idx, c_job in enumerate(completed_jobs):
            with st.expander(f"🟢 {c_job['job_id']} - {c_job['worker']} (COMPLETED)"):
                st.write(f"**Description:** {c_job['desc']}")
                st.write(f"**Rectifications Logged:** {c_job['rectification_note'] if c_job['rectification_note'] else 'None'}")
                
                # Full Live URL for QR Scanning
                live_qr_url = f"{LIVE_APP_URL}/?verify_job={c_job['job_id']}"
                
                qr_preview = qrcode.QRCode(box_size=3, border=1)
                qr_preview.add_data(live_qr_url)
                qr_preview.make(fit=True)
                p_img = qr_preview.make_image(fill_color="black", back_color="white")
                img_io = io.BytesIO()
                p_img.save(img_io, format='PNG')
                st.image(img_io.getvalue(), caption="Scan QR with any Phone Camera to View Online Certificate", width=130)
                
                # View Certificate Inside App
                if st.button(f"👁️ View Digital Certificate ({c_job['job_id']})", key=f"view_{c_job['job_id']}"):
                    st.query_params["verify_job"] = c_job['job_id']
                    st.rerun()

                # PDF Download
                pdf_bytes = create_pdf(c_job, live_qr_url)
                st.download_button(
                    label=f"📄 Download / Print PDF ({c_job['job_id']})",
                    data=pdf_bytes,
                    file_name=f"TPL_Certificate_{c_job['job_id']}.pdf",
                    mime="application/pdf",
                    key=f"dl_{c_job['job_id']}_{c_idx}"
                )
                
                # Delete Record
                if st.button(f"🗑️ Delete Record ({c_job['job_id']})", key=f"del_{c_job['job_id']}_{c_idx}"):
                    st.session_state.jobs_db = [j for j in st.session_state.jobs_db if j["job_id"] != c_job["job_id"]]
                    save_data(st.session_state.jobs_db)
                    st.success(f"Job {c_job['job_id']} deleted permanently!")
                    st.rerun()

# TAB 2: QC INSPECTOR
with tab2:
    st.subheader("QC Defect Inspection & Reporting")
    
    ongoing = [j for j in st.session_state.jobs_db if j["status"] != "Completed"]
    if not ongoing:
        st.info("No active jobs available for inspection.")
    else:
        qc_job_ids = [j["job_id"] for j in ongoing]
        target_id = st.selectbox("Select Job ID to Inspect", qc_job_ids)
        target_job = next(j for j in st.session_state.jobs_db if j["job_id"] == target_id)
        
        st.markdown(f"**Work Scope:** {target_job['desc']}")
        st.markdown(f"**Assigned Worker:** {target_job['worker']}")
        
        with st.form("qc_report_form"):
            defect_text = st.text_area("QC Defect / Issue Found", value=target_job["qc_defect"], placeholder="Describe weld defect, paint issue, dimensional variation...")
            photo_file = st.file_uploader("Upload Inspection / Defect Photo", type=["jpg", "jpeg", "png"])
            submit_qc = st.form_submit_button("Submit QC Inspection")
            
            if submit_qc:
                target_job["qc_defect"] = defect_text
                if photo_file:
                    saved_path = os.path.join(PHOTOS_DIR, f"{target_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    with open(saved_path, "wb") as f:
                        f.write(photo_file.getbuffer())
                    target_job["qc_photo_path"] = saved_path
                target_job["defect_rectified"] = False
                save_data(st.session_state.jobs_db)
                st.success(f"QC Report saved permanently for {target_id}!")
                st.rerun()

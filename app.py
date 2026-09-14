import streamlit as st
import pandas as pd
from datetime import datetime
import io
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="TPL QA/QC Fabrication Tracker", layout="centered", page_icon="⚡")

# 1. In-memory Database
if "jobs_db" not in st.session_state:
    st.session_state.jobs_db = [
        {
            "job_id": "TPL-GEN-001",
            "desc": "Soundproof canopy 250kVA - Base frame welding and acoustic panel cutting",
            "worker": "Kamal Silva",
            "start_time": "2026-09-14 08:30 AM",
            "status": "In Progress",
            "qc_defect": "Weld undercut at base plate corner",
            "defect_rectified": False,
            "rectification_note": "Grinded and re-welded with E7018 rod",
            "qc_photo": None
        }
    ]

# 2. Bug-Free PDF Generator
def create_pdf(job):
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

    # Job Basic Info
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

    # Details & QC Sections
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

    # Standard Plain Text QR Code (Works on ANY camera/scanner app)
    qr_text = (
        f"--- TPL VERIFIED JOB ---\n"
        f"Job ID: {job['job_id']}\n"
        f"Worker: {job['worker']}\n"
        f"Status: COMPLETED\n"
        f"QC Defects: {qc_defect_txt}\n"
        f"Rectification: {rect_txt}\n"
        f"Verified: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}"
    )
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(qr_text)
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

# --- APP INTERFACE ---
st.title("⚡ TPL Generator Fabrication & QA/QC")

tab1, tab2 = st.tabs(["🛠️ Workshop (Assign, Rectify & Complete)", "🔍 QC Inspector (Report Defects)"])

# ==========================================
# TAB 1: WORKSHOP (FULL CONTROL & COMPLETION)
# ==========================================
with tab1:
    st.subheader("1. Assign New Fabrication Job")
    with st.form("assign_job_form", clear_on_submit=True):
        new_job_id = st.text_input("Job ID", placeholder="e.g. TPL-GEN-002")
        new_desc = st.text_area("Job Scope / Fabrication Details", placeholder="Specify canopy dimensions, gauge, welding scope...")
        new_worker = st.text_input("Assigned Employee Name")
        new_start = st.text_input("Start Date & Time", value=datetime.now().strftime("%Y-%m-%d %I:%M %p"))
        assign_btn = st.form_submit_button("Assign Job")
        
        if assign_btn and new_job_id and new_desc and new_worker:
            st.session_state.jobs_db.append({
                "job_id": new_job_id,
                "desc": new_desc,
                "worker": new_worker,
                "start_time": new_start,
                "status": "In Progress",
                "qc_defect": "",
                "defect_rectified": False,
                "rectification_note": "",
                "qc_photo": None
            })
            st.success(f"Job {new_job_id} assigned successfully!")
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
                
                # Show QC Defects if logged
                if job["qc_defect"]:
                    st.error(f"⚠️ **QC Reported Defect:** {job['qc_defect']}")
                    if job.get("qc_photo"):
                        st.image(job["qc_photo"], caption="QC Defect Photo", width=220)
                    
                    # Checkbox to confirm defect was rectified
                    is_rect = st.checkbox(f"Defect Fixed / Rectified? ({job['job_id']})", value=job["defect_rectified"], key=f"rect_chk_{job['job_id']}")
                    rect_note = st.text_input(f"Action Taken to Fix ({job['job_id']})", value=job["rectification_note"], key=f"rect_note_{job['job_id']}", placeholder="e.g. Ground down weld and redone")
                    job["defect_rectified"] = is_rect
                    job["rectification_note"] = rect_note
                else:
                    st.success("No defects reported by QC yet.")

                st.write("---")
                # Completion Section
                is_comp = st.checkbox(f"✅ Mark Job as COMPLETED ({job['job_id']})", key=f"comp_{job['job_id']}")
                
                if st.button(f"Submit Final Job ({job['job_id']})", key=f"sub_{job['job_id']}"):
                    if is_comp:
                        job["status"] = "Completed"
                        st.success(f"Job {job['job_id']} marked as COMPLETED! Generating Certificate & QR Code...")
                        
                        # Generate PDF & QR Immediately on Submit
                        pdf_data = create_pdf(job)
                        
                        # Display Direct Download Button
                        st.download_button(
                            label=f"📄 Download / Print PDF Certificate ({job['job_id']})",
                            data=pdf_data,
                            file_name=f"TPL_{job['job_id']}_Certificate.pdf",
                            mime="application/pdf"
                        )
                        st.rerun()
                    else:
                        st.warning("Please tick the 'Mark Job as COMPLETED' box before submitting.")

    # ==========================================
    # COMPLETED JOBS LIST (DOWNLOAD & DELETE)
    # ==========================================
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
                
                # Auto QR Display on Screen
                qr_preview = qrcode.QRCode(box_size=3, border=1)
                qr_preview.add_data(f"TPL JOB: {c_job['job_id']}\nWorker: {c_job['worker']}\nStatus: COMPLETED\nRectified: {c_job['rectification_note']}")
                qr_preview.make(fit=True)
                p_img = qr_preview.make_image(fill_color="black", back_color="white")
                img_io = io.BytesIO()
                p_img.save(img_io, format='PNG')
                st.image(img_io.getvalue(), caption="Scan with any Phone Camera to Verify", width=120)
                
                # PDF Download Button
                pdf_bytes = create_pdf(c_job)
                st.download_button(
                    label=f"📄 Download / Print PDF ({c_job['job_id']})",
                    data=pdf_bytes,
                    file_name=f"TPL_Certificate_{c_job['job_id']}.pdf",
                    mime="application/pdf",
                    key=f"dl_{c_job['job_id']}_{c_idx}"
                )
                
                # Delete Button
                if st.button(f"🗑️ Delete Record ({c_job['job_id']})", key=f"del_{c_job['job_id']}_{c_idx}"):
                    st.session_state.jobs_db = [j for j in st.session_state.jobs_db if j["job_id"] != c_job["job_id"]]
                    st.success(f"Job {c_job['job_id']} deleted!")
                    st.rerun()

# ==========================================
# TAB 2: QC INSPECTOR (REPORT DEFECTS & PHOTOS)
# ==========================================
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
            defect_text = st.text_area("QC Defect / Issue Found (Type details)", value=target_job["qc_defect"], placeholder="Describe weld porosity, dimensional errors, paint runs...")
            photo_file = st.file_uploader("Upload Inspection / Defect Photo", type=["jpg", "jpeg", "png"])
            submit_qc = st.form_submit_button("Submit QC Inspection")
            
            if submit_qc:
                target_job["qc_defect"] = defect_text
                if photo_file:
                    target_job["qc_photo"] = photo_file
                target_job["defect_rectified"] = False  # Reset rectification state
                st.success(f"QC Defect submitted for {target_id}! Workshop can now view and rectify this issue.")
                st.rerun()

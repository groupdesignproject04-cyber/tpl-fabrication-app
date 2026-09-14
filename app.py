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

st.set_page_config(page_title="TPL QA/QC Tracker", layout="centered", page_icon="⚡")

# 1. Local Database Simulation (Session State)
if "jobs_db" not in st.session_state:
    st.session_state.jobs_db = [
        {
            "job_id": "TPL-GEN-001",
            "desc": "Soundproof canopy sheet bending & box frame welding (250kVA)",
            "worker": "Kamal Perera",
            "start_time": "2026-09-14 08:30 AM",
            "status": "In Progress",
            "qc_defect": "Minor gap on bottom seam",
            "rectification": "Re-welded & ground smooth",
            "qc_photo": None
        }
    ]

# 2. PDF Generator Function with QR Code
def create_pdf(job):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        alignment=1,
        textColor=colors.HexColor("#003366"),
        fontSize=18,
        spaceAfter=4
    )
    sub_style = ParagraphStyle(
        'Sub',
        parent=styles['Normal'],
        alignment=1,
        textColor=colors.HexColor("#555555"),
        fontSize=11,
        spaceAfter=15
    )

    elements.append(Paragraph("TRADE PROMOTERS LIMITED", title_style))
    elements.append(Paragraph("GENERATOR FABRICATION & QA/QC CLEARANCE CERTIFICATE", sub_style))

    # Job Basic Details Table
    job_info = [
        [Paragraph(f"<b>Job ID:</b> {job['job_id']}", styles['Normal']), Paragraph(f"<b>Start Date/Time:</b> {job['start_time']}", styles['Normal'])],
        [Paragraph(f"<b>Assigned Employee:</b> {job['worker']}", styles['Normal']), Paragraph(f"<b>Status:</b> <font color='green'><b>COMPLETED</b></font>", styles['Normal'])]
    ]
    t1 = Table(job_info, colWidths=[270, 270])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F4F6F8")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D2D6DC"))
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 12))

    # Scope & Rectification Sections
    body_info = [
        [Paragraph("<b>Job Scope / Details:</b>", styles['Normal'])],
        [Paragraph(job['desc'], styles['Normal'])],
        [Paragraph("<b>QC Inspection & Defect Log:</b>", styles['Normal'])],
        [Paragraph(job['qc_defect'] if job['qc_defect'] else "None (Passed first inspection)", styles['Normal'])],
        [Paragraph("<b>Rectification / Actions Taken:</b>", styles['Normal'])],
        [Paragraph(job['rectification'] if job['rectification'] else "Fabricated according to specifications", styles['Normal'])]
    ]
    t2 = Table(body_info, colWidths=[540])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor("#FEF3C7")),
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor("#DCFCE7")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB"))
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 15))

    # Generate QR Code
    qr_data = f"TPL QUALITY VERIFIED\nJob ID: {job['job_id']}\nWorker: {job['worker']}\nStatus: COMPLETED\nRectification: {job['rectification']}"
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    
    # Signatures & QR Section
    sig_info = [
        [RLImage(qr_buffer, width=90, height=90), 
         Paragraph("<br><br>_____________________<br><b>Fabrication Engineer</b>", styles['Normal']),
         Paragraph("<br><br>_____________________<br><b>QC Inspector Sign</b>", styles['Normal'])]
    ]
    t3 = Table(sig_info, colWidths=[140, 200, 200])
    elements.append(t3)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- APP INTERFACE ---
st.title("⚡ TPL Fabrication QA/QC System")

# Top Navigation Tabs
tab1, tab2, tab3 = st.tabs(["➕ Assign Job", "🔍 QC & Rectification", "📋 Completed / Print PDF"])

# TAB 1: ASSIGN NEW JOB
with tab1:
    st.subheader("Assign New Fabrication Job")
    with st.form("new_job_form", clear_on_submit=True):
        job_id = st.text_input("Job ID", placeholder="e.g. TPL-GEN-002")
        desc = st.text_area("Job Scope / Description", placeholder="Type full work details, sheet sizes, frame specs...")
        worker = st.text_input("Assigned Employee Name")
        start_time = st.text_input("Start Date & Time", value=datetime.now().strftime("%Y-%m-%d %I:%M %A"))
        submit_job = st.form_submit_button("Assign Job")
        
        if submit_job:
            if job_id and desc and worker:
                st.session_state.jobs_db.append({
                    "job_id": job_id,
                    "desc": desc,
                    "worker": worker,
                    "start_time": start_time,
                    "status": "In Progress",
                    "qc_defect": "",
                    "rectification": "",
                    "qc_photo": None
                })
                st.success(f"Job {job_id} assigned successfully!")
            else:
                st.error("Please fill in Job ID, Description, and Employee Name.")

# TAB 2: QC INSPECTION & RECTIFICATION
with tab2:
    st.subheader("QC Inspection & Rectification")
    
    # Filter non-completed jobs
    active_jobs = [j for j in st.session_state.jobs_db if j["status"] != "Completed"]
    
    if not active_jobs:
        st.info("No ongoing jobs found.")
    else:
        job_options = [j["job_id"] for j in active_jobs]
        selected_id = st.selectbox("Select Active Job ID", job_options)
        
        # Get Job Object
        job = next(j for j in st.session_state.jobs_db if j["job_id"] == selected_id)
        
        st.markdown(f"**Description:** {job['desc']}")
        st.markdown(f"**Employee:** {job['worker']} | **Started:** {job['start_time']}")
        
        # QC Defect Logging
        st.write("---")
        st.markdown("#### 1. QC Defect / Issue Logging")
        qc_note = st.text_area("QC Defect / Rectification Note", value=job["qc_defect"], placeholder="Type any issues found during inspection...")
        uploaded_photo = st.file_uploader("Upload QC Defect Photo", type=["jpg", "jpeg", "png"])
        
        if uploaded_photo:
            job["qc_photo"] = uploaded_photo
            st.image(uploaded_photo, caption="Uploaded Defect Photo", width=250)

        # Worker Rectification
        st.write("---")
        st.markdown("#### 2. Rectification Action Taken")
        rect_note = st.text_area("How defect was rectified", value=job["rectification"], placeholder="Explain how the issues were resolved...")
        
        # Final Completion
        is_completed = st.checkbox("✅ All Work & Rectifications Completed (Mark as Completed)", value=(job["status"] == "Completed"))
        
        if st.button("Update Job Status"):
            job["qc_defect"] = qc_note
            job["rectification"] = rect_note
            if is_completed:
                job["status"] = "Completed"
                st.success(f"{selected_id} marked as Completed! Go to the 'Completed / Print PDF' tab to download Certificate.")
            else:
                job["status"] = "Needs Rectification" if qc_note else "In Progress"
                st.warning(f"{selected_id} updated. Current status: {job['status']}")
            st.rerun()

# TAB 3: COMPLETED JOBS & PRINT PDF
with tab3:
    st.subheader("Completed Jobs & PDF Verification")
    
    completed_jobs = [j for j in st.session_state.jobs_db if j["status"] == "Completed"]
    
    if not completed_jobs:
        st.info("No completed jobs yet. Complete a job from Tab 2 to generate certificates.")
    else:
        for c_job in completed_jobs:
            with st.expander(f"🟢 {c_job['job_id']} - {c_job['worker']} (COMPLETED)"):
                st.write(f"**Scope:** {c_job['desc']}")
                st.write(f"**Rectification Done:** {c_job['rectification']}")
                
                # Show QR Preview on screen
                qr = qrcode.QRCode(box_size=3, border=1)
                qr.add_data(f"TPL Job: {c_job['job_id']} | Status: Completed")
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                img_byte_arr = io.BytesIO()
                qr_img.save(img_byte_arr, format='PNG')
                st.image(img_byte_arr.getvalue(), caption=f"Scan to Verify {c_job['job_id']}", width=120)
                
                # Generate and download PDF button
                pdf_bytes = create_pdf(c_job)
                st.download_button(
                    label=f"📄 Download / Print PDF Certificate ({c_job['job_id']})",
                    data=pdf_bytes,
                    file_name=f"TPL_Certificate_{c_job['job_id']}.pdf",
                    mime="application/pdf"
                )

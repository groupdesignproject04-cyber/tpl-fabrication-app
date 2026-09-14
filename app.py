import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import io
import os
import json
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="TPL QA/QC Fabrication Tracker", layout="centered", page_icon="⚡")

DB_FILE = "tpl_jobs_database.json"
PHOTOS_DIR = "uploaded_photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

LIVE_APP_URL = "https://epaiqfnt5gkqh8brx.streamlit.app"

# SRI LANKA TIMEZONE FUNCTION
def get_sl_time():
    sl_tz = pytz.timezone('Asia/Colombo')
    return datetime.now(sl_tz).strftime("%Y-%m-%d %I:%M %p")

# DATABASE FUNCTIONS
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

if "jobs_db" not in st.session_state:
    st.session_state.jobs_db = load_data()

# DIGITAL CERTIFICATE VIEW (QR TARGET)
query_params = st.query_params
if "verify_job" in query_params:
    verified_id = query_params["verify_job"]
    matched = [j for j in st.session_state.jobs_db if j["job_id"] == verified_id]
    
    if matched:
        job = matched[0]
        st.markdown("""
        <div style="background-color: #003366; color: white; padding: 20px; border-radius: 10px; text-align: center;">
            <h2 style="margin: 0; color: white; letter-spacing: 1px;">TRADE PROMOTERS LIMITED</h2>
            <p style="margin: 5px 0 0 0; font-size: 13px; color: #cbd5e1;">GENERATOR FABRICATION QA/QC CLEARANCE RECORD</p>
            <div style="margin-top: 10px;">
                <span style="background-color: #22c55e; color: white; padding: 5px 16px; border-radius: 20px; font-weight: bold; font-size: 13px;">
                    ✓ FULLY RECTIFIED &amp; APPROVED
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Job ID:** {job['job_id']}\n\n**Worker:** {job['worker']}")
        with col2:
            st.info(f"**Start Time:** {job['start_time']}\n\n**Completed At:** {job.get('completed_time', 'N/A')}")

        st.markdown("#### 📋 Scope of Work")
        st.markdown(f"<div style='background-color: #f8fafc; border-left: 5px solid #003366; padding: 12px; border-radius: 4px;'>{job['desc']}</div>", unsafe_allow_html=True)
        
        st.markdown("#### 🛠️ Rectifications & Approvals Log")
        if not job["rectifications"]:
            st.success("Clean pass. No defects reported during inspection.")
        else:
            for idx, r in enumerate(job["rectifications"]):
                st.markdown(f"""
                <div style='background-color: #f0fdf4; border: 1px solid #bbf7d0; border-left: 5px solid #22c55e; padding: 10px; border-radius: 4px; margin-bottom: 8px;'>
                    <b>Issue #{idx+1}:</b> {r['defect']}<br/>
                    <b>Worker Action:</b> {r['action']}<br/>
                    <b>Verification:</b> <span style='color: #15803d; font-weight: bold;'>✓ Verified &amp; Approved by QC</span>
                </div>
                """, unsafe_allow_html=True)

        st.write("")
        if st.button("⬅️ Return to Portal"):
            st.query_params.clear()
            st.rerun()
        st.stop()

# PDF GENERATOR
def create_pdf(job, qr_link_url):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TStyle', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor("#003366"), fontSize=18, spaceAfter=4)
    sub_style = ParagraphStyle('SStyle', parent=styles['Normal'], alignment=1, textColor=colors.HexColor("#555555"), fontSize=10, spaceAfter=14)
    cell_style = ParagraphStyle('CStyle', parent=styles['Normal'], fontSize=9, leading=12)
    header_cell = ParagraphStyle('HStyle', parent=styles['Normal'], fontSize=9, leading=12, fontName="Helvetica-Bold")

    elements.append(Paragraph("TRADE PROMOTERS LIMITED", title_style))
    elements.append(Paragraph("GENERATOR FABRICATION &amp; QA/QC CLEARANCE CERTIFICATE", sub_style))

    job_info = [
        [Paragraph(f"<b>Job ID:</b> {job['job_id']}", cell_style), Paragraph(f"<b>Start Date/Time:</b> {job['start_time']}", cell_style)],
        [Paragraph(f"<b>Lead Worker:</b> {job['worker']}", cell_style), Paragraph(f"<b>Completed Time:</b> {job.get('completed_time', 'N/A')}", cell_style)]
    ]
    t1 = Table(job_info, colWidths=[270, 270])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F4F6F8")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D2D6DC"))
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 10))

    body_info = [
        [Paragraph("<b>Job Scope / Fabrication Details:</b>", header_cell)],
        [Paragraph(job['desc'], cell_style)]
    ]
    
    if job["rectifications"]:
        body_info.append([Paragraph("<b>QC Rectification History &amp; Approval Log:</b>", header_cell)])
        for i, r in enumerate(job["rectifications"]):
            body_info.append([Paragraph(f"<b>#{i+1} Defect:</b> {r['defect']}<br/><b>Action:</b> {r['action']} - <font color='green'><b>[QC Approved]</b></font>", cell_style)])
    else:
        body_info.append([Paragraph("<b>QC Inspection Status:</b>", header_cell)])
        body_info.append([Paragraph("No defects reported. Inspected and approved to factory standards.", cell_style)])

    t2 = Table(body_info, colWidths=[540])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor("#DCFCE7")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB"))
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 12))

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
# MAIN INTERFACE
# ==========================================
st.title("⚡ TPL Generator Fabrication & QA/QC")

tab1, tab2 = st.tabs(["🛠️ Workshop (Assign, Rectify & Complete)", "🔍 QC Inspector (Report Defects)"])

# TAB 1: WORKSHOP
with tab1:
    st.subheader("1. Assign New Fabrication Job")
    current_sl_time = get_sl_time()
    
    with st.form("assign_job_form", clear_on_submit=True):
        new_job_id = st.text_input("Job ID", placeholder="e.g. TPL-GEN-002")
        new_desc = st.text_area("Job Scope / Fabrication Details", placeholder="Canopy gauge, steel grade, welding specs...")
        new_worker = st.text_input("Assigned Employee Name")
        st.info(f"🕒 Auto Sri Lanka Time: **{current_sl_time}**")
        assign_btn = st.form_submit_button("Assign Job")
        
        if assign_btn and new_job_id and new_desc and new_worker:
            st.session_state.jobs_db.append({
                "job_id": new_job_id.strip(),
                "desc": new_desc.strip(),
                "worker": new_worker.strip(),
                "start_time": current_sl_time,
                "status": "In Progress",
                "rectifications": []
            })
            save_data(st.session_state.jobs_db)
            st.success(f"Job {new_job_id} assigned successfully!")
            st.rerun()

    st.write("---")
    st.subheader("2. Active Jobs & Rectification Pipeline")
    
    active_jobs = [j for j in st.session_state.jobs_db if j["status"] != "Completed"]
    if not active_jobs:
        st.info("No active jobs currently in progress.")
    else:
        for job in active_jobs:
            # Check if all rectifications have both worker fix and QC approval
            all_rect_cleared = True
            if job["rectifications"]:
                for r in job["rectifications"]:
                    if not (r["worker_done"] and r["qc_approved"]):
                        all_rect_cleared = False
                        break

            status_icon = "🟢" if all_rect_cleared and job["rectifications"] else ("🔴" if job["rectifications"] else "🟡")
            
            with st.expander(f"{status_icon} {job['job_id']} - {job['worker']} [{job['status']}]", expanded=True):
                st.write(f"**Description:** {job['desc']}")
                st.caption(f"Started: {job['start_time']}")

                # RECTIFICATIONS LIST
                if job["rectifications"]:
                    st.markdown("#### ⚠️ QC Rectification Items:")
                    for idx, r in enumerate(job["rectifications"]):
                        st.markdown(f"**Item #{idx+1}:** {r['defect']} *(Logged: {r.get('time', 'N/A')})*")
                        if r.get("photo") and os.path.exists(r["photo"]):
                            st.image(r["photo"], width=180)
                        
                        col_w, col_qc = st.columns(2)
                        with col_w:
                            # Worker Fix Checkbox & Action
                            w_tick = st.checkbox(f"Worker: Fixed #{idx+1}", value=r["worker_done"], key=f"w_chk_{job['job_id']}_{idx}")
                            action_txt = st.text_input(f"Action Taken #{idx+1}", value=r["action"], key=f"act_{job['job_id']}_{idx}", placeholder="e.g. Ground down and re-welded")
                            r["worker_done"] = w_tick
                            r["action"] = action_txt

                        with col_qc:
                            # QC Approval Checkbox
                            qc_tick = st.checkbox(f"QC: Verified & Approved #{idx+1}", value=r["qc_approved"], disabled=(not r["worker_done"]), key=f"qc_chk_{job['job_id']}_{idx}")
                            r["qc_approved"] = qc_tick
                            if not r["worker_done"]:
                                st.caption("*(Awaiting worker fix first)*")
                        st.divider()
                    
                    save_data(st.session_state.jobs_db)
                else:
                    st.success("No defects logged yet. Work in normal progress.")

                # COMPLETION LOCK GATE
                st.write("---")
                if not all_rect_cleared:
                    st.warning("🔒 Cannot complete job: All QC defect items must be fixed by Worker AND verified/approved by QC.")
                    st.checkbox("✅ Mark Job as COMPLETED", disabled=True, help="Disabled until all rectifications are approved by QC.")
                    st.button(f"Submit Final Job ({job['job_id']})", disabled=True)
                else:
                    is_comp = st.checkbox(f"✅ Mark Job as COMPLETED ({job['job_id']})", key=f"comp_{job['job_id']}")
                    if st.button(f"Submit Final Job ({job['job_id']})", key=f"sub_{job['job_id']}"):
                        if is_comp:
                            job["status"] = "Completed"
                            job["completed_time"] = get_sl_time()
                            save_data(st.session_state.jobs_db)
                            st.success(f"Job {job['job_id']} COMPLETED successfully!")
                            st.rerun()
                        else:
                            st.warning("Please tick the completion checkbox above before submitting.")

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
                st.write(f"**Completed At:** {c_job.get('completed_time', 'N/A')}")
                st.write(f"**Rectifications Cleared:** {len(c_job['rectifications'])} items verified.")
                
                live_qr_url = f"{LIVE_APP_URL}/?verify_job={c_job['job_id']}"
                
                qr_preview = qrcode.QRCode(box_size=3, border=1)
                qr_preview.add_data(live_qr_url)
                qr_preview.make(fit=True)
                p_img = qr_preview.make_image(fill_color="black", back_color="white")
                img_io = io.BytesIO()
                p_img.save(img_io, format='PNG')
                st.image(img_io.getvalue(), caption="Scan QR with Phone Camera to View Online Certificate", width=130)
                
                if st.button(f"👁️ View Digital Certificate ({c_job['job_id']})", key=f"view_{c_job['job_id']}"):
                    st.query_params["verify_job"] = c_job['job_id']
                    st.rerun()

                pdf_bytes = create_pdf(c_job, live_qr_url)
                st.download_button(
                    label=f"📄 Download / Print PDF ({c_job['job_id']})",
                    data=pdf_bytes,
                    file_name=f"TPL_Certificate_{c_job['job_id']}.pdf",
                    mime="application/pdf",
                    key=f"dl_{c_job['job_id']}_{c_idx}"
                )
                
                if st.button(f"🗑️ Delete Record ({c_job['job_id']})", key=f"del_{c_job['job_id']}_{c_idx}"):
                    st.session_state.jobs_db = [j for j in st.session_state.jobs_db if j["job_id"] != c_job["job_id"]]
                    save_data(st.session_state.jobs_db)
                    st.success(f"Job {c_job['job_id']} deleted!")
                    st.rerun()

# TAB 2: QC INSPECTOR (ADD MULTIPLE DEFECTS)
with tab2:
    st.subheader("QC Defect Inspection & Item Addition")
    
    ongoing = [j for j in st.session_state.jobs_db if j["status"] != "Completed"]
    if not ongoing:
        st.info("No active jobs available for inspection.")
    else:
        qc_job_ids = [j["job_id"] for j in ongoing]
        target_id = st.selectbox("Select Job ID to Inspect", qc_job_ids)
        target_job = next(j for j in st.session_state.jobs_db if j["job_id"] == target_id)
        
        st.markdown(f"**Work Scope:** {target_job['desc']}")
        st.markdown(f"**Assigned Worker:** {target_job['worker']}")

        # Show existing defects
        if target_job["rectifications"]:
            st.markdown(f"**Current Pending Defect Count:** {len(target_job['rectifications'])}")

        with st.form("qc_add_defect_form", clear_on_submit=True):
            defect_text = st.text_area("New Defect / Issue Found", placeholder="Describe weld porosity, paint scratch, misaligned holes...")
            photo_file = st.file_uploader("Upload Inspection / Defect Photo", type=["jpg", "jpeg", "png"])
            add_defect_btn = st.form_submit_button("➕ Add This Rectification Item")
            
            if add_defect_btn and defect_text:
                photo_path = ""
                if photo_file:
                    photo_path = os.path.join(PHOTOS_DIR, f"{target_id}_defect_{len(target_job['rectifications'])+1}.png")
                    with open(photo_path, "wb") as f:
                        f.write(photo_file.getbuffer())

                target_job["rectifications"].append({
                    "defect": defect_text.strip(),
                    "photo": photo_path,
                    "worker_done": False,
                    "action": "",
                    "qc_approved": False,
                    "time": get_sl_time()
                })
                target_job["status"] = "Needs Rectification"
                save_data(st.session_state.jobs_db)
                st.success(f"Defect item added to {target_id}! Workshop can now see and rectify it.")
                st.rerun()

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

st.set_page_config(page_title="TPL QA/QC Tracker", layout="centered", page_icon="⚡")

DB_FILE = "tpl_jobs_database.json"
PHOTOS_DIR = "uploaded_photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

# LIVE APP URL (Scannable from any phone without installing apps)
LIVE_APP_URL = "https://epaiqfnt5gkqh8brx.streamlit.app"

# SRI LANKA TIMEZONE FUNCTION (Colombo Time)
def get_sl_time():
    sl_tz = pytz.timezone('Asia/Colombo')
    return datetime.now(sl_tz).strftime("%Y-%m-%d %I:%M %p")

# DATABASE LOAD & AUTO-MIGRATE OLD JOBS
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                for j in data:
                    if "rectifications" not in j:
                        j["rectifications"] = []
                    if "status" not in j:
                        j["status"] = "In Progress"
                return data
        except Exception:
            return []
    return []

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

if "jobs_db" not in st.session_state:
    st.session_state.jobs_db = load_data()

# =======================================================
# 1. PUBLIC DIGITAL CERTIFICATE (ACCESSIBLE VIA ANY BROWSER)
# =======================================================
query_params = st.query_params
if "verify_job" in query_params:
    verified_id = query_params["verify_job"]
    matched = [j for j in st.session_state.jobs_db if j.get("job_id") == verified_id]
    
    if matched:
        job = matched[0]
        
        # Hide default streamlit header/footer for clean standalone look
        st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
        </style>
        """, unsafe_allow_html=True)
        
        # Official Certificate UI
        st.markdown(f"""
        <div style="background-color: #003366; color: white; padding: 22px; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <h2 style="margin: 0; color: white; letter-spacing: 1.5px; font-family: sans-serif;">TRADE PROMOTERS LIMITED</h2>
            <p style="margin: 6px 0 0 0; font-size: 12px; color: #cbd5e1; letter-spacing: 0.5px;">GENERATOR FABRICATION &amp; QA/QC CLEARANCE CERTIFICATE</p>
            <div style="margin-top: 14px;">
                <span style="background-color: #22c55e; color: white; padding: 6px 18px; border-radius: 20px; font-weight: bold; font-size: 13px; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
                    ✓ QUALITY VERIFIED &amp; COMPLETED
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Job ID:** {job.get('job_id', 'N/A')}\n\n**Lead Worker:** {job.get('worker', 'N/A')}")
        with col2:
            st.info(f"**Started:** {job.get('start_time', 'N/A')}\n\n**Completed:** {job.get('completed_time', 'N/A')}")

        st.markdown("#### 📋 Fabrication Scope")
        st.markdown(f"<div style='background-color: #f8fafc; border-left: 5px solid #003366; padding: 12px; border-radius: 6px; font-size: 14px;'>{job.get('desc', 'N/A')}</div>", unsafe_allow_html=True)
        
        st.markdown("#### 🛠️ Rectifications & Approvals Log")
        rects = job.get("rectifications", [])
        if not rects:
            st.success("Clean pass. Inspected and approved without defects.")
        else:
            for idx, r in enumerate(rects):
                st.markdown(f"""
                <div style='background-color: #f0fdf4; border: 1px solid #bbf7d0; border-left: 5px solid #22c55e; padding: 12px; border-radius: 6px; margin-bottom: 10px;'>
                    <b>Issue #{idx+1}:</b> {r.get('defect', '-')}<br/>
                    <b>Action Taken:</b> {r.get('action', '-')}<br/>
                    <b>Status:</b> <span style='color: #15803d; font-weight: bold;'>✓ Cleared &amp; Approved by QC</span>
                </div>
                """, unsafe_allow_html=True)
                if r.get("photo") and os.path.exists(r["photo"]):
                    st.image(r["photo"], width=220, caption=f"Inspection Photo #{idx+1}")

        st.caption("Authenticated Digital Quality Record • Trade Promoters Limited QA/QC Division")
        
        st.write("---")
        if st.button("⬅️ Open Workshop Portal"):
            st.query_params.clear()
            st.rerun()
        st.stop()
    else:
        st.error(f"Job Record '{verified_id}' not found in verification registry.")
        if st.button("⬅️ Back"):
            st.query_params.clear()
            st.rerun()
        st.stop()

# =======================================================
# 2. PDF GENERATOR
# =======================================================
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
        [Paragraph(f"<b>Job ID:</b> {job.get('job_id', '')}", cell_style), Paragraph(f"<b>Start Date/Time:</b> {job.get('start_time', '')}", cell_style)],
        [Paragraph(f"<b>Lead Worker:</b> {job.get('worker', '')}", cell_style), Paragraph(f"<b>Completed Time:</b> {job.get('completed_time', 'N/A')}", cell_style)]
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
        [Paragraph(job.get('desc', ''), cell_style)]
    ]
    
    rects = job.get("rectifications", [])
    if rects:
        body_info.append([Paragraph("<b>QC Rectification History &amp; Approval Log:</b>", header_cell)])
        for i, r in enumerate(rects):
            body_info.append([Paragraph(f"<b>#{i+1} Defect:</b> {r.get('defect', '')}<br/><b>Action:</b> {r.get('action', '')} - <font color='green'><b>[QC Approved]</b></font>", cell_style)])
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

# =======================================================
# 3. MAIN WORKSHOP & QC INTERFACE
# =======================================================
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
    
    active_jobs = [j for j in st.session_state.jobs_db if j.get("status") != "Completed"]
    if not active_jobs:
        st.info("No active jobs currently in progress.")
    else:
        for job in active_jobs:
            rects = job.get("rectifications", [])
            all_rect_cleared = True
            if rects:
                for r in rects:
                    if not (r.get("worker_done") and r.get("qc_approved")):
                        all_rect_cleared = False
                        break

            status_icon = "🟢" if (all_rect_cleared and rects) else ("🔴" if rects else "🟡")
            
            with st.expander(f"{status_icon} {job.get('job_id', '')} - {job.get('worker', '')} [{job.get('status', 'In Progress')}]", expanded=True):
                st.write(f"**Description:** {job.get('desc', '')}")
                st.caption(f"Started: {job.get('start_time', '')}")

                if rects:
                    st.markdown("#### ⚠️ QC Rectification Items:")
                    for idx, r in enumerate(rects):
                        st.markdown(f"**Item #{idx+1}:** {r.get('defect', '')} *(Logged: {r.get('time', 'N/A')})*")
                        if r.get("photo") and os.path.exists(r["photo"]):
                            st.image(r["photo"], width=180)
                        
                        col_w, col_qc = st.columns(2)
                        with col_w:
                            w_tick = st.checkbox(f"Worker: Fixed #{idx+1}", value=r.get("worker_done", False), key=f"w_chk_{job.get('job_id')}_{idx}")
                            action_txt = st.text_input(f"Action Taken #{idx+1}", value=r.get("action", ""), key=f"act_{job.get('job_id')}_{idx}", placeholder="e.g. Ground down and re-welded")
                            r["worker_done"] = w_tick
                            r["action"] = action_txt

                        with col_qc:
                            qc_tick = st.checkbox(f"QC: Verified & Approved #{idx+1}", value=r.get("qc_approved", False), disabled=(not r.get("worker_done", False)), key=f"qc_chk_{job.get('job_id')}_{idx}")
                            r["qc_approved"] = qc_tick
                            if not r.get("worker_done", False):
                                st.caption("*(Awaiting worker fix first)*")
                        st.divider()
                    
                    save_data(st.session_state.jobs_db)
                else:
                    st.success("No defects logged yet. Work in normal progress.")

                st.write("---")
                if not all_rect_cleared:
                    st.warning("🔒 Cannot complete job: All QC defect items must be fixed by Worker AND approved by QC.")
                    st.checkbox(f"✅ Mark Job as COMPLETED ({job.get('job_id')})", disabled=True, key=f"dis_comp_{job.get('job_id')}", help="Disabled until all rectifications are approved by QC.")
                    st.button(f"Submit Final Job ({job.get('job_id')})", disabled=True, key=f"dis_btn_{job.get('job_id')}")
                else:
                    is_comp = st.checkbox(f"✅ Mark Job as COMPLETED ({job.get('job_id')})", key=f"comp_{job.get('job_id')}")
                    if st.button(f"Submit Final Job ({job.get('job_id')})", key=f"sub_{job.get('job_id')}"):
                        if is_comp:
                            job["status"] = "Completed"
                            job["completed_time"] = get_sl_time()
                            save_data(st.session_state.jobs_db)
                            st.success(f"Job {job.get('job_id')} COMPLETED successfully!")
                            st.rerun()
                        else:
                            st.warning("Please tick the completion checkbox above before submitting.")

    # COMPLETED JOBS ARCHIVE
    st.write("---")
    st.subheader("3. Completed Jobs Archive")
    
    completed_jobs = [j for j in st.session_state.jobs_db if j.get("status") == "Completed"]
    if not completed_jobs:
        st.caption("No completed jobs yet.")
    else:
        for c_idx, c_job in enumerate(completed_jobs):
            c_rects = c_job.get("rectifications", [])
            with st.expander(f"🟢 {c_job.get('job_id', '')} - {c_job.get('worker', '')} (COMPLETED)"):
                st.write(f"**Description:** {c_job.get('desc', '')}")
                st.write(f"**Completed At:** {c_job.get('completed_time', 'N/A')}")
                st.write(f"**Rectifications Cleared:** {len(c_rects)} items verified.")
                
                # Standalone Web URL that opens directly in any phone's browser
                live_qr_url = f"{LIVE_APP_URL}/?verify_job={c_job.get('job_id', '')}"
                
                qr_preview = qrcode.QRCode(box_size=3, border=1)
                qr_preview.add_data(live_qr_url)
                qr_preview.make(fit=True)
                p_img = qr_preview.make_image(fill_color="black", back_color="white")
                img_io = io.BytesIO()
                p_img.save(img_io, format='PNG')
                st.image(img_io.getvalue(), caption="Scan QR with any phone to view web certificate", width=130)
                
                if st.button(f"👁️ View Digital Certificate ({c_job.get('job_id', '')})", key=f"view_{c_job.get('job_id', '')}_{c_idx}"):
                    st.query_params["verify_job"] = c_job.get('job_id', '')
                    st.rerun()

                pdf_bytes = create_pdf(c_job, live_qr_url)
                st.download_button(
                    label=f"📄 Download / Print PDF ({c_job.get('job_id', '')})",
                    data=pdf_bytes,
                    file_name=f"TPL_Certificate_{c_job.get('job_id', '')}.pdf",
                    mime="application/pdf",
                    key=f"dl_{c_job.get('job_id', '')}_{c_idx}"
                )
                
                if st.button(f"🗑️ Delete Record ({c_job.get('job_id', '')})", key=f"del_{c_job.get('job_id', '')}_{c_idx}"):
                    st.session_state.jobs_db = [j for j in st.session_state.jobs_db if j.get("job_id") != c_job.get("job_id")]
                    save_data(st.session_state.jobs_db)
                    st.success(f"Job {c_job.get('job_id')} deleted!")
                    st.rerun()

# TAB 2: QC INSPECTOR
with tab2:
    st.subheader("QC Defect Inspection & Item Addition")
    
    ongoing = [j for j in st.session_state.jobs_db if j.get("status") != "Completed"]
    if not ongoing:
        st.info("No active jobs available for inspection.")
    else:
        qc_job_ids = [j.get("job_id") for j in ongoing if j.get("job_id")]
        target_id = st.selectbox("Select Job ID to Inspect", qc_job_ids)
        target_job = next(j for j in st.session_state.jobs_db if j.get("job_id") == target_id)
        
        st.markdown(f"**Work Scope:** {target_job.get('desc', '')}")
        st.markdown(f"**Assigned Worker:** {target_job.get('worker', '')}")

        curr_rects = target_job.get("rectifications", [])
        if curr_rects:
            st.markdown(f"**Current Pending Defect Count:** {len(curr_rects)}")

        with st.form("qc_add_defect_form", clear_on_submit=True):
            defect_text = st.text_area("New Defect / Issue Found", placeholder="Describe weld porosity, paint scratch, misaligned holes...")
            photo_file = st.file_uploader("Upload Inspection / Defect Photo", type=["jpg", "jpeg", "png"])
            add_defect_btn = st.form_submit_button("➕ Add This Rectification Item")
            
            if add_defect_btn and defect_text:
                photo_path = ""
                if photo_file:
                    photo_path = os.path.join(PHOTOS_DIR, f"{target_id}_defect_{len(curr_rects)+1}.png")
                    with open(photo_path, "wb") as f:
                        f.write(photo_file.getbuffer())

                if "rectifications" not in target_job:
                    target_job["rectifications"] = []

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
                st.success(f"Defect item added to {target_id}!")
                st.rerun()

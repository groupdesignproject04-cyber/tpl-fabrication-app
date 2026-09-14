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

# LIVE PUBLIC DOMAIN FOR QR SCANNING
LIVE_APP_URL = "https://epaiqfnt5gkqh8brx.streamlit.app"

# SRI LANKA TIMEZONE (Asia/Colombo)
def get_sl_time():
    sl_tz = pytz.timezone('Asia/Colombo')
    return datetime.now(sl_tz).strftime("%Y-%m-%d %I:%M %p")

# DATABASE PERSISTENCE
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
                    if "qc_final_approval_photo" not in j:
                        j["qc_final_approval_photo"] = ""
                return data
        except Exception:
            return []
    return []

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

current_db = load_data()
st.session_state.jobs_db = current_db

# =======================================================
# 1. PUBLIC DIGITAL CERTIFICATE VIEW (OPENED VIA QR)
# =======================================================
if "verify_job" in st.query_params:
    verified_id = st.query_params["verify_job"]
    matched = [j for j in current_db if str(j.get("job_id")).strip().lower() == str(verified_id).strip().lower()]
    
    if matched:
        job = matched[0]
        
        st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background-color: #003366; color: white; padding: 22px; border-radius: 12px; text-align: center;">
            <h2 style="margin: 0; color: white; letter-spacing: 1px;">TRADE PROMOTERS LIMITED</h2>
            <p style="margin: 6px 0 0 0; font-size: 12px; color: #cbd5e1;">GENERATOR FABRICATION &amp; QA/QC CLEARANCE CERTIFICATE</p>
            <div style="margin-top: 14px;">
                <span style="background-color: #22c55e; color: white; padding: 6px 18px; border-radius: 20px; font-weight: bold; font-size: 13px;">
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
        
        st.markdown("#### 🛠️ Rectifications Log")
        rects = job.get("rectifications", [])
        if not rects:
            st.success("Clean pass. Initial inspection passed with zero defects.")
        else:
            for idx, r in enumerate(rects):
                st.markdown(f"""
                <div style='background-color: #f0fdf4; border: 1px solid #bbf7d0; border-left: 5px solid #22c55e; padding: 12px; border-radius: 6px; margin-bottom: 12px;'>
                    <b>Defect #{idx+1}:</b> {r.get('defect', '-')}<br/>
                    <b>Worker Rectification:</b> {r.get('action', '-')}<br/>
                    <b>Status:</b> <span style='color: #15803d; font-weight: bold;'>✓ Fixed by Worker</span>
                </div>
                """, unsafe_allow_html=True)
                
                img_col1, img_col2 = st.columns(2)
                with img_col1:
                    if r.get("photo") and os.path.exists(r["photo"]):
                        st.image(r["photo"], caption="QC Defect Photo", use_container_width=True)
                with img_col2:
                    if r.get("fixed_photo") and os.path.exists(r["fixed_photo"]):
                        st.image(r["fixed_photo"], caption="Worker Fixed Proof", use_container_width=True)

        if job.get("qc_final_approval_photo") and os.path.exists(job["qc_final_approval_photo"]):
            st.write("---")
            st.markdown("#### 🔍 QC Final Approval Verification Photo")
            st.image(job["qc_final_approval_photo"], caption="Authorized QC Clearance Photo", width=260)

        st.caption("Authenticated Digital Quality Record • Trade Promoters Limited QA/QC Division")
        
        st.write("---")
        if st.button("⬅️ Open Main Workshop Portal"):
            st.query_params.clear()
            st.rerun()
        st.stop()
    else:
        st.error(f"Job Record '{verified_id}' not found in registry.")
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
        body_info.append([Paragraph("<b>QC Rectification &amp; Action Log:</b>", header_cell)])
        for i, r in enumerate(rects):
            fixed_note = " [Photo Attached]" if r.get("fixed_photo") else ""
            body_info.append([Paragraph(f"<b>#{i+1} Defect:</b> {r.get('defect', '')}<br/><b>Worker Fix:</b> {r.get('action', '')}{fixed_note} - <font color='green'><b>[Fixed &amp; Cleared]</b></font>", cell_style)])
    else:
        body_info.append([Paragraph("<b>QC Inspection Status:</b>", header_cell)])
        body_info.append([Paragraph("No defects reported. Inspected and approved to standard tolerances.", cell_style)])

    body_info.append([Paragraph("<b>Final Verification:</b>", header_cell)])
    body_info.append([Paragraph("QC Final Approval Photo Verified &amp; Signed Off for Dispatch.", cell_style)])

    t2 = Table(body_info, colWidths=[540])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor("#DCFCE7")),
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor("#FEF3C7")),
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
                "rectifications": [],
                "qc_final_approval_photo": ""
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
            
            # 1. Check if all defects are fixed by worker
            all_worker_fixed = True
            if rects:
                for r in rects:
                    if not r.get("worker_done", False):
                        all_worker_fixed = False
                        break

            # 2. Check if QC has uploaded the final approval photo
            qc_photo_uploaded = bool(job.get("qc_final_approval_photo") and os.path.exists(job["qc_final_approval_photo"]))
            
            # Status icon
            status_icon = "🟢" if (all_worker_fixed and qc_photo_uploaded) else ("🔴" if rects and not all_worker_fixed else "🟡")
            
            with st.expander(f"{status_icon} {job.get('job_id', '')} - {job.get('worker', '')} [{job.get('status', 'In Progress')}]", expanded=True):
                st.write(f"**Description:** {job.get('desc', '')}")
                st.caption(f"Started: {job.get('start_time', '')}")

                # RECTIFICATIONS SECTION
                if rects:
                    st.markdown("#### ⚠️ QC Rectification Items:")
                    for idx, r in enumerate(rects):
                        st.markdown(f"**Item #{idx+1}:** {r.get('defect', '')} *(Logged: {r.get('time', 'N/A')})*")
                        
                        if r.get("photo") and os.path.exists(r["photo"]):
                            st.image(r["photo"], width=170, caption="QC Defect Photo (Optional)")
                        
                        col_w1, col_w2 = st.columns(2)
                        with col_w1:
                            w_tick = st.checkbox(f"Worker: Completed / Fixed #{idx+1}", value=r.get("worker_done", False), key=f"w_chk_{job.get('job_id')}_{idx}")
                            action_txt = st.text_input(f"Action Taken #{idx+1}", value=r.get("action", ""), key=f"act_{job.get('job_id')}_{idx}", placeholder="e.g. Re-welded and ground smooth")
                            r["worker_done"] = w_tick
                            r["action"] = action_txt

                        with col_w2:
                            # Optional worker fixed photo
                            fixed_photo_file = st.file_uploader(f"Upload Fixed Photo #{idx+1} (Optional)", type=["jpg", "jpeg", "png"], key=f"fixed_img_{job.get('job_id')}_{idx}")
                            if fixed_photo_file:
                                fixed_path = os.path.join(PHOTOS_DIR, f"{job.get('job_id')}_fixed_{idx+1}.png")
                                with open(fixed_path, "wb") as f:
                                    f.write(fixed_photo_file.getbuffer())
                                r["fixed_photo"] = fixed_path
                                st.success("Fixed photo attached!")

                            if r.get("fixed_photo") and os.path.exists(r["fixed_photo"]):
                                st.image(r["fixed_photo"], width=130, caption="Fixed Proof Photo")
                        
                        st.divider()
                    
                    save_data(st.session_state.jobs_db)
                else:
                    st.success("No defects logged yet. Work in normal progress.")

                # ==========================================
                # QC FINAL APPROVAL PHOTO GATEWAY
                # ==========================================
                st.write("---")
                st.markdown("#### 🛡️ QC Final Approval Photo (Required for Job Completion)")
                
                if not all_worker_fixed:
                    st.warning("⚠️ Worker must first mark all rectification items as 'Completed / Fixed' above.")
                
                # Upload QC Approval Photo
                qc_appr_file = st.file_uploader(f"📸 Upload QC Approval Photo / Sign ({job.get('job_id')})", type=["jpg", "jpeg", "png"], key=f"qc_appr_{job.get('job_id')}")
                if qc_appr_file:
                    appr_path = os.path.join(PHOTOS_DIR, f"{job.get('job_id')}_qc_approval.png")
                    with open(appr_path, "wb") as f:
                        f.write(qc_appr_file.getbuffer())
                    job["qc_final_approval_photo"] = appr_path
                    save_data(st.session_state.jobs_db)
                    st.success("QC Final Approval Photo successfully uploaded!")
                    st.rerun()

                if job.get("qc_final_approval_photo") and os.path.exists(job["qc_final_approval_photo"]):
                    st.image(job["qc_final_approval_photo"], width=200, caption="Verified QC Approval Photo")

                # COMPLETION CHECKBOX & SUBMISSION
                st.write("---")
                can_complete = all_worker_fixed and qc_photo_uploaded
                
                if not can_complete:
                    missing_reasons = []
                    if not all_worker_fixed:
                        missing_reasons.append("Worker must fix all defect items")
                    if not qc_photo_uploaded:
                        missing_reasons.append("QC must upload the Final Approval Photo")
                    
                    st.warning(f"🔒 Completion Locked: {', and '.join(missing_reasons)}.")
                    st.checkbox(f"✅ Mark Job as COMPLETED ({job.get('job_id')})", disabled=True, key=f"dis_comp_{job.get('job_id')}")
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
                st.write(f"**Rectifications Logged:** {len(c_rects)} items.")
                
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

# TAB 2: QC INSPECTOR (ADD DEFECTS)
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
            st.markdown(f"**Current Defect Count:** {len(curr_rects)}")

        with st.form("qc_add_defect_form", clear_on_submit=True):
            defect_text = st.text_area("Defect / Rectification Note", placeholder="Describe weld porosity, scratch, misaligned holes...")
            photo_file = st.file_uploader("Upload Inspection / Defect Photo (Optional)", type=["jpg", "jpeg", "png"])
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
                    "fixed_photo": "",
                    "worker_done": False,
                    "action": "",
                    "time": get_sl_time()
                })
                target_job["status"] = "Needs Rectification"
                save_data(st.session_state.jobs_db)
                st.success(f"Defect item added to {target_id}!")
                st.rerun()

import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import io
import os
import json
import base64
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="TPL QA/QC Clearance", layout="centered", page_icon="⚡")

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

# Helper to convert local image to base64 for reliable display
def get_image_base64(path):
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        except Exception:
            return None
    return None

# =======================================================
# 1. INSTANT PUBLIC VERIFICATION (NO LOGIN, PURE CERTIFICATE)
# =======================================================
query_params = st.query_params
if "verify_job" in query_params:
    verified_id = query_params["verify_job"]
    matched = [j for j in current_db if str(j.get("job_id", "")).strip().lower() == str(verified_id).strip().lower()]
    
    # Hide all Streamlit default UI elements completely
    st.markdown("""
    <style>
        #MainMenu, footer, header, .stDeployButton, [data-testid="stToolbar"] {display: none !important;}
        .block-container {padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 680px !important;}
        body {background-color: #f1f5f9;}
    </style>
    """, unsafe_allow_html=True)
    
    if matched:
        job = matched[0]
        
        # Header Banner
        st.markdown(f"""
        <div style="background-color: #003366; color: white; padding: 24px 16px; border-radius: 12px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.12);">
            <h2 style="margin: 0; color: #ffffff; letter-spacing: 1.5px; font-size: 22px; font-weight: 800;">TRADE PROMOTERS LIMITED</h2>
            <p style="margin: 5px 0 0 0; font-size: 11px; color: #93c5fd; letter-spacing: 0.8px; text-transform: uppercase;">GENERATOR FABRICATION QA/QC CLEARANCE CERTIFICATE</p>
            <div style="margin-top: 14px;">
                <span style="background-color: #16a34a; color: white; padding: 6px 18px; border-radius: 20px; font-weight: bold; font-size: 12px; display: inline-block; letter-spacing: 0.5px;">
                    ✓ AUTHENTIC &amp; QUALITY VERIFIED
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        
        # Basic Job Info Card
        st.markdown(f"""
        <div style="background: white; border-radius: 10px; padding: 16px; border: 1px solid #e2e8f0; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <table style="width: 100%; font-size: 13px; line-height: 1.8;">
                <tr>
                    <td style="color: #64748b; width: 45%;">Job ID:</td>
                    <td style="font-weight: bold; color: #0f172a;">{job.get('job_id', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="color: #64748b;">Fabrication Lead:</td>
                    <td style="font-weight: bold; color: #0f172a;">{job.get('worker', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="color: #64748b;">Started Date/Time:</td>
                    <td style="color: #0f172a;">{job.get('start_time', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="color: #64748b;">Completed Date/Time:</td>
                    <td style="color: #16a34a; font-weight: bold;">{job.get('completed_time', 'N/A')}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        # Work Scope
        st.markdown("##### 📋 Fabrication Scope")
        st.markdown(f"""
        <div style="background: white; border-left: 5px solid #003366; border-radius: 6px; padding: 12px 16px; font-size: 13px; color: #1e293b; margin-bottom: 16px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;">
            {job.get('desc', 'N/A')}
        </div>
        """, unsafe_allow_html=True)
        
        # Rectifications & QC Actions
        st.markdown("##### 🛠️ QC Rectifications & Clearances")
        rects = job.get("rectifications", [])
        if not rects:
            st.markdown("""
            <div style="background: #f0fdf4; border-left: 5px solid #16a34a; padding: 12px 16px; border-radius: 6px; font-size: 13px; color: #166534;">
                Clean pass. All fabrication parameters satisfied standard engineering specifications on initial inspection.
            </div>
            """, unsafe_allow_html=True)
        else:
            for idx, r in enumerate(rects):
                st.markdown(f"""
                <div style="background: white; border: 1px solid #e2e8f0; border-left: 5px solid #16a34a; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                    <div style="font-size: 13px; font-weight: bold; color: #991b1b; margin-bottom: 4px;">Defect #{idx+1}: {r.get('defect', '-')}</div>
                    <div style="font-size: 13px; color: #166534; font-weight: 500;">✓ Action Taken: {r.get('action', '-')}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Photos for this defect (Defect Photo & Fixed Photo)
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    if r.get("photo") and os.path.exists(r["photo"]):
                        st.image(r["photo"], caption=f"Defect Photo #{idx+1}", use_container_width=True)
                with col_p2:
                    if r.get("fixed_photo") and os.path.exists(r["fixed_photo"]):
                        st.image(r["fixed_photo"], caption=f"Fixed Proof #{idx+1}", use_container_width=True)

        # Final QC Approval Photo
        if job.get("qc_final_approval_photo") and os.path.exists(job["qc_final_approval_photo"]):
            st.write("")
            st.markdown("##### 🔍 QC Final Clearance Verification")
            st.image(job["qc_final_approval_photo"], caption="Authorized QC Final Sign-Off Photo", use_container_width=True)

        # Footer Verification Badge
        st.markdown("""
        <div style="text-align: center; font-size: 11px; color: #64748b; margin-top: 25px; border-top: 1px solid #cbd5e1; padding-top: 15px;">
            Digitally Authenticated Certificate • Trade Promoters Limited<br>
            Quality Assurance &amp; Generator Installation Division
        </div>
        """, unsafe_allow_html=True)

        st.stop()
    else:
        st.error(f"Certificate record for Job ID '{verified_id}' was not found.")
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
# 3. WORKSHOP & QC MAIN APP PORTAL
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
            
            all_worker_fixed = True
            if rects:
                for r in rects:
                    if not r.get("worker_done", False):
                        all_worker_fixed = False
                        break

            qc_photo_uploaded = bool(job.get("qc_final_approval_photo") and os.path.exists(job["qc_final_approval_photo"]))
            status_icon = "🟢" if (all_worker_fixed and qc_photo_uploaded) else ("🔴" if rects and not all_worker_fixed else "🟡")
            
            with st.expander(f"{status_icon} {job.get('job_id', '')} - {job.get('worker', '')} [{job.get('status', 'In Progress')}]", expanded=True):
                st.write(f"**Description:** {job.get('desc', '')}")
                st.caption(f"Started: {job.get('start_time', '')}")

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

                st.write("---")
                st.markdown("#### 🛡️ QC Final Approval Photo (Required for Completion)")
                
                if not all_worker_fixed:
                    st.warning("⚠️ Worker must first mark all defect items as 'Completed / Fixed' above.")
                
                qc_appr_file = st.file_uploader(f"📸 Upload QC Approval Photo / Sign ({job.get('job_id')})", type=["jpg", "jpeg", "png"], key=f"qc_appr_{job.get('job_id')}")
                if qc_appr_file:
                    appr_path = os.path.join(PHOTOS_DIR, f"{job.get('job_id')}_qc_approval.png")
                    with open(appr_path, "wb") as f:
                        f.write(qc_appr_file.getbuffer())
                    job["qc_final_approval_photo"] = appr_path
                    save_data(st.session_state.jobs_db)
                    st.success("QC Final Approval Photo successfully attached!")
                    st.rerun()

                if job.get("qc_final_approval_photo") and os.path.exists(job["qc_final_approval_photo"]):
                    st.image(job["qc_final_approval_photo"], width=200, caption="Verified QC Approval Photo")

                st.write("---")
                can_complete = all_worker_fixed and qc_photo_uploaded
                
                if not can_complete:
                    missing_reasons = []
                    if not all_worker_fixed:
                        missing_reasons.append("Worker must fix all defects")
                    if not qc_photo_uploaded:
                        missing_reasons.append("QC Approval Photo must be uploaded")
                    
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
                st.write(f"**Rectifications Cleared:** {len(c_rects)} items.")
                
                # Public Standalone QR URL
                live_qr_url = f"{LIVE_APP_URL}/?verify_job={c_job.get('job_id', '')}"
                
                qr_preview = qrcode.QRCode(box_size=3, border=1)
                qr_preview.add_data(live_qr_url)
                qr_preview.make(fit=True)
                p_img = qr_preview.make_image(fill_color="black", back_color="white")
                img_io = io.BytesIO()
                p_img.save(img_io, format='PNG')
                st.image(img_io.getvalue(), caption="Scan QR with any phone camera to verify", width=140)

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

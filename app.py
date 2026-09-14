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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="TPL QA/QC Fabrication System", layout="centered", page_icon="⚡")

DB_FILE = "tpl_jobs_database.json"
PHOTOS_DIR = "uploaded_photos"
CERT_DIR = "generated_certificates"
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)

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

# Helper to encode images for HTML Certificate
def img_to_b64(path):
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        except Exception:
            return ""
    return ""

# =======================================================
# 1. PUBLIC DIGITAL CERTIFICATE (ZERO-LOGIN AUTO-DISPLAY)
# =======================================================
if "verify_job" in st.query_params:
    verified_id = st.query_params["verify_job"]
    matched = [j for j in current_db if str(j.get("job_id", "")).strip().lower() == str(verified_id).strip().lower()]
    
    st.markdown("""
    <style>
        #MainMenu, footer, header, .stDeployButton, [data-testid="stToolbar"] {display: none !important;}
        .block-container {padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 650px !important;}
        body {background-color: #f8fafc;}
    </style>
    """, unsafe_allow_html=True)
    
    if matched:
        job = matched[0]
        
        st.markdown(f"""
        <div style="background-color: #003366; color: white; padding: 22px; border-radius: 12px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
            <h2 style="margin: 0; color: #ffffff; letter-spacing: 1.5px; font-size: 20px; font-weight: 800;">TRADE PROMOTERS LIMITED</h2>
            <p style="margin: 5px 0 0 0; font-size: 11px; color: #93c5fd; letter-spacing: 0.8px; text-transform: uppercase;">OFFICIAL GENERATOR QA/QC DIGITAL CERTIFICATE</p>
            <div style="margin-top: 12px;">
                <span style="background-color: #16a34a; color: white; padding: 5px 16px; border-radius: 20px; font-weight: bold; font-size: 12px; display: inline-block;">
                    ✓ AUTHENTIC &amp; QUALITY VERIFIED
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        
        st.markdown(f"""
        <div style="background: white; border-radius: 10px; padding: 14px; border: 1px solid #e2e8f0; margin-bottom: 12px;">
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

        st.markdown("##### 📋 Fabrication Scope")
        st.markdown(f"""
        <div style="background: white; border-left: 5px solid #003366; border-radius: 6px; padding: 10px 14px; font-size: 13px; color: #1e293b; margin-bottom: 14px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;">
            {job.get('desc', 'N/A')}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("##### 🛠️ QC Rectifications & Clearances")
        rects = job.get("rectifications", [])
        if not rects:
            st.markdown("""
            <div style="background: #f0fdf4; border-left: 5px solid #16a34a; padding: 10px 14px; border-radius: 6px; font-size: 13px; color: #166534;">
                Clean pass. All fabrication parameters satisfied standard engineering specifications on initial inspection.
            </div>
            """, unsafe_allow_html=True)
        else:
            for idx, r in enumerate(rects):
                st.markdown(f"""
                <div style="background: white; border: 1px solid #e2e8f0; border-left: 5px solid #16a34a; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px;">
                    <div style="font-size: 13px; font-weight: bold; color: #991b1b; margin-bottom: 3px;">Defect #{idx+1}: {r.get('defect', '-')}</div>
                    <div style="font-size: 13px; color: #166534; font-weight: 500;">✓ Action Taken: {r.get('action', '-')}</div>
                </div>
                """, unsafe_allow_html=True)
                
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    if r.get("photo") and os.path.exists(r["photo"]):
                        st.image(r["photo"], caption=f"Defect Photo #{idx+1}", use_container_width=True)
                with col_p2:
                    if r.get("fixed_photo") and os.path.exists(r["fixed_photo"]):
                        st.image(r["fixed_photo"], caption=f"Worker Proof #{idx+1}", use_container_width=True)

        if job.get("qc_final_approval_photo") and os.path.exists(job["qc_final_approval_photo"]):
            st.write("")
            st.markdown("##### 🔍 QC Final Clearance Sign-Off")
            st.image(job["qc_final_approval_photo"], caption="QC Final Clearance Stamp / Photo", use_container_width=True)

        st.markdown("""
        <div style="text-align: center; font-size: 11px; color: #64748b; margin-top: 20px; border-top: 1px solid #cbd5e1; padding-top: 12px;">
            Digitally Authenticated Certificate • Trade Promoters Limited<br>
            Quality Assurance &amp; Generator Installation Division
        </div>
        """, unsafe_allow_html=True)

        st.stop()
    else:
        st.error(f"Certificate record for Job ID '{verified_id}' was not found.")
        st.stop()

# =======================================================
# 2. AUTO DIGITAL CERTIFICATE HTML GENERATOR
# =======================================================
def generate_html_certificate(job, qr_data_url):
    rects = job.get("rectifications", [])
    rect_html = ""
    if not rects:
        rect_html = '<div style="background:#f0fdf4; border-left:4px solid #16a34a; padding:10px; font-size:12px; color:#166534;">Clean pass. No defects reported. Inspected and approved to engineering standards.</div>'
    else:
        for idx, r in enumerate(rects):
            d_b64 = img_to_b64(r.get("photo"))
            f_b64 = img_to_b64(r.get("fixed_photo"))
            d_img = f'<img src="{d_b64}" style="max-width:140px; border-radius:4px; border:1px solid #ccc; margin-top:5px;"><br><small>Defect Photo</small>' if d_b64 else ''
            f_img = f'<img src="{f_b64}" style="max-width:140px; border-radius:4px; border:1px solid #ccc; margin-top:5px;"><br><small>Worker Proof</small>' if f_b64 else ''
            
            rect_html += f"""
            <div style="border:1px solid #e2e8f0; border-left:4px solid #16a34a; padding:8px 12px; border-radius:4px; margin-bottom:8px; font-size:12px;">
                <b style="color:#b91c1c;">Issue #{idx+1}:</b> {r.get('defect', '-')}<br>
                <b style="color:#15803d;">Action:</b> {r.get('action', '-')}<br>
                <table style="margin-top:6px;"><tr><td style="padding-right:10px;">{d_img}</td><td>{f_img}</td></tr></table>
            </div>
            """

    qc_appr_b64 = img_to_b64(job.get("qc_final_approval_photo"))
    qc_appr_html = f'<div style="margin-top:10px;"><b>QC Clearance Photo:</b><br><img src="{qc_appr_b64}" style="max-width:200px; border-radius:4px; border:1px solid #ccc; margin-top:4px;"></div>' if qc_appr_b64 else ''

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TPL Digital Certificate - {job.get('job_id')}</title>
<style>
    body {{ font-family: Arial, sans-serif; background: #f8fafc; margin: 0; padding: 15px; color: #0f172a; }}
    .card {{ background: white; max-width: 600px; margin: auto; border: 2px solid #003366; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    .hdr {{ background: #003366; color: white; text-align: center; padding: 15px; border-radius: 6px; margin-bottom: 15px; }}
    .badge {{ background: #16a34a; color: white; padding: 4px 14px; border-radius: 15px; font-size: 11px; font-weight: bold; display: inline-block; margin-top: 8px; }}
    table {{ width: 100%; font-size: 13px; line-height: 1.6; border-collapse: collapse; }}
    .scope {{ background: #f8fafc; border-left: 4px solid #003366; padding: 8px 12px; font-size: 12px; margin-bottom: 12px; }}
</style>
</head>
<body>
<div class="card">
    <div class="hdr">
        <h2 style="margin:0; font-size:18px;">TRADE PROMOTERS LIMITED</h2>
        <div style="font-size:10px; color:#93c5fd; margin-top:3px;">GENERATOR FABRICATION QA/QC DIGITAL CERTIFICATE</div>
        <div class="badge">✓ VERIFIED & COMPLETED</div>
    </div>
    <table style="margin-bottom:12px;">
        <tr><td style="color:#64748b;">Job ID:</td><td><b>{job.get('job_id')}</b></td></tr>
        <tr><td style="color:#64748b;">Worker:</td><td><b>{job.get('worker')}</b></td></tr>
        <tr><td style="color:#64748b;">Started:</td><td>{job.get('start_time')}</td></tr>
        <tr><td style="color:#64748b;">Completed:</td><td style="color:#16a34a; font-weight:bold;">{job.get('completed_time')}</td></tr>
    </table>
    <div style="font-weight:bold; font-size:12px; margin-bottom:4px;">Fabrication Scope:</div>
    <div class="scope">{job.get('desc')}</div>
    <div style="font-weight:bold; font-size:12px; margin-bottom:4px;">QC Rectification & Clearance Log:</div>
    {rect_html}
    {qc_appr_html}
    <div style="text-align:center; margin-top:20px; border-top:1px solid #e2e8f0; padding-top:12px;">
        <img src="{qr_data_url}" width="90" height="90"><br>
        <small style="color:#64748b; font-size:10px;">Scanned Verification Record • Trade Promoters Limited</small>
    </div>
</div>
</body>
</html>
"""
    return html_content

# =======================================================
# 3. PDF GENERATOR
# =======================================================
def create_pdf(job, qr_link_url):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TStyle', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor("#003366"), fontSize=17, spaceAfter=3)
    sub_style = ParagraphStyle('SStyle', parent=styles['Normal'], alignment=1, textColor=colors.HexColor("#555555"), fontSize=9, spaceAfter=12)
    cell_style = ParagraphStyle('CStyle', parent=styles['Normal'], fontSize=8.5, leading=11)
    header_cell = ParagraphStyle('HStyle', parent=styles['Normal'], fontSize=8.5, leading=11, fontName="Helvetica-Bold")

    elements.append(Paragraph("TRADE PROMOTERS LIMITED", title_style))
    elements.append(Paragraph("GENERATOR FABRICATION QA/QC CLEARANCE CERTIFICATE", sub_style))

    job_info = [
        [Paragraph(f"<b>Job ID:</b> {job.get('job_id', '')}", cell_style), Paragraph(f"<b>Start Date/Time:</b> {job.get('start_time', '')}", cell_style)],
        [Paragraph(f"<b>Lead Worker:</b> {job.get('worker', '')}", cell_style), Paragraph(f"<b>Completed Time:</b> {job.get('completed_time', 'N/A')}", cell_style)]
    ]
    t1 = Table(job_info, colWidths=[270, 270])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F4F6F8")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D2D6DC"))
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 8))

    scope_info = [
        [Paragraph("<b>Job Scope / Fabrication Details:</b>", header_cell)],
        [Paragraph(job.get('desc', ''), cell_style)]
    ]
    t_scope = Table(scope_info, colWidths=[540])
    t_scope.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB"))
    ]))
    elements.append(t_scope)
    elements.append(Spacer(1, 8))

    rects = job.get("rectifications", [])
    if rects:
        rect_rows = [[Paragraph("<b>QC Rectification Audit Log &amp; Photo Proofs:</b>", header_cell)]]
        for i, r in enumerate(rects):
            rect_rows.append([Paragraph(f"<b>Issue #{i+1}:</b> {r.get('defect', '')}<br/><b>Worker Action:</b> {r.get('action', '')} - <font color='green'><b>[Fixed &amp; Cleared]</b></font>", cell_style)])
            
            photo_cells = []
            if r.get("photo") and os.path.exists(r["photo"]):
                try:
                    photo_cells.append(RLImage(r["photo"], width=130, height=95))
                except Exception:
                    photo_cells.append(Paragraph("[Defect Photo]", cell_style))
            else:
                photo_cells.append(Paragraph("No Defect Photo", cell_style))

            if r.get("fixed_photo") and os.path.exists(r["fixed_photo"]):
                try:
                    photo_cells.append(RLImage(r["fixed_photo"], width=130, height=95))
                except Exception:
                    photo_cells.append(Paragraph("[Fixed Proof]", cell_style))
            else:
                photo_cells.append(Paragraph("No Fixed Photo", cell_style))

            img_table = Table([[Paragraph("<b>QC Defect Photo:</b>", cell_style), Paragraph("<b>Worker Fixed Proof:</b>", cell_style)], photo_cells], colWidths=[260, 260])
            img_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('PADDING', (0,0), (-1,-1), 3)]))
            rect_rows.append([img_table])

        t2 = Table(rect_rows, colWidths=[540])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#FEF3C7")),
            ('PADDING', (0,0), (-1,-1), 4),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB"))
        ]))
        elements.append(t2)
        elements.append(Spacer(1, 8))
    else:
        pass_table = Table([[Paragraph("<b>QC Inspection Status:</b>", header_cell)], [Paragraph("Clean pass. Inspected and approved to factory standards without defects.", cell_style)]], colWidths=[540])
        pass_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#DCFCE7")), ('PADDING', (0,0), (-1,-1), 4), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB"))]))
        elements.append(pass_table)
        elements.append(Spacer(1, 8))

    if job.get("qc_final_approval_photo") and os.path.exists(job["qc_final_approval_photo"]):
        try:
            qc_img = RLImage(job["qc_final_approval_photo"], width=150, height=105)
            qc_table = Table([[Paragraph("<b>QC Final Approval Sign-Off Photo:</b>", header_cell)], [qc_img]], colWidths=[540])
            qc_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#DCFCE7")), ('ALIGN', (0,1), (-1,1), 'CENTER'), ('PADDING', (0,0), (-1,-1), 4), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB"))]))
            elements.append(qc_table)
            elements.append(Spacer(1, 8))
        except Exception:
            pass

    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(qr_link_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    sig_info = [
        [RLImage(qr_buf, width=75, height=75), 
         Paragraph("___________________________<br/><b>Fabrication Engineer</b><br/><font size=7 color='#666'>Trade Promoters Limited</font>", cell_style),
         Paragraph("___________________________<br/><b>Authorized QC Inspector</b><br/><font size=7 color='#666'>Quality Assurance Division</font>", cell_style)]
    ]
    t3 = Table(sig_info, colWidths=[120, 210, 210])
    t3.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 2)
    ]))
    elements.append(KeepTogether(t3))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# Helper: Get current live app origin dynamically
def get_clean_app_url():
    # If custom domain or streamlit app, build clean base URL
    return "https://epaiqfnt5gkqh8brx.streamlit.app"

# =======================================================
# 4. MAIN WORKSHOP & QC WORKSPACE
# =======================================================
st.title("⚡ TPL Generator Fabrication & QA/QC Portal")

# 1. ASSIGN JOB
st.subheader("1. Assign New Fabrication Job")
current_sl_time = get_sl_time()

with st.form("assign_job_form", clear_on_submit=True):
    new_job_id = st.text_input("Job ID", placeholder="e.g. TPL-GEN-002")
    new_desc = st.text_area("Job Scope / Fabrication Details", placeholder="Specify canopy dimensions, steel grade, welding specs...")
    new_worker = st.text_input("Assigned Employee Name")
    st.caption(f"🕒 Timestamp (Sri Lanka): **{current_sl_time}**")
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

# 2. ACTIVE JOBS
st.subheader("2. Ongoing Fabrication & QC Inspection Pipeline")

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

            # RECTIFICATIONS
            if rects:
                st.markdown("#### ⚠️ QC Rectification Issues:")
                for idx, r in enumerate(rects):
                    st.markdown(f"**Defect #{idx+1}:** {r.get('defect', '')} *(Logged: {r.get('time', 'N/A')})*")
                    if r.get("photo") and os.path.exists(r["photo"]):
                        st.image(r["photo"], width=170, caption="QC Defect Photo")
                    
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
                st.success("No defects logged yet. Work progressing normally.")

            # QC ADDS DEFECT
            st.markdown("#### 🔍 QC Inspector: Log Defect")
            with st.form(f"qc_add_defect_{job.get('job_id')}", clear_on_submit=True):
                defect_text = st.text_area("Defect / Rectification Note", placeholder="Describe issue: weld gap, misaligned holes, paint run...", key=f"def_txt_{job.get('job_id')}")
                photo_file = st.file_uploader("Upload Defect Photo (Optional)", type=["jpg", "jpeg", "png"], key=f"def_img_{job.get('job_id')}")
                add_defect_btn = st.form_submit_button("➕ Submit Rectification Issue")
                
                if add_defect_btn and defect_text:
                    photo_path = ""
                    if photo_file:
                        photo_path = os.path.join(PHOTOS_DIR, f"{job.get('job_id')}_defect_{len(rects)+1}.png")
                        with open(photo_path, "wb") as f:
                            f.write(photo_file.getbuffer())

                    job["rectifications"].append({
                        "defect": defect_text.strip(),
                        "photo": photo_path,
                        "fixed_photo": "",
                        "worker_done": False,
                        "action": "",
                        "time": get_sl_time()
                    })
                    job["status"] = "Needs Rectification"
                    save_data(st.session_state.jobs_db)
                    st.success(f"Rectification issue added to {job.get('job_id')}!")
                    st.rerun()

            # QC APPROVAL PHOTO
            st.write("---")
            st.markdown("#### 🛡️ QC Final Clearance Photo (Required for Completion)")
            qc_appr_file = st.file_uploader(f"📸 Upload QC Approval Photo / Sign ({job.get('job_id')})", type=["jpg", "jpeg", "png"], key=f"qc_appr_{job.get('job_id')}")
            if qc_appr_file:
                appr_path = os.path.join(PHOTOS_DIR, f"{job.get('job_id')}_qc_approval.png")
                with open(appr_path, "wb") as f:
                    f.write(qc_appr_file.getbuffer())
                job["qc_final_approval_photo"] = appr_path
                save_data(st.session_state.jobs_db)
                st.success("QC Final Approval Photo attached!")
                st.rerun()

            if job.get("qc_final_approval_photo") and os.path.exists(job["qc_final_approval_photo"]):
                st.image(job["qc_final_approval_photo"], width=200, caption="Verified QC Approval Photo")

            # COMPLETE & SUBMIT
            st.write("---")
            can_complete = all_worker_fixed and qc_photo_uploaded
            
            if not can_complete:
                missing_items = []
                if not all_worker_fixed:
                    missing_items.append("Worker must mark defects as Fixed")
                if not qc_photo_uploaded:
                    missing_items.append("QC Approval Photo must be uploaded")
                st.warning(f"🔒 Completion Locked: {', and '.join(missing_items)}.")
                st.checkbox(f"✅ Mark Job as COMPLETED ({job.get('job_id')})", disabled=True, key=f"dis_comp_{job.get('job_id')}")
                st.button(f"Submit Final Job ({job.get('job_id')})", disabled=True, key=f"dis_btn_{job.get('job_id')}")
            else:
                is_comp = st.checkbox(f"✅ Mark Job as COMPLETED ({job.get('job_id')})", key=f"comp_{job.get('job_id')}")
                if st.button(f"Submit Final Job ({job.get('job_id')})", key=f"sub_{job.get('job_id')}"):
                    if is_comp:
                        job["status"] = "Completed"
                        job["completed_time"] = get_sl_time()
                        save_data(st.session_state.jobs_db)
                        st.success(f"Job {job.get('job_id')} COMPLETED! Auto-generated Certificate & PDF are ready below.")
                        st.rerun()
                    else:
                        st.warning("Please tick the completion checkbox above before submitting.")

# 3. COMPLETED JOBS ARCHIVE
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
            
            # Universal Dynamic Clean QR URL
            live_qr_url = f"https://epaiqfnt5gkqh8brx.streamlit.app/?verify_job={c_job.get('job_id', '')}"
            
            qr_preview = qrcode.QRCode(box_size=3, border=1)
            qr_preview.add_data(live_qr_url)
            qr_preview.make(fit=True)
            p_img = qr_preview.make_image(fill_color="black", back_color="white")
            img_io = io.BytesIO()
            p_img.save(img_io, format='PNG')
            st.image(img_io.getvalue(), caption="Scan QR with any phone to view web certificate", width=140)

            # Auto-Generated HTML Digital Certificate
            qr_b64 = f"data:image/png;base64,{base64.b64encode(img_io.getvalue()).decode()}"
            html_cert = generate_html_certificate(c_job, qr_b64)
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                pdf_bytes = create_pdf(c_job, live_qr_url)
                st.download_button(
                    label=f"📄 Download / Print PDF ({c_job.get('job_id', '')})",
                    data=pdf_bytes,
                    file_name=f"TPL_{c_job.get('job_id', '')}_Certificate.pdf",
                    mime="application/pdf",
                    key=f"dl_pdf_{c_job.get('job_id', '')}_{c_idx}"
                )
            with col_d2:
                # Direct Download / Open Digital Certificate
                st.download_button(
                    label=f"🌐 Download Digital Certificate HTML ({c_job.get('job_id', '')})",
                    data=html_cert,
                    file_name=f"TPL_{c_job.get('job_id', '')}_DigitalCertificate.html",
                    mime="text/html",
                    key=f"dl_html_{c_job.get('job_id', '')}_{c_idx}"
                )

            if st.button(f"🗑️ Delete Record ({c_job.get('job_id', '')})", key=f"del_{c_job.get('job_id', '')}_{c_idx}"):
                st.session_state.jobs_db = [j for j in st.session_state.jobs_db if j.get("job_id") != c_job.get("job_id")]
                save_data(st.session_state.jobs_db)
                st.success(f"Job {c_job.get('job_id')} deleted!")
                st.rerun()

import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import io
import os
import json
import uuid
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="TPL QA/QC Fabrication System", layout="centered", page_icon="⚡")

DB_FILE = "tpl_jobs_database.json"
PHOTOS_DIR = "uploaded_photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)
PUBLIC_DOMAIN = "https://tpl-fabrication-app-evtpzepaiqfnt5gkqh8brx.streamlit.app"


def get_sl_time():
    sl_tz = pytz.timezone("Asia/Colombo")
    return datetime.now(sl_tz).strftime("%Y-%m-%d %I:%M %p")


def make_record_id():
    return f"REC-{uuid.uuid4().hex[:12].upper()}"


def normalize_photo_list(value):
    """Convert old single-photo fields and new list fields into a list."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if x]
    return [str(value)]


def migrate_job(j):
    if not j.get("record_id"):
        j["record_id"] = make_record_id()
    if "rectifications" not in j or not isinstance(j.get("rectifications"), list):
        j["rectifications"] = []
    if "status" not in j:
        j["status"] = "In Progress"

    # Migrate old single-photo fields to new multi-photo fields.
    for r in j["rectifications"]:
        if "photos" not in r:
            r["photos"] = normalize_photo_list(r.get("photo"))
        if "fixed_photos" not in r:
            r["fixed_photos"] = normalize_photo_list(r.get("fixed_photo"))
        r.setdefault("worker_done", False)
        r.setdefault("action", "")
        r.setdefault("time", "N/A")

    if "qc_final_approval_photos" not in j:
        j["qc_final_approval_photos"] = normalize_photo_list(j.get("qc_final_approval_photo"))
    return j


def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for j in data:
                migrate_job(j)
            return data
        except Exception:
            return []
    return []


def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def safe_remove_file(path):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


def save_uploaded_file(uploaded_file, prefix):
    """Save one uploaded image with a unique filename and return its path."""
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        ext = ".png"
    filename = f"{prefix}_{uuid.uuid4().hex[:10]}{ext}"
    path = os.path.join(PHOTOS_DIR, filename)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def photo_columns(photo_paths, prefix, width=150):
    """Display saved photos with an easy remove button."""
    valid = [p for p in photo_paths if p and os.path.exists(p)]
    if not valid:
        return False

    for i, path in enumerate(valid):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.image(path, width=width, caption=f"Photo {i + 1}")
        with col2:
            st.write("")
            if st.button("🗑️ Remove", key=f"{prefix}_remove_{i}_{uuid.uuid5(uuid.NAMESPACE_URL, path)}"):
                safe_remove_file(path)
                photo_paths.remove(path)
                return True
    return False


# Load + migrate old records.
current_db = load_data()
save_data(current_db)
st.session_state.jobs_db = current_db

if "delete_confirm_id" not in st.session_state:
    st.session_state.delete_confirm_id = None

# Uploader version counters: changing the widget key after a successful save
# clears the previous upload, so Streamlit cannot save the same file again on rerun.
if "photo_uploader_versions" not in st.session_state:
    st.session_state.photo_uploader_versions = {}

def uploader_version(name):
    return st.session_state.photo_uploader_versions.get(name, 0)

def bump_uploader_version(name):
    st.session_state.photo_uploader_versions[name] = uploader_version(name) + 1

# =======================================================
# 1. DIGITAL CERTIFICATE VIEW
# =======================================================
verify_id = st.query_params.get("verify_job")

if verify_id:
    clean_id = str(verify_id).strip().lower()
    matched = [j for j in current_db if str(j.get("record_id", "")).strip().lower() == clean_id]
    if not matched:
        # Backward compatibility for old QR codes that stored Job ID.
        matched = [j for j in current_db if str(j.get("job_id", "")).strip().lower() == clean_id]

    st.markdown("""
    <style>
        #MainMenu, footer, header, .stDeployButton, [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
        .block-container {padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 680px !important;}
        body {background-color: #f8fafc;}
    </style>
    """, unsafe_allow_html=True)

    if matched:
        job = matched[0]
        st.markdown(f"""
        <div style="background-color:#003366;color:white;padding:22px 14px;border-radius:12px;text-align:center;">
            <h2 style="margin:0;color:#ffffff;letter-spacing:1.2px;font-size:21px;font-weight:800;">TRADE PROMOTERS LIMITED</h2>
            <p style="margin:5px 0 0 0;font-size:11px;color:#93c5fd;letter-spacing:.8px;text-transform:uppercase;">GENERATOR FABRICATION QA/QC CLEARANCE CERTIFICATE</p>
            <div style="margin-top:12px;"><span style="background:#16a34a;color:white;padding:5px 16px;border-radius:20px;font-weight:bold;font-size:12px;display:inline-block;">✓ QUALITY VERIFIED &amp; COMPLETED</span></div>
        </div>
        """, unsafe_allow_html=True)
        st.write("")

        st.markdown(f"""
        <div style="background:white;border-radius:10px;padding:14px;border:1px solid #e2e8f0;margin-bottom:15px;">
            <table style="width:100%;font-size:13px;line-height:1.8;">
                <tr><td style="color:#64748b;width:45%;">Job ID:</td><td style="font-weight:bold;color:#0f172a;">{job.get('job_id','N/A')}</td></tr>
                <tr><td style="color:#64748b;">Fabrication Lead:</td><td style="font-weight:bold;color:#0f172a;">{job.get('worker','N/A')}</td></tr>
                <tr><td style="color:#64748b;">Started Date/Time:</td><td>{job.get('start_time','N/A')}</td></tr>
                <tr><td style="color:#64748b;">Completed Date/Time:</td><td style="color:#16a34a;font-weight:bold;">{job.get('completed_time','N/A')}</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("##### 📋 Fabrication Scope")
        st.info(job.get("desc", "N/A"))

        st.markdown("##### 🛠️ QC Rectifications & Clearances")
        rects = job.get("rectifications", [])
        if not rects:
            st.success("Clean pass. Initial inspection passed with standard engineering tolerances.")
        else:
            for idx, r in enumerate(rects):
                st.markdown(f"**Defect #{idx+1}:** {r.get('defect','-')}")
                st.markdown(f"✓ **Action Taken:** {r.get('action','-')}")
                defect_photos = normalize_photo_list(r.get("photos", r.get("photo")))
                fixed_photos = normalize_photo_list(r.get("fixed_photos", r.get("fixed_photo")))
                if defect_photos:
                    st.markdown("**QC Defect Photos**")
                    st.image([p for p in defect_photos if os.path.exists(p)], use_container_width=True)
                if fixed_photos:
                    st.markdown("**Worker Fixed Proof Photos**")
                    st.image([p for p in fixed_photos if os.path.exists(p)], use_container_width=True)
                st.divider()

        approval_photos = normalize_photo_list(job.get("qc_final_approval_photos", job.get("qc_final_approval_photo")))
        valid_approval = [p for p in approval_photos if os.path.exists(p)]
        if valid_approval:
            st.markdown("##### 🔍 QC Final Clearance Sign-Off")
            st.image(valid_approval, use_container_width=True)

        st.markdown("<div style='text-align:center;font-size:11px;color:#64748b;margin-top:25px;border-top:1px solid #cbd5e1;padding-top:12px;'>Trade Promoters Limited • Generator Installation &amp; QA/QC Division</div>", unsafe_allow_html=True)
        st.write("---")
        if st.button("⬅️ Back to Workshop Portal"):
            st.query_params.clear()
            st.rerun()
        st.stop()
    else:
        st.error(f"Certificate record for Job ID '{verify_id}' was not found.")
        if st.button("⬅️ Back to Portal"):
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
    title_style = ParagraphStyle("TStyle", parent=styles["Heading1"], alignment=1, textColor=colors.HexColor("#003366"), fontSize=17, spaceAfter=3)
    sub_style = ParagraphStyle("SStyle", parent=styles["Normal"], alignment=1, textColor=colors.HexColor("#555555"), fontSize=9, spaceAfter=12)
    cell_style = ParagraphStyle("CStyle", parent=styles["Normal"], fontSize=8.5, leading=11)
    header_cell = ParagraphStyle("HStyle", parent=styles["Normal"], fontSize=8.5, leading=11, fontName="Helvetica-Bold")

    elements.append(Paragraph("TRADE PROMOTERS LIMITED", title_style))
    elements.append(Paragraph("GENERATOR FABRICATION QA/QC CLEARANCE CERTIFICATE", sub_style))
    job_info = [
        [Paragraph(f"<b>Job ID:</b> {job.get('job_id','')}", cell_style), Paragraph(f"<b>Start Date/Time:</b> {job.get('start_time','')}", cell_style)],
        [Paragraph(f"<b>Fabrication Lead:</b> {job.get('worker','')}", cell_style), Paragraph(f"<b>Completed Time:</b> {job.get('completed_time','N/A')}", cell_style)]
    ]
    t1 = Table(job_info, colWidths=[270,270])
    t1.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor("#F4F6F8")),('PADDING',(0,0),(-1,-1),5),('GRID',(0,0),(-1,-1),0.5,colors.HexColor("#D2D6DC"))]))
    elements.append(t1); elements.append(Spacer(1,8))

    scope_info = [[Paragraph("<b>Job Scope / Fabrication Details:</b>", header_cell)], [Paragraph(job.get("desc",""), cell_style)]]
    t_scope = Table(scope_info, colWidths=[540])
    t_scope.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor("#E2E8F0")),('PADDING',(0,0),(-1,-1),5),('GRID',(0,0),(-1,-1),0.5,colors.HexColor("#E5E7EB"))]))
    elements.append(t_scope); elements.append(Spacer(1,8))

    rects = job.get("rectifications", [])
    if rects:
        rect_rows = [[Paragraph("<b>QC Rectification Audit Log &amp; Photo Proofs:</b>", header_cell)]]
        for i, r in enumerate(rects):
            rect_rows.append([Paragraph(f"<b>Issue #{i+1}:</b> {r.get('defect','')}<br/><b>Worker Action:</b> {r.get('action','')} - <font color='green'><b>[Fixed &amp; Cleared]</b></font>", cell_style)])
            defect_paths = [p for p in normalize_photo_list(r.get("photos", r.get("photo"))) if os.path.exists(p)]
            fixed_paths = [p for p in normalize_photo_list(r.get("fixed_photos", r.get("fixed_photo"))) if os.path.exists(p)]
            photo_cells = []
            if defect_paths:
                photo_cells.append(RLImage(defect_paths[0], width=130, height=95))
            else:
                photo_cells.append(Paragraph("No Defect Photo", cell_style))
            if fixed_paths:
                photo_cells.append(RLImage(fixed_paths[0], width=130, height=95))
            else:
                photo_cells.append(Paragraph("No Fixed Photo", cell_style))
            img_table = Table([[Paragraph("<b>QC Defect Photo:</b>",cell_style),Paragraph("<b>Worker Fixed Proof:</b>",cell_style)],photo_cells], colWidths=[260,260])
            img_table.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('PADDING',(0,0),(-1,-1),3)]))
            rect_rows.append([img_table])
        t2 = Table(rect_rows, colWidths=[540])
        t2.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor("#FEF3C7")),('PADDING',(0,0),(-1,-1),4),('GRID',(0,0),(-1,-1),0.5,colors.HexColor("#E5E7EB"))]))
        elements.append(t2); elements.append(Spacer(1,8))
    else:
        pass_table = Table([[Paragraph("<b>QC Inspection Status:</b>",header_cell)],[Paragraph("Clean pass. Inspected and approved to factory standards without defects.",cell_style)]], colWidths=[540])
        pass_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor("#DCFCE7")),('PADDING',(0,0),(-1,-1),4),('GRID',(0,0),(-1,-1),0.5,colors.HexColor("#E5E7EB"))]))
        elements.append(pass_table); elements.append(Spacer(1,8))

    approval_paths = [p for p in normalize_photo_list(job.get("qc_final_approval_photos", job.get("qc_final_approval_photo"))) if os.path.exists(p)]
    if approval_paths:
        try:
            qc_imgs = [RLImage(p, width=140, height=100) for p in approval_paths[:4]]
            qc_table = Table([[Paragraph("<b>QC Final Approval Sign-Off Photos:</b>",header_cell)],[qc_imgs]], colWidths=[540])
            qc_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor("#DCFCE7")),('ALIGN',(0,1),(-1,1),'CENTER'),('PADDING',(0,0),(-1,-1),4),('GRID',(0,0),(-1,-1),0.5,colors.HexColor("#E5E7EB"))]))
            elements.append(qc_table); elements.append(Spacer(1,8))
        except Exception:
            pass

    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(qr_link_url); qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buf = io.BytesIO(); qr_img.save(qr_buf, format="PNG"); qr_buf.seek(0)
    sig_info = [[RLImage(qr_buf,width=75,height=75), Paragraph("___________________________<br/><br/><b>Workshop Engineer</b>",cell_style), Paragraph("___________________________<br/><br/><b>Quality Engineer</b>",cell_style)]]
    t3 = Table(sig_info, colWidths=[120,210,210])
    t3.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'BOTTOM'),('ALIGN',(0,0),(-1,-1),'CENTER'),('PADDING',(0,0),(-1,-1),2)]))
    elements.append(KeepTogether(t3))
    doc.build(elements); buffer.seek(0)
    return buffer


def generate_qr_png(url):
    qr = qrcode.QRCode(box_size=5, border=2)
    qr.add_data(str(url).strip()); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return buf.getvalue()


# =======================================================
# 3. MAIN PORTAL
# =======================================================
st.title("⚡ TPL Generator Fabrication & QA/QC Portal")

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
            "record_id": make_record_id(),
            "job_id": new_job_id.strip(),
            "desc": new_desc.strip(),
            "worker": new_worker.strip(),
            "start_time": current_sl_time,
            "status": "In Progress",
            "rectifications": [],
            "qc_final_approval_photos": []
        })
        save_data(st.session_state.jobs_db)
        st.success(f"Job {new_job_id} assigned successfully!")
        st.rerun()

st.write("---")
st.subheader("2. Ongoing Fabrication & QC Inspection Pipeline")
active_jobs = [j for j in st.session_state.jobs_db if j.get("status") != "Completed"]

if not active_jobs:
    st.info("No active jobs currently in progress.")
else:
    for a_idx, job in enumerate(active_jobs):
        migrate_job(job)
        record_id = job["record_id"]
        rects = job.get("rectifications", [])
        all_worker_fixed = all(r.get("worker_done", False) for r in rects)
        approval_paths = normalize_photo_list(job.get("qc_final_approval_photos", []))
        qc_photo_uploaded = any(os.path.exists(p) for p in approval_paths)
        status_icon = "🟢" if (all_worker_fixed and qc_photo_uploaded) else ("🔴" if rects and not all_worker_fixed else "🟡")

        with st.expander(f"{status_icon} {job.get('job_id','')} - {job.get('worker','')} [{job.get('status','In Progress')}]"):
            st.write(f"**Description:** {job.get('desc','')}")
            st.caption(f"Started: {job.get('start_time','')}")

            if rects:
                st.markdown("#### ⚠️ QC Rectification Issues:")
                for idx, r in enumerate(rects):
                    st.markdown(f"**Defect #{idx+1}:** {r.get('defect','')} *(Logged: {r.get('time','N/A')})*")
                    defect_paths = normalize_photo_list(r.get("photos", r.get("photo")))
                    if defect_paths:
                        st.markdown("**QC Defect Photos**")
                        changed = photo_columns(defect_paths, f"defect_{record_id}_{idx}", width=170)
                        if changed:
                            r["photos"] = defect_paths
                            save_data(st.session_state.jobs_db)
                            st.rerun()

                    col_w1, col_w2 = st.columns(2)
                    with col_w1:
                        w_tick = st.checkbox(f"Worker: Completed / Fixed #{idx+1}", value=r.get("worker_done",False), key=f"w_chk_{record_id}_{idx}")
                        action_txt = st.text_input(f"Action Taken #{idx+1}", value=r.get("action",""), key=f"act_{record_id}_{idx}", placeholder="e.g. Re-welded and ground smooth")
                        r["worker_done"] = w_tick
                        r["action"] = action_txt
                    with col_w2:
                        fixed_paths = normalize_photo_list(r.get("fixed_photos", r.get("fixed_photo")))
                        if fixed_paths:
                            st.markdown("**Worker Fixed Proof Photos**")
                            changed = photo_columns(fixed_paths, f"fixed_{record_id}_{idx}", width=130)
                            if changed:
                                r["fixed_photos"] = fixed_paths
                                save_data(st.session_state.jobs_db)
                                st.rerun()
                        fixed_uploader_id = f"fixed_img_{record_id}_{idx}"
                        new_fixed = st.file_uploader(
                            f"Upload Fixed Photo(s) #{idx+1} (Optional)",
                            type=["jpg","jpeg","png"],
                            accept_multiple_files=True,
                            key=f"{fixed_uploader_id}_v{uploader_version(fixed_uploader_id)}"
                        )
                        if new_fixed:
                            added_count = 0
                            for uploaded in new_fixed:
                                path = save_uploaded_file(uploaded, f"{record_id}_fixed_{idx+1}")
                                fixed_paths.append(path)
                                added_count += 1
                            r["fixed_photos"] = fixed_paths
                            save_data(st.session_state.jobs_db)
                            bump_uploader_version(fixed_uploader_id)
                            st.success(f"{added_count} fixed photo(s) attached successfully. You can upload more photos.")
                            st.rerun()
                    st.divider()
                save_data(st.session_state.jobs_db)
            else:
                st.success("No defects logged yet. Work progressing normally.")

            st.markdown("#### 🔍 QC Inspector: Log Comment / Defect for this Job")
            with st.form(f"qc_add_defect_{record_id}", clear_on_submit=True):
                defect_text = st.text_area("Defect / Rectification Note", placeholder="Describe issue: weld gap, misaligned holes, paint run...", key=f"def_txt_{record_id}")
                photo_files = st.file_uploader(
                    "Upload Inspection / Defect Photo(s) (Optional)",
                    type=["jpg","jpeg","png"],
                    accept_multiple_files=True,
                    key=f"def_img_{record_id}"
                )
                st.caption("You can select multiple photos at once. Photos are saved only after submitting this rectification issue.")
                add_defect_btn = st.form_submit_button("➕ Submit Rectification Issue")
                if add_defect_btn and defect_text:
                    photo_paths = []
                    for uploaded in (photo_files or []):
                        photo_paths.append(save_uploaded_file(uploaded, f"{record_id}_defect_{len(rects)+1}"))
                    job["rectifications"].append({
                        "defect": defect_text.strip(),
                        "photos": photo_paths,
                        "fixed_photos": [],
                        "worker_done": False,
                        "action": "",
                        "time": get_sl_time()
                    })
                    job["status"] = "Needs Rectification"
                    save_data(st.session_state.jobs_db)
                    st.success(f"Rectification issue added to {job.get('job_id')}!")
                    st.rerun()

            st.write("---")
            st.markdown("#### 🛡️ QC Final Clearance Photo(s) (Required for Job Completion)")
            approval_paths = normalize_photo_list(job.get("qc_final_approval_photos", job.get("qc_final_approval_photo")))
            if approval_paths:
                changed = photo_columns(approval_paths, f"approval_{record_id}", width=180)
                if changed:
                    job["qc_final_approval_photos"] = approval_paths
                    save_data(st.session_state.jobs_db)
                    st.rerun()

            approval_uploader_id = f"qc_appr_{record_id}"
            qc_appr_files = st.file_uploader(
                f"📸 Upload QC Approval Photo(s) / Sign ({job.get('job_id')})",
                type=["jpg","jpeg","png"],
                accept_multiple_files=True,
                key=f"{approval_uploader_id}_v{uploader_version(approval_uploader_id)}"
            )
            if qc_appr_files:
                added_count = 0
                for uploaded in qc_appr_files:
                    approval_paths.append(save_uploaded_file(uploaded, f"{record_id}_qc_approval"))
                    added_count += 1
                job["qc_final_approval_photos"] = approval_paths
                save_data(st.session_state.jobs_db)
                bump_uploader_version(approval_uploader_id)
                st.success(f"{added_count} QC approval photo(s) attached successfully. You can upload more photos.")
                st.rerun()

            if approval_paths:
                st.caption(f"{len(approval_paths)} QC approval photo(s) saved.")

            st.write("---")
            can_complete = all_worker_fixed and any(os.path.exists(p) for p in approval_paths)
            if not can_complete:
                missing_items = []
                if not all_worker_fixed:
                    missing_items.append("Worker must mark all defects as Fixed")
                if not any(os.path.exists(p) for p in approval_paths):
                    missing_items.append("QC Approval Photo must be uploaded")
                st.warning(f"🔒 Completion Locked: {', and '.join(missing_items)}.")
                st.checkbox(f"✅ Mark Job as COMPLETED ({job.get('job_id')})", disabled=True, key=f"dis_comp_{record_id}")
                st.button(f"Submit Final Job ({job.get('job_id')})", disabled=True, key=f"dis_btn_{record_id}")
            else:
                is_comp = st.checkbox(f"✅ Mark Job as COMPLETED ({job.get('job_id')})", key=f"comp_{record_id}")
                if st.button(f"Submit Final Job ({job.get('job_id')})", key=f"sub_{record_id}"):
                    if is_comp:
                        job["status"] = "Completed"
                        job["completed_time"] = get_sl_time()
                        save_data(st.session_state.jobs_db)
                        st.success(f"Job {job.get('job_id')} COMPLETED successfully!")
                        st.rerun()
                    else:
                        st.warning("Please tick the completion checkbox above before submitting.")

            st.write("---")
            act_del_key = f"active_{record_id}"
            if st.session_state.delete_confirm_id == act_del_key:
                st.error(f"⚠️ Are you sure you want to delete ongoing job **{job.get('job_id')}**?")
                conf_c1, conf_c2 = st.columns(2)
                with conf_c1:
                    if st.button("Yes, Delete Job", key=f"act_yes_{record_id}"):
                        for r in job.get("rectifications", []):
                            for p in normalize_photo_list(r.get("photos", [])) + normalize_photo_list(r.get("fixed_photos", [])):
                                safe_remove_file(p)
                        for p in normalize_photo_list(job.get("qc_final_approval_photos", [])):
                            safe_remove_file(p)
                        st.session_state.jobs_db = [j for j in st.session_state.jobs_db if j.get("record_id") != record_id]
                        save_data(st.session_state.jobs_db)
                        st.session_state.delete_confirm_id = None
                        st.success(f"Job {job.get('job_id')} permanently deleted!")
                        st.rerun()
                with conf_c2:
                    if st.button("No, Cancel", key=f"act_no_{record_id}"):
                        st.session_state.delete_confirm_id = None
                        st.rerun()
            else:
                if st.button(f"🗑️ Delete This Job ({job.get('job_id')})", key=f"act_del_btn_{record_id}"):
                    st.session_state.delete_confirm_id = act_del_key
                    st.rerun()

# =======================================================
# 4. COMPLETED JOBS ARCHIVE
# =======================================================
st.write("---")
st.subheader("3. Completed Jobs Archive")
completed_jobs = [j for j in st.session_state.jobs_db if j.get("status") == "Completed"]

if not completed_jobs:
    st.caption("No completed jobs yet.")
else:
    for c_idx, c_job in enumerate(completed_jobs):
        migrate_job(c_job)
        record_id = c_job["record_id"]
        c_rects = c_job.get("rectifications", [])
        with st.expander(f"🟢 {c_job.get('job_id','')} - {c_job.get('worker','')} (COMPLETED)"):
            st.write(f"**Description:** {c_job.get('desc','')}")
            st.write(f"**Completed At:** {c_job.get('completed_time','N/A')}")
            st.write(f"**Rectifications Cleared:** {len(c_rects)} items.")

            direct_qr_url = f"{PUBLIC_DOMAIN}/?verify_job={record_id}"
            st.write("---")
            st.markdown("#### 📱 Digital Certificate QR Code:")
            qr_bytes = generate_qr_png(direct_qr_url)
            qr_col1, qr_col2 = st.columns([1,2])
            with qr_col1:
                st.image(qr_bytes, width=150, caption=f"Scan to Verify {c_job.get('job_id')}")
            with qr_col2:
                st.info("💡 Scan with any smartphone camera to open the authenticated certificate.")
                st.download_button(label="📥 Download QR Code (PNG)", data=qr_bytes, file_name=f"TPL_{c_job.get('job_id')}_QR.png", mime="image/png", key=f"qr_dl_{record_id}_{c_idx}")

            st.write("---")
            btn_col1, btn_col2, btn_col3 = st.columns([1.2,1.5,1])
            with btn_col1:
                if st.button("👁️ View Certificate", key=f"view_{record_id}_{c_idx}"):
                    st.query_params["verify_job"] = record_id
                    st.rerun()
            with btn_col2:
                pdf_bytes = create_pdf(c_job, direct_qr_url)
                st.download_button(label="📄 Print PDF Certificate", data=pdf_bytes, file_name=f"TPL_{c_job.get('job_id')}_Certificate.pdf", mime="application/pdf", key=f"dl_{record_id}_{c_idx}")
            with btn_col3:
                comp_del_key = f"completed_{record_id}"
                if st.button("🗑️ Delete", key=f"del_btn_{record_id}_{c_idx}"):
                    st.session_state.delete_confirm_id = comp_del_key
                    st.rerun()

            if st.session_state.delete_confirm_id == f"completed_{record_id}":
                st.write("")
                st.error(f"⚠️ Are you sure you want to delete completed record **{c_job.get('job_id')}**?")
                conf_c1, conf_c2 = st.columns(2)
                with conf_c1:
                    if st.button("Yes, Delete Record", key=f"comp_yes_{record_id}"):
                        for r in c_job.get("rectifications", []):
                            for p in normalize_photo_list(r.get("photos", [])) + normalize_photo_list(r.get("fixed_photos", [])):
                                safe_remove_file(p)
                        for p in normalize_photo_list(c_job.get("qc_final_approval_photos", [])):
                            safe_remove_file(p)
                        st.session_state.jobs_db = [j for j in st.session_state.jobs_db if j.get("record_id") != record_id]
                        save_data(st.session_state.jobs_db)
                        st.session_state.delete_confirm_id = None
                        st.success(f"Job {c_job.get('job_id')} permanently deleted!")
                        st.rerun()
                with conf_c2:
                    if st.button("No, Cancel", key=f"comp_no_{record_id}"):
                        st.session_state.delete_confirm_id = None
                        st.rerun()

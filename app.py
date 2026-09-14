import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
import sqlite3
import hashlib
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="TPL QA/QC Tracker", layout="centered", page_icon="⚡")

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
DB_PATH = "tpl_jobs.db"
PHOTO_DIR = "qc_photos"
os.makedirs(PHOTO_DIR, exist_ok=True)

# Simple credential store: username -> sha256(password)
# Change these before real use, or better, move to st.secrets["users"]
USERS = {
    "admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "qc": hashlib.sha256("qc123".encode()).hexdigest(),
}

# ------------------------------------------------------------------
# 1. DATABASE LAYER (SQLite -> fixes "no persistence" + gives basic
#    write locking for free, since SQLite serializes writes)
# ------------------------------------------------------------------
def get_conn():
    # timeout lets a second writer wait instead of instantly failing
    # if another session is mid-write (basic concurrency safety)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")  # better concurrent read/write
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            desc TEXT,
            worker TEXT,
            start_time TEXT,
            status TEXT,
            qc_defect TEXT,
            rectification TEXT,
            qc_photo_path TEXT,
            updated_by TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def seed_if_empty():
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as c FROM jobs").fetchone()
    if row["c"] == 0:
        conn.execute("""
            INSERT INTO jobs (job_id, desc, worker, start_time, status,
                               qc_defect, rectification, qc_photo_path,
                               updated_by, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "TPL-GEN-001",
            "Soundproof canopy sheet bending & box frame welding (250kVA)",
            "Kamal Perera",
            "2026-09-14 08:30 AM",
            "In Progress",
            "Minor gap on bottom seam",
            "Re-welded & ground smooth",
            None,
            "system",
            datetime.now().isoformat(timespec="seconds"),
        ))
        conn.commit()
    conn.close()


def add_job(job_id, desc, worker, start_time, user):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO jobs (job_id, desc, worker, start_time, status,
                               qc_defect, rectification, qc_photo_path,
                               updated_by, updated_at)
            VALUES (?, ?, ?, ?, 'In Progress', '', '', NULL, ?, ?)
        """, (job_id, desc, worker, start_time, user,
              datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, "Job ID already exists. Choose a unique Job ID."
    finally:
        conn.close()


def get_jobs(status_filter=None):
    conn = get_conn()
    if status_filter == "active":
        rows = conn.execute("SELECT * FROM jobs WHERE status != 'Completed'").fetchall()
    elif status_filter == "completed":
        rows = conn.execute("SELECT * FROM jobs WHERE status = 'Completed'").fetchall()
    else:
        rows = conn.execute("SELECT * FROM jobs").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_job(job_id, qc_defect, rectification, photo_path, status, user):
    conn = get_conn()
    conn.execute("""
        UPDATE jobs
        SET qc_defect = ?, rectification = ?, qc_photo_path = COALESCE(?, qc_photo_path),
            status = ?, updated_by = ?, updated_at = ?
        WHERE job_id = ?
    """, (qc_defect, rectification, photo_path, status, user,
          datetime.now().isoformat(timespec="seconds"), job_id))
    conn.commit()
    conn.close()


init_db()
seed_if_empty()

# ------------------------------------------------------------------
# 2. AUTHENTICATION (fixes "anyone can edit anything")
# ------------------------------------------------------------------
def login_screen():
    st.title(" ⚡TPL QA/QC Tracker — Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            hashed = hashlib.sha256(password.encode()).hexdigest()
            if username in USERS and USERS[username] == hashed:
                st.session_state.auth_user = username
                st.rerun()
            else:
                st.error("Invalid username or password.")


if "auth_user" not in st.session_state:
    login_screen()
    st.stop()

current_user = st.session_state.auth_user

# ------------------------------------------------------------------
# 3. PDF GENERATOR (now embeds the actual QC defect photo, if any)
# ------------------------------------------------------------------
def create_pdf(job):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], alignment=1,
        textColor=colors.HexColor("#003366"), fontSize=18, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        'Sub', parent=styles['Normal'], alignment=1,
        textColor=colors.HexColor("#555555"), fontSize=11, spaceAfter=15
    )

    elements.append(Paragraph("TRADE PROMOTERS LIMITED", title_style))
    elements.append(Paragraph("GENERATOR FABRICATION & QA/QC CLEARANCE CERTIFICATE", sub_style))

    job_info = [
        [Paragraph(f"<b>Job ID:</b> {job['job_id']}", styles['Normal']),
         Paragraph(f"<b>Start Date/Time:</b> {job['start_time']}", styles['Normal'])],
        [Paragraph(f"<b>Assigned Employee:</b> {job['worker']}", styles['Normal']),
         Paragraph("<b>Status:</b> <font color='green'><b>COMPLETED</b></font>", styles['Normal'])]
    ]
    t1 = Table(job_info, colWidths=[270, 270])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F4F6F8")),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D2D6DC"))
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 12))

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
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor("#FEF3C7")),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor("#DCFCE7")),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB"))
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 15))

    # Embed the actual defect photo if one was uploaded and saved to disk
    photo_path = job.get("qc_photo_path")
    if photo_path and os.path.exists(photo_path):
        elements.append(Paragraph("<b>QC Defect Photo:</b>", styles['Normal']))
        elements.append(Spacer(1, 6))
        elements.append(RLImage(photo_path, width=220, height=165))
        elements.append(Spacer(1, 15))

    # QR Code
    qr_data = f"TPL QUALITY VERIFIED\nJob ID: {job['job_id']}\nWorker: {job['worker']}\nStatus: COMPLETED\nRectification: {job['rectification']}"
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

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


# ------------------------------------------------------------------
# 4. APP INTERFACE
# ------------------------------------------------------------------
top_left, top_right = st.columns([4, 1])
with top_left:
    st.title("⚡ TPL Fabrication QA/QC System")
with top_right:
    st.write("")
    st.caption(f"👤 {current_user}")
    if st.button("Logout"):
        del st.session_state.auth_user
        st.rerun()

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
                ok, err = add_job(job_id, desc, worker, start_time, current_user)
                if ok:
                    st.success(f"Job {job_id} assigned successfully!")
                else:
                    st.error(err)
            else:
                st.error("Please fill in Job ID, Description, and Employee Name.")

# TAB 2: QC INSPECTION & RECTIFICATION
with tab2:
    st.subheader("QC Inspection & Rectification")

    active_jobs = get_jobs("active")

    if not active_jobs:
        st.info("No ongoing jobs found.")
    else:
        job_options = [j["job_id"] for j in active_jobs]
        selected_id = st.selectbox("Select Active Job ID", job_options)
        job = next(j for j in active_jobs if j["job_id"] == selected_id)

        st.markdown(f"**Description:** {job['desc']}")
        st.markdown(f"**Employee:** {job['worker']} | **Started:** {job['start_time']}")
        st.caption(f"Last updated by {job['updated_by']} at {job['updated_at']}")

        st.write("---")
        st.markdown("#### 1. QC Defect / Issue Logging")
        qc_note = st.text_area("QC Defect / Rectification Note", value=job["qc_defect"] or "",
                                placeholder="Type any issues found during inspection...")
        uploaded_photo = st.file_uploader("Upload QC Defect Photo", type=["jpg", "jpeg", "png"])

        new_photo_path = None
        if uploaded_photo:
            # Persist the photo to disk so it survives restarts and can go into the PDF
            ext = os.path.splitext(uploaded_photo.name)[1] or ".png"
            new_photo_path = os.path.join(PHOTO_DIR, f"{selected_id}{ext}")
            with open(new_photo_path, "wb") as f:
                f.write(uploaded_photo.getbuffer())
            st.image(uploaded_photo, caption="Uploaded Defect Photo (will be saved on update)", width=250)
        elif job["qc_photo_path"] and os.path.exists(job["qc_photo_path"]):
            st.image(job["qc_photo_path"], caption="Currently saved defect photo", width=250)

        st.write("---")
        st.markdown("#### 2. Rectification Action Taken")
        rect_note = st.text_area("How defect was rectified", value=job["rectification"] or "",
                                  placeholder="Explain how the issues were resolved...")

        is_completed = st.checkbox("✅ All Work & Rectifications Completed (Mark as Completed)",
                                    value=(job["status"] == "Completed"))

        if st.button("Update Job Status"):
            new_status = "Completed" if is_completed else ("Needs Rectification" if qc_note else "In Progress")
            update_job(selected_id, qc_note, rect_note, new_photo_path, new_status, current_user)
            if is_completed:
                st.success(f"{selected_id} marked as Completed! Go to the 'Completed / Print PDF' tab to download Certificate.")
            else:
                st.warning(f"{selected_id} updated. Current status: {new_status}")
            st.rerun()

# TAB 3: COMPLETED JOBS & PRINT PDF
with tab3:
    st.subheader("Completed Jobs & PDF Verification")

    completed_jobs = get_jobs("completed")

    if not completed_jobs:
        st.info("No completed jobs yet. Complete a job from Tab 2 to generate certificates.")
    else:
        for c_job in completed_jobs:
            with st.expander(f"🟢 {c_job['job_id']} - {c_job['worker']} (COMPLETED)"):
                st.write(f"**Scope:** {c_job['desc']}")
                st.write(f"**Rectification Done:** {c_job['rectification']}")

                if c_job["qc_photo_path"] and os.path.exists(c_job["qc_photo_path"]):
                    st.image(c_job["qc_photo_path"], caption="QC Defect Photo", width=200)

                qr = qrcode.QRCode(box_size=3, border=1)
                qr.add_data(f"TPL Job: {c_job['job_id']} | Status: Completed")
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                img_byte_arr = io.BytesIO()
                qr_img.save(img_byte_arr, format='PNG')
                st.image(img_byte_arr.getvalue(), caption=f"Scan to Verify {c_job['job_id']}", width=120)

                pdf_bytes = create_pdf(c_job)
                st.download_button(
                    label=f"📄 Download / Print PDF Certificate ({c_job['job_id']})",
                    data=pdf_bytes,
                    file_name=f"TPL_Certificate_{c_job['job_id']}.pdf",
                    mime="application/pdf",
                    key=f"dl_{c_job['job_id']}"
                )

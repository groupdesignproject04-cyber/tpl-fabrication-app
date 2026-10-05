import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import io
import os
import json
import uuid
from html import escape
import qrcode
import requests

from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from supabase import create_client


# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="TPL QA/QC Fabrication System",
    layout="centered",
    page_icon="âš¡"
)


# ==========================================================
# SUPABASE CONFIGURATION
# ==========================================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

except Exception as e:
    st.error(
        "âŒ Supabase connection failed.\n\n"
        "Please check SUPABASE_URL and SUPABASE_KEY "
        "inside Streamlit Cloud â†’ Settings â†’ Secrets."
    )
    st.stop()


JOBS_TABLE = "tpl_jobs"
PHOTO_BUCKET = "tpl-photos"

# IMPORTANT: Existing tpl_jobs/job_data records are preserved.
# This update adds a separate notifications table only; it does not
# replace or migrate existing job records.

PUBLIC_DOMAIN = "https://tpl-fabrication-app-evtpzepaiqfnt5gkqh8brx.streamlit.app"


# ==========================================================
# LOGIN CREDENTIALS
# ==========================================================

USERS = {
    # Existing editor account is retained as Admin so the existing
    # login/password continues to work.
    "tpl_e": {
        "password": "E112233",
        "role": "admin"
    },

    "tpl_qc": {
        "password": "QC0000",
        "role": "qc"
    },

    "tpl_v": {
        "password": "V0000",
        "role": "viewer"
    },
}

NOTIFICATIONS_TABLE = "notifications"


# ==========================================================
# TIME
# ==========================================================

def get_sl_time():

    sl_tz = pytz.timezone("Asia/Colombo")

    return datetime.now(sl_tz).strftime(
        "%Y-%m-%d %I:%M %p"
    )


# ==========================================================
# RECORD ID
# ==========================================================

def make_record_id():

    return f"REC-{uuid.uuid4().hex[:12].upper()}"


# ==========================================================
# PHOTO LIST NORMALIZATION
# ==========================================================

def normalize_photo_list(value):

    if not value:
        return []

    if isinstance(value, list):
        return [
            str(x)
            for x in value
            if x
        ]

    return [str(value)]


# ==========================================================
# JOB MIGRATION / DEFAULT VALUES
# ==========================================================

def migrate_job(j):

    if not j.get("record_id"):
        j["record_id"] = make_record_id()

    if (
        "rectifications" not in j
        or not isinstance(j.get("rectifications"), list)
    ):
        j["rectifications"] = []

    if "status" not in j:
        j["status"] = "In Progress"

    if not j.get("start_time"):
        j["start_time"] = get_sl_time()

    for r in j["rectifications"]:

        if "photos" not in r:

            r["photos"] = normalize_photo_list(
                r.get("photo")
            )

        if "fixed_photos" not in r:

            r["fixed_photos"] = normalize_photo_list(
                r.get("fixed_photo")
            )

        r.setdefault(
            "worker_done",
            False
        )

        r.setdefault(
            "action",
            ""
        )

        r.setdefault(
            "time",
            "N/A"
    )

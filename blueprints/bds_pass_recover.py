import os, uuid, json, re
import pandas as pd
from flask import Blueprint, request, render_template, jsonify, Response, send_file, session, redirect, url_for
from docx import Document
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

bds_pass_recover_bp = Blueprint("bds_pass_recover", __name__)

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# ✅ Dashboard Integration

def get_bds_pass():
    return ["BDSPASS-1234", "BDSPASS-5678"]

@bds_pass_recover_bp.route("/bds_pass_recover")
def index():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    return render_template("pages/bds_pass_recover.html", results=get_bds_pass())

@bds_pass_recover_bp.route("/bds_pass_recover/upload", methods=["POST"])
def upload():
    file = request.files.get("input_file")
    if not file or file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400

    file_ext = file.filename.rsplit(".", 1)[-1].lower()
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    if file_ext in ["xlsx", "xls"]:
        df = pd.read_excel(file_path)
        return jsonify({"type": "excel", "file_path": file_path, "columns": df.columns.tolist()})
    elif file_ext == "docx":
        return jsonify({"type": "docx", "file_path": file_path})
    else:
        return jsonify({"error": "Unsupported file type"}), 400

@bds_pass_recover_bp.route("/bds_pass_recover/process")
def process():
    file_path = request.args.get("file_path")
    user_col = request.args.get("user_col")
    mobile_col = request.args.get("mobile_col")
    return Response(generate(file_path, user_col, mobile_col), mimetype="text/event-stream")

@bds_pass_recover_bp.route("/bds_pass_recover/download")
def download():
    path = request.args.get("path")
    if not path:
        return "Missing file path", 400

    safe_path = os.path.join(os.getcwd(), path.replace("/", os.sep))
    if not os.path.exists(safe_path):
        return "File not found", 404

    return send_file(safe_path, as_attachment=True)

def generate(file_path, user_col=None, mobile_col=None):
    ext = file_path.rsplit(".", 1)[-1].lower()

    if ext == "docx":
        doc = Document(file_path)
        data = [[cell.text.strip() for cell in row.cells] for table in doc.tables for row in table.rows]
        if not data:
            yield f"data: {json.dumps({'error': 'Empty file'})}\n\n"
            return
        df = pd.DataFrame(data[1:], columns=data[0])
        user_col = "USER_ID"
        mobile_col = "Mobile Number"
    else:
        df = pd.read_excel(file_path)

    total_rows = len(df)
    yield f"data: {json.dumps({'total_rows': total_rows})}\n\n"

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    form_url = "http://dgme.teletalk.com.bd/bds/options/getpass.php"

    results = []
    processed = 0
    not_found = 0
    error_count = 0
    found_count = 0

    for _, row in df.iterrows():
        try:
            driver.get(form_url)
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "inv"))).send_keys(str(row[user_col]))

            mobile = str(row[mobile_col]).strip()
            if not mobile.startswith("0"):
                mobile = "0" + mobile

            driver.find_element(By.ID, "smobile").send_keys(mobile)
            driver.find_element(By.ID, "button01").click()
            result = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, "(//span[@class='red12bold'])[2]"))
            ).text.strip()

            result_lower = result.lower()
            if "sorry" in result_lower:
                status = "not_found"
                not_found += 1
            elif "fail" in result_lower or "error" in result_lower:
                status = "error"
                error_count += 1
            elif re.match(r"^[A-Z]{10}$", result):
                status = "found"
                found_count += 1
            else:
                status = "found"
                found_count += 1

        except Exception:
            result = "Sorry, User ID not found!!"
            status = "error"
            error_count += 1

        processed += 1

        result_obj = {
            "User ID": row[user_col],
            "Mobile Number": mobile,
            "Result": result,
            "Status": status,
            "Processed": processed,
            "NotFound": not_found,
            "ErrorCount": error_count,
            "Found": found_count
        }

        results.append(result_obj)
        yield f"data: {json.dumps(result_obj)}\n\n"

    driver.quit()

    df_result = pd.DataFrame(results)
    out_path = os.path.join(RESULT_FOLDER, f"result_{uuid.uuid4().hex}.xlsx")
    df_result.to_excel(out_path, index=False)

    download_url = "/bds_pass_recover/download?path=" + out_path.replace("\\", "/")
    yield f"data: {json.dumps({'download': download_url})}\n\n"

# blueprints/mbbs_user_id.py
import os, uuid, json
import pandas as pd
from flask import Blueprint, request, render_template, jsonify, send_file, Response, session, redirect, url_for
from docx import Document
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

mbbs_user_id_bp = Blueprint("mbbs_user_id_bp", __name__)

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@mbbs_user_id_bp.route("/mbbs_user_id")
def index():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    return render_template("pages/mbbs_user_id.html", ids=get_mbbs_ids())

@mbbs_user_id_bp.route("/mbbs_user_id/upload", methods=["POST"])
def upload():
    if "input_file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["input_file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    file_ext = file.filename.rsplit('.', 1)[-1].lower()
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    if file_ext in ["xlsx", "xls"]:
        df = pd.read_excel(file_path)
        columns = df.columns.tolist()
        return jsonify({"type": "excel", "file_path": file_path, "columns": columns})
    elif file_ext == "docx":
        return jsonify({"type": "docx", "file_path": file_path})
    else:
        return jsonify({"error": "Unsupported file type"}), 400

@mbbs_user_id_bp.route("/mbbs_user_id/process")
def process():
    file_path = request.args.get("file_path")
    name_col = request.args.get("name_col")
    father_col = request.args.get("father_col")
    mobile_col = request.args.get("mobile_col")

    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 400

    return Response(generate(file_path, name_col, father_col, mobile_col), mimetype="text/event-stream")

def generate(file_path, name_col=None, father_col=None, mobile_col=None):
    ext = file_path.rsplit(".", 1)[-1].lower()
    if ext == "docx":
        doc = Document(file_path)
        data = []
        for table in doc.tables:
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                data.append(row_data)
        if not data or len(data) < 2:
            yield f"data: {json.dumps({'error': 'No data found in the document'})}\n\n"
            return
        df = pd.DataFrame(data[1:], columns=data[0])
        name_col, father_col, mobile_col = "Name", "Father's Name", "Mobile Number"
    else:
        df = pd.read_excel(file_path)
        if not all([name_col, father_col, mobile_col]):
            yield f"data: {json.dumps({'error': 'Missing column selections'})}\n\n"
            return

    total_rows = len(df)
    yield f"data: {json.dumps({'total_rows': total_rows})}\n\n"

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    form_url = "http://dgme.teletalk.com.bd/mbbs/options/getinvoice.php"
    results = df.copy()
    results["MBBS User ID"] = ""

    processed = 0
    not_found = 0
    error_count = 0

    for idx, row in df.iterrows():
        driver.get(form_url)
        try:
            name = str(row[name_col])
            father = str(row[father_col])
            mobile = str(row[mobile_col]).strip()
            if not mobile.startswith("0"):
                mobile = "0" + mobile

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "sname"))).send_keys(name)
            driver.find_element(By.ID, "sfather").send_keys(father)
            driver.find_element(By.ID, "smobile").send_keys(mobile)
            driver.find_element(By.ID, "button01").click()
            result = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "red12bold"))
            ).text
            if "Sorry, User ID not found" in result:
                not_found += 1
        except Exception as e:
            result = f"Failed: {str(e)}"
            error_count += 1

        results.at[idx, "MBBS User ID"] = result
        processed += 1

        res_data = {
            "Name": name,
            "Father's Name": father,
            "Mobile Number": mobile,
            "MBBS User ID": result,
            "Processed": processed,
            "Total": total_rows,
            "NotFound": not_found,
            "ErrorCount": error_count
        }
        yield f"data: {json.dumps(res_data)}\n\n"

    driver.quit()
    result_filename = f"Live_Result_{uuid.uuid4().hex}.xlsx"
    result_path = os.path.join(RESULT_FOLDER, result_filename)
    results.to_excel(result_path, index=False)

    download_url = f"/mbbs_user_id/download?file={result_filename}"
    yield f"data: {json.dumps({'download': download_url, 'total_rows': total_rows, 'processed': processed, 'not_found': not_found, 'error_count': error_count})}\n\n"

@mbbs_user_id_bp.route("/mbbs_user_id/download")
def download():
    filename = request.args.get("file")
    if not filename:
        return "File parameter missing", 400
    path = os.path.abspath(os.path.join(RESULT_FOLDER, filename))
    result_dir = os.path.abspath(RESULT_FOLDER)
    if not path.startswith(result_dir):
        return "Invalid file path", 403
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return f"File not found: {filename}", 404

# ✅ Used for dynamic content loading in dashboard

def get_mbbs_ids():
    return ["MBBS1001", "MBBS1002", "MBBS1003"]
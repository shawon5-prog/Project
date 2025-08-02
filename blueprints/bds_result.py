import os, uuid, json
import pandas as pd
from flask import Blueprint, request, render_template, Response, send_file, jsonify, session, redirect, url_for
from docx import Document
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

bds_result_bp = Blueprint('bds_result', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "uploads")
RESULT_FOLDER = os.path.join(BASE_DIR, "..", "results")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# ✅ Dashboard SPA View Loader
@bds_result_bp.route("/bds_result")
def index():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    return render_template("pages/bds_result.html", results=get_bds_results())

# ✅ Dummy data used for initial SPA view (can be removed)
def get_bds_results():
    return [
        {"BDS_Roll": "112233", "Student Name": "Ayesha Akter", "Merit Score": "88"},
        {"BDS_Roll": "445566", "Student Name": "Tanvir Rahman", "Merit Score": "85"}
    ]

# ✅ Upload DOCX/Excel File
@bds_result_bp.route("/bds_result/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower()
    uid = uuid.uuid4().hex
    filename = f"{uid}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    if ext in ["xlsx", "xls"]:
        df = pd.read_excel(file_path)
        return jsonify({
            "type": "excel",
            "file_path": file_path,
            "columns": df.columns.tolist()
        })
    elif ext == "docx":
        return jsonify({"type": "docx", "file_path": file_path})
    else:
        return jsonify({"error": "Unsupported file type"}), 400

# ✅ SSE Result Processor
@bds_result_bp.route("/bds_result/process")
def process():
    file_path = request.args.get("file_path")
    roll_col = request.args.get("roll_col", "BDS_Roll")
    if not os.path.exists(file_path):
        return "File not found", 404
    return Response(generate_result(file_path, roll_col), mimetype="text/event-stream")

# ✅ Core Result Generation Logic using Selenium
def generate_result(file_path, roll_col):
    ext = file_path.rsplit(".", 1)[-1].lower()

    if ext == "docx":
        doc = Document(file_path)
        rows = [[cell.text.strip() for cell in row.cells] for table in doc.tables for row in table.rows]
        if len(rows) < 2:
            yield f"data: {json.dumps({'error': 'Invalid DOCX structure'})}\n\n"
            return
        df = pd.DataFrame(rows[1:], columns=rows[0])
    else:
        df = pd.read_excel(file_path)

    if roll_col not in df.columns:
        yield f"data: {json.dumps({'error': 'Invalid column'})}\n\n"
        return

    total = len(df)
    yield f"data: {json.dumps({'total_rows': total})}\n\n"

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    result_data = []

    for idx, row in df.iterrows():
        roll = str(row[roll_col]).strip()
        driver.get("https://result.dghs.gov.bd/bds/")
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "roll2"))).send_keys(roll)
            driver.find_element(By.CLASS_NAME, "search_btn").click()
            elements = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "stones")))
            results = [el.text for el in elements]
        except Exception as e:
            results = [f"Error: {str(e)}"]

        if not results:
            results = ["Result not found"]

        entry = {"BDS_Roll": roll}
        for i, r in enumerate(results):
            entry[f"Result_{i+1}"] = r
        result_data.append(entry)

        yield f"data: {json.dumps(entry)}\n\n"

    driver.quit()

    # ✅ Optional Result Column Rename Mapping
    rename_map = {
        "Result_1": "Roll No",
        "Result_2": "Student Name",
        "Result_3": "Test Score",
        "Result_4": "Merit Score",
        "Result_5": "Merit Position",
        "Result_6": "Allotted College Code",
        "Result_7": "Status"
    }

    final_df = df.copy()
    for entry in result_data:
        mask = final_df[roll_col].astype(str).str.strip() == entry["BDS_Roll"]
        for key, val in entry.items():
            if key != "BDS_Roll":
                final_df.loc[mask, key] = val

    final_df.rename(columns=rename_map, inplace=True)

    out_file = f"result_{uuid.uuid4().hex}.xlsx"
    out_path = os.path.join(RESULT_FOLDER, out_file)
    final_df.to_excel(out_path, index=False)

    yield f"data: {json.dumps({'download': '/bds_result/download?file=' + out_file})}\n\n"

# ✅ Download Final Excel
@bds_result_bp.route("/bds_result/download")
def download():
    fname = request.args.get("file")
    fpath = os.path.join(RESULT_FOLDER, fname)
    if os.path.exists(fpath):
        return send_file(fpath, as_attachment=True)
    return f"File not found: {fpath}", 404

from fastapi import FastAPI, Query
from typing import List, Optional
import os
import requests
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import uuid

app = FastAPI(
    title="DART 공시 API",
    description="기업명을 입력하면 고유코드를 찾고, 해당 기업의 최근 30일 공시 목록을 반환합니다.",
    version="1.0.0"
)

# 환경 변수에서 API 키 읽기
API_KEY = os.getenv("DART_API_KEY", "b596571f28ba3404d31949859e2a07d5a35567b4")  # 반드시 실제 환경에선 환경변수로 설정할 것

CORPCODE_FILE = "CORPCODE.xml"

# 1. corpCode.xml 다운로드 및 압축 해제
def download_and_extract_corpcode(api_key):
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise Exception(f"코드 목록 다운로드 실패 (HTTP {response.status_code})")

    zip_path = f"corpCode_{uuid.uuid4().hex}.zip"
    with open(zip_path, "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall()
    
    os.remove(zip_path)

# 2. 기업명으로 고유코드 찾기
def find_corp_codes(company_name: str) -> List[dict]:
    if not os.path.exists(CORPCODE_FILE):
        download_and_extract_corpcode(API_KEY)

    tree = ET.parse(CORPCODE_FILE)
    root = tree.getroot()
    
    matched = []
    for corp in root.findall('list'):
        name = corp.find('corp_name').text.strip()
        code = corp.find('corp_code').text.strip()
        if company_name in name:
            matched.append({"corp_name": name, "corp_code": code})

    return matched

# 3. 고유코드로 최근 공시 목록 조회
def get_recent_reports(corp_code: str) -> List[dict]:
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")

    url = (
        f"https://opendart.fss.or.kr/api/list.json?"
        f"crtfc_key={API_KEY}&corp_code={corp_code}&bgn_de={start_date}&end_de={end_date}"
    )

    response = requests.get(url)
    if response.status_code != 200:
        return [{"error": f"DART 요청 실패 (HTTP {response.status_code})"}]
    
    data = response.json()

    if data.get("status") != "013" and not data.get("list"):
        return [{"error": f"공시 정보 조회 실패: {data.get('message', '알 수 없음')}"}]

    report_list = []
    for report in data.get("list", [])[:10]:




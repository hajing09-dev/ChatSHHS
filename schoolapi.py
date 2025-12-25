import requests
import os
try:
    import streamlit as st
    has_streamlit = True
except:
    has_streamlit = False

def get_neis_key():
    """NEIS 서비스 키를 secrets.toml 또는 환경변수에서 로드"""
    if has_streamlit:
        try:
            return st.secrets["neis"]["service_key"]
        except:
            pass
    return os.getenv("NEIS_API_KEY")

def call_school_api(api_name, date=None, grade=None, classnum=None, info_type=None):
    service_key = get_neis_key()
    if not service_key:
        return "NEIS API 키가 설정되지 않았습니다. .streamlit/secrets.toml 파일에 추가하거나 NEIS_API_KEY 환경 변수를 설정해주세요."
    base_urls = {
        "lunch": "https://open.neis.go.kr/hub/mealServiceDietInfo",
        "schedule": "https://open.neis.go.kr/hub/hisTimetable",
        "inform": "https://open.neis.go.kr/hub/schoolInfo",
        "year_sch": "https://open.neis.go.kr/hub/SchoolSchedule"
    }
    def single_query(single_date):
        params = {
            "KEY": service_key,
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": "J10",
            "SD_SCHUL_CODE": "7530081"
        }
        if api_name == "lunch":
            params.update({"MLSV_YMD": single_date, "pSize": "1"})
        elif api_name == "schedule":
            params.update({"GRADE": grade, "CLASS_NM": classnum, "ALL_TI_YMD": single_date, "pSize": "20"})
        elif api_name == "inform":
            params.update({"pSize": "10"})
        elif api_name == "year_sch":
            params.update({"AA_YMD": single_date, "pSize": "1"})
        else:
            return "지원하지 않는 API"
        url = base_urls.get(api_name)
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return f"API 호출 오류: {e}"
    # 날짜가 리스트면 반복 호출, 아니면 단일 호출
    if isinstance(date, list):
        results = {}
        for d in date:
            results[d] = single_query(d)
        return results
    else:
        return single_query(date)

# 결과 파싱 함수 분리

def extract_school_api_result(api_name, result, date, info_type=None):
    output = []
    if isinstance(result, dict) and isinstance(date, list):
        for d in date:
            if api_name == "lunch":
                try:
                    meal = result[d].get('mealServiceDietInfo', [{}])[1].get('row', [{}])[0].get('DDISH_NM', '정보 없음')
                except Exception:
                    meal = '정보 없음'
                output.append(f"{d} : 급식 {meal}")
            elif api_name == "schedule":
                try:
                    rows = result[d].get('hisTimetable', [{}])[1].get('row', [])
                except Exception:
                    rows = []
                if rows:
                    for i, r in enumerate(rows, 1):
                        output.append(f"{d} : {i}교시 {r.get('ITRT_CNTNT', '정보 없음')}")
                else:
                    output.append(f"{d} : 시간표 정보 없음")
            elif api_name == "year_sch":
                try:
                    event = result[d].get('SchoolSchedule', [{}])[1].get('row', [{}])[0].get('EVENT_NM', '일정 없음')
                except Exception:
                    event = '일정 없음'
                output.append(f"{d} : 일정 {event}")
            elif api_name == "inform":
                try:
                    info = result[d].get('schoolInfo', [{}])[1].get('row', [{}])[0].get(info_type, '정보 없음')
                except Exception:
                    info = '정보 없음'
                output.append(f"{d} : 정보 {info}")
            else:
                output.append(f"{d} : {result[d]}")
    else:
        if api_name == "year_sch":
            try:
                event = result.get('SchoolSchedule', [{}])[1].get('row', [{}])[0].get('EVENT_NM', '일정 없음')
            except Exception:
                event = '일정 없음'
            output.append(f"{date} : 일정 {event}")
        elif api_name == "lunch":
            try:
                meal = result.get('mealServiceDietInfo', [{}])[1].get('row', [{}])[0].get('DDISH_NM', '정보 없음')
            except Exception:
                meal = '정보 없음'
            output.append(f"{date} : 급식 {meal}")
        elif api_name == "schedule":
            try:
                rows = result.get('hisTimetable', [{}])[1].get('row', [])
            except Exception:
                rows = []
            if rows:
                for i, r in enumerate(rows, 1):
                    output.append(f"{date} : {i}교시 {r.get('ITRT_CNTNT', '정보 없음')}")
            else:
                output.append(f"{date} : 시간표 정보 없음")
        elif api_name == "inform":
            try:
                info = result.get('schoolInfo', [{}])[1].get('row', [{}])[0].get(info_type, '정보 없음')
            except Exception:
                info = '정보 없음'
            output.append(f"{date} : 정보 {info}")
        else:
            output.append(str(result))
    return output

def get_school_info(api_name, date=None, grade=None, classnum=None, info_type=None):
    """
    API 호출부터 정리된 데이터 추출까지 한 번에 반환하는 함수.
    항상 딕셔너리 형태로 반환.
    """
    result = call_school_api(api_name, date=date, grade=grade, classnum=classnum, info_type=info_type)
    lines = extract_school_api_result(api_name, result, date, info_type)
    out = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            out[key.strip()] = value.strip()
    return out

# 사용 예시
if __name__ == "__main__":
    print("학교 API 테스트")
    api_name = input("API 이름(lunch/schedule/inform/year_sch): ").strip()
    date_input = input("날짜(YYYYMMDD, 여러 개는 쉼표로): ").strip()
    if "," in date_input:
        date = [d.strip() for d in date_input.split(",")]
    else:
        date = date_input
    grade = input("학년(필요시): ").strip() or None
    classnum = input("반(필요시): ").strip() or None
    info_type = input("정보 코드(inform API만): ").strip() or None
    result = get_school_info(api_name, date=date, grade=grade, classnum=classnum, info_type=info_type)
    print("결과:")
    print(result)

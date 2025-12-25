"""ChatSHHS — Streamlit 기반 NEIS 통합 챗봇

이 모듈은 서현고등학교(학교 코드: 7530081) 관련 정보를 NEIS 오픈 API로 조회하고
Streamlit UI를 통해 질의응답 형태로 제공합니다. 주요 기능:
- 급식(lunch), 시간표(schedule), 학사일정(year_sch), 학교 기본 정보(inform) 조회
- OpenAI를 사용해 사용자의 의도를 판단하고 필요한 경우 NEIS API를 호출

실행 방법 (일반적인 가이드):
1) 터미널을 열고 이 파일이 있는 디렉토리(프로젝트 루트)로 이동합니다.
     예: `cd /경로/까지/프로젝트_폴더`
2) Streamlit으로 실행합니다 (파일명은 실제 파일에 맞게 조정하세요):
     `streamlit run ChatSHHS.py`
     (파일명을 바꿔 실행하거나 절대 경로로 지정할 수 있습니다.)

환경(의존성) 설치 예시:
    pip install streamlit requests openai
"""

import streamlit as st
import os
import requests
import datetime
import re
from openai import OpenAI
import logging
import pytz

# NEIS API 호출 개선 및 기존 챗봇 코드 개선

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# schoolapi.py의 API 통합 함수

def call_school_api(api_name, date=None, grade=None, classnum=None, info_type=None):
    """NEIS 오픈 API를 호출합니다.

    간단한 wrapper로, 단일 날짜 또는 여러 날짜를 순회하며 NEIS의 각 엔드포인트를 호출합니다.

    Args:
        api_name (str): 호출할 API 이름. ("lunch", "schedule", "inform", "year_sch").
        date (str or list[str], optional): 조회할 날짜(또는 날짜 리스트). 예: "20250614" 또는 ["20250614", "20250615"].
        grade (int, optional): 시간표 조회 시 학년.
        classnum (int, optional): 시간표 조회 시 반 번호.
        info_type (str, optional): 학교 기본정보 조회 시 원하는 필드명.

    Returns:
        dict or str: 성공 시 JSON을 Python dict로 반환합니다. 여러 날짜를 전달하면 날짜별 dict를 반환합니다.
        오류 발생 시 오류 메시지 문자열을 반환합니다.

    Raises:
        requests.RequestException: 네트워크/HTTP 오류가 발생할 수 있습니다(내부에서 캐치되어 문자열로 반환될 수 있음).
    """
    # NEIS 서비스 키: 우선 st.secrets에서 찾고, 없으면 환경변수 NEIS_API_KEY 사용
    try:
        service_key = st.secrets.neis.service_key
    except Exception:
        service_key = os.getenv("NEIS_API_KEY")
    if not service_key:
        logging.warning("NEIS API key not found. Set NEIS_API_KEY env var or add to .streamlit/secrets.toml")
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
            "ATPT_OFCDC_SC_CODE": "J10", #경기도 교육청의 코드
            "SD_SCHUL_CODE": "7530081" #서현고등학교의 학교 코드
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
    if isinstance(date, list):
        results = {}
        for d in date:
            results[d] = single_query(d)
        return results
    else:
        return single_query(date)

def extract_school_api_result(api_name, result, date, info_type=None):
    """`call_school_api`의 응답에서 의미 있는 텍스트 라인을 추출합니다.

    이 함수는 API 응답(JSON 구조)을 받아 사용자가 보기 쉬운 문자열 리스트로 변환합니다.

    Args:
        api_name (str): 사용한 API 이름.
        result (dict): `call_school_api`가 반환한 결과(단일 날짜의 dict 또는 날짜->dict 매핑).
        date (str or list[str]): 조회한 날짜(또는 날짜 리스트).
        info_type (str, optional): `inform` API 사용 시 원하는 필드명.

    Returns:
        list[str]: 날짜별로 포맷된 문자열 리스트를 반환합니다. 예: ["20251121 : 급식 ...", ...].
    """
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
                    row = result[d].get('schoolInfo', [{}])[1].get('row', [{}])[0]
                    if info_type:
                        info = row.get(info_type, '정보 없음')
                        output.append(f"학교 정보 - {info_type}: {info}")
                    else:
                        # info_type이 없으면 주요 정보를 모두 표시
                        school_name = row.get('SCHUL_NM', '학교명 없음')
                        school_addr = row.get('ORG_RDNMA', '주소 없음')
                        school_tel = row.get('ORG_TELNO', '전화번호 없음')
                        output.append(f"학교명: {school_name}")
                        output.append(f"주소: {school_addr}")
                        output.append(f"전화번호: {school_tel}")
                except Exception as e:
                    output.append(f"정보 조회 오류: {str(e)}")
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
                row = result.get('schoolInfo', [{}])[1].get('row', [{}])[0]
                if info_type:
                    info = row.get(info_type, '정보 없음')
                    output.append(f"학교 정보 - {info_type}: {info}")
                else:
                    # info_type이 없으면 주요 정보를 모두 표시
                    school_name = row.get('SCHUL_NM', '학교명 없음')
                    school_addr = row.get('ORG_RDNMA', '주소 없음')
                    school_tel = row.get('ORG_TELNO', '전화번호 없음')
                    output.append(f"학교명: {school_name}")
                    output.append(f"주소: {school_addr}")
                    output.append(f"전화번호: {school_tel}")
            except Exception as e:
                output.append(f"정보 조회 오류: {str(e)}")
        else:
            output.append(str(result))
    return output

def get_school_info(api_name, date=None, grade=None, classnum=None, info_type=None):
    """NEIS API를 호출하고 포맷된 결과(문자열 리스트)를 반환합니다.

    Args:
        api_name (str): 사용할 API 이름.
        date (str or list[str], optional): 조회할 날짜 또는 날짜 리스트.
        grade (int, optional): 시간표 조회 시 학년.
        classnum (int, optional): 시간표 조회 시 반 번호.
        info_type (str, optional): `inform` API 시 조회할 필드명.

    Returns:
        list[str]: 사용자에게 보여줄 수 있도록 포맷된 결과 라인들의 리스트.
    """
    result = call_school_api(api_name, date=date, grade=grade, classnum=classnum, info_type=info_type)
    lines = extract_school_api_result(api_name, result, date, info_type)
    # 여러 날짜의 결과를 모두 출력하도록 리스트 반환
    return lines

# 기존 ChatSHHS.py의 AI 챗봇 구조

def convert_relative_date_in_text(text, today_kst):
    """사용자 입력에서 상대 날짜 표현을 YYYYMMDD로 변환합니다."""
    import re
    
    # 한국식 주 구분: 일요일 시작
    days_since_sunday = (today_kst.weekday() + 1) % 7
    this_week_start = today_kst - datetime.timedelta(days=days_since_sunday)
    next_week_start = this_week_start + datetime.timedelta(days=7)
    
    # 상대 날짜 매핑
    replacements = {
        r'내일': (today_kst + datetime.timedelta(days=1)).strftime('%Y년 %m월 %d일'),
        r'모레': (today_kst + datetime.timedelta(days=2)).strftime('%Y년 %m월 %d일'),
        r'어제': (today_kst - datetime.timedelta(days=1)).strftime('%Y년 %m월 %d일'),
        r'다음주\s*월요일': (next_week_start + datetime.timedelta(days=1)).strftime('%Y년 %m월 %d일'),
        r'다음주\s*화요일': (next_week_start + datetime.timedelta(days=2)).strftime('%Y년 %m월 %d일'),
        r'다음주\s*수요일': (next_week_start + datetime.timedelta(days=3)).strftime('%Y년 %m월 %d일'),
        r'다음주\s*목요일': (next_week_start + datetime.timedelta(days=4)).strftime('%Y년 %m월 %d일'),
        r'다음주\s*금요일': (next_week_start + datetime.timedelta(days=5)).strftime('%Y년 %m월 %d일'),
        r'다음주\s*토요일': (next_week_start + datetime.timedelta(days=6)).strftime('%Y년 %m월 %d일'),
        r'다음주\s*일요일': next_week_start.strftime('%Y년 %m월 %d일'),
        r'이번주\s*월요일': (this_week_start + datetime.timedelta(days=1)).strftime('%Y년 %m월 %d일'),
        r'이번주\s*화요일': (this_week_start + datetime.timedelta(days=2)).strftime('%Y년 %m월 %d일'),
        r'이번주\s*수요일': (this_week_start + datetime.timedelta(days=3)).strftime('%Y년 %m월 %d일'),
        r'이번주\s*목요일': (this_week_start + datetime.timedelta(days=4)).strftime('%Y년 %m월 %d일'),
        r'이번주\s*금요일': (this_week_start + datetime.timedelta(days=5)).strftime('%Y년 %m월 %d일'),
        r'이번주\s*토요일': (this_week_start + datetime.timedelta(days=6)).strftime('%Y년 %m월 %d일'),
        r'이번주\s*일요일': this_week_start.strftime('%Y년 %m월 %d일'),
    }
    
    converted_text = text
    for pattern, replacement in replacements.items():
        converted_text = re.sub(pattern, replacement, converted_text)
    
    return converted_text

def respond(prompt):
    """사용자 질문을 받아 OpenAI로부터 응답을 생성하고 필요 시 NEIS API를 호출합니다.

    이 함수는 다음 흐름을 따릅니다:
    1) 사용자의 질문을 기반으로 모델에게 API 호출 필요 여부를 묻습니다.
    2) 모델이 `API:`로 응답하면 해당 API를 호출하고 결과를 모델에 다시 제공해 최종 응답을 생성합니다.

    Args:
        prompt (str): 사용자의 질문 텍스트.

    Returns:
        str: 최종적으로 사용자에게 보여줄 응답 텍스트.

    Side effects:
        - OpenAI API 호출
        - NEIS API 호출 (필요 시)
        - `st.session_state.messages`에 메시지를 추가하는 코드와 함께 사용됩니다.
    """
    logging.info(f"사용자 질문: {prompt}")
    # 한국 시간대로 오늘 날짜 설정
    kst = pytz.timezone('Asia/Seoul')
    today_kst = datetime.datetime.now(kst).date()
    today_yyyymmdd = today_kst.strftime("%Y%m%d")
    
    # 사용자 입력에서 상대 날짜를 절대 날짜로 변환
    converted_prompt = convert_relative_date_in_text(prompt, today_kst)
    if converted_prompt != prompt:
        logging.info(f"날짜 변환됨: {prompt} -> {converted_prompt}")
    
    # OpenAI API 키: 우선 st.secrets에서 찾고, 없으면 환경변수 OPENAI_API_KEY 사용
    try:
        api_key = st.secrets.openai.api_key
    except Exception:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.warning("OpenAI API key not found. Set OPENAI_API_KEY env var or add to .streamlit/secrets.toml")
    client = OpenAI(api_key=api_key)
    
    # 요일 정보 계산
    weekday_names = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    today_weekday = weekday_names[today_kst.weekday()]  # Monday=0, Sunday=6
    
    # 이번주와 다음주 날짜 예시 생성
    # 한국식: 일요일 시작 기준 (일-토)
    days_since_sunday = (today_kst.weekday() + 1) % 7  # 일요일=0, 월요일=1, ..., 토요일=6
    this_week_start = today_kst - datetime.timedelta(days=days_since_sunday)
    next_week_start = this_week_start + datetime.timedelta(days=7)
    
    this_week_friday = this_week_start + datetime.timedelta(days=5)  # 금요일
    next_week_friday = next_week_start + datetime.timedelta(days=5)  # 다음주 금요일
    
    messages = [
        {"role": "system", "content": f'''너는 서현고등학교 구성원들을 돕는 유용한 ChatSHHS이야.

**오늘 날짜: {today_yyyymmdd} ({today_weekday})**

참고: 사용자가 "다음주 월요일" 같은 상대 날짜를 말하면, 이미 서버에서 절대 날짜(예: 2025년 12월 29일)로 변환되어 전달됩니다.

**API 호출 규칙:**
1. 사용자 질문에 API 정보가 필요하면 호출
2. 날짜는 반드시 YYYYMMDD 형식 (예: 20251224)
3. "12월 25일" 형식은 20251225로 변환
4. 여러 날짜는 쉼표 구분 (예: lunch, 20251224,20251225)

API 목록:
- 급식: lunch, [YYYYMMDD]
- 시간표: schedule, [YYYYMMDD], [학년], [반]
- 학사일정: year_sch, [YYYYMMDD]
- 학교정보: inform (날짜 없음)
'''},
    ] + st.session_state.messages
    import json

    def generate_dialogue(messages, model="gpt-4.1-mini-2025-04-14", max_tokens=150,
                          temperature=0.7, top_p=1.0, frequency_penalty=0.0, presence_penalty=0.0,
                          functions=None, function_call="auto"):
        logging.info("OpenAI API 호출 중...")
        kwargs = dict(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )
        if functions is not None:
            kwargs["functions"] = functions
            kwargs["function_call"] = function_call
        response = client.chat.completions.create(**kwargs)
        logging.info("OpenAI 응답 수신 완료")
        return response

    # function-calling 스키마
    functions = [
        {
            "name": "get_school_info",
            "description": "NEIS API를 통해 학교 급식/시간표/학사일정/기본정보를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "api_name": {"type": "string"},
                    "date": {"type": ["string", "array"], "items": {"type": "string"}},
                    "grade": {"type": "integer"},
                    "classnum": {"type": "integer"},
                    "info_type": {"type": "string"}
                },
                "required": ["api_name"]
            }
        }
    ]

    def normalize_date_token(tok):
        """다양한 날짜 형식을 YYYYMMDD로 정규화합니다."""
        tok = str(tok).strip()
        
        # 이미 YYYYMMDD 형식인 경우
        if re.match(r"^\d{8}$", tok):
            try:
                datetime.datetime.strptime(tok, "%Y%m%d")
                return tok
            except ValueError:
                return None
        
        # YYYY-MM-DD 형식
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", tok)
        if m:
            try:
                datetime.datetime.strptime(f"{m.group(1)}{m.group(2)}{m.group(3)}", "%Y%m%d")
                return f"{m.group(1)}{m.group(2)}{m.group(3)}"
            except ValueError:
                return None
        
        # MM-DD 형식 (올해로 자동 설정)
        m = re.match(r"^(\d{1,2})-(\d{1,2})$", tok)
        if m:
            try:
                year = today_kst.year
                month = m.group(1).zfill(2)
                day = m.group(2).zfill(2)
                datetime.datetime.strptime(f"{year}{month}{day}", "%Y%m%d")
                return f"{year}{month}{day}"
            except ValueError:
                return None
        
        return None

    def validate_and_prepare_args(args: dict):
        allowed = {"lunch", "schedule", "inform", "year_sch"}
        api_name = args.get("api_name")
        if not api_name or api_name not in allowed:
            raise ValueError(f"허용되지 않는 api_name: {api_name}")
        out = {"api_name": api_name}
        
        # inform API는 date를 사용하지 않음
        if api_name == "inform":
            if "info_type" in args and args.get("info_type") is not None:
                out["info_type"] = str(args.get("info_type"))
            return out
        
        date = args.get("date")
        if isinstance(date, list):
            normalized = [normalize_date_token(d) for d in date]
            if any(n is None for n in normalized):
                raise ValueError("잘못된 날짜 형식")
            out["date"] = normalized
        elif isinstance(date, str):
            if "," in date:
                parts = [p.strip() for p in date.split(",") if p.strip()]
                normalized = [normalize_date_token(p) for p in parts]
                if any(n is None for n in normalized):
                    raise ValueError("잘못된 날짜 형식")
                out["date"] = normalized
            else:
                nd = normalize_date_token(date)
                if nd is None and date is not None:
                    raise ValueError("잘못된 날짜 형식")
                out["date"] = nd
        if "grade" in args and args.get("grade") is not None:
            out["grade"] = int(args.get("grade"))
        if "classnum" in args and args.get("classnum") is not None:
            out["classnum"] = int(args.get("classnum"))
        if "info_type" in args and args.get("info_type") is not None:
            out["info_type"] = str(args.get("info_type"))
        return out

    # 1) 사용자 메시지 전송 (모델에게 function 스키마 포함) - 변환된 프롬프트 사용
    messages.append({"role": "user", "content": converted_prompt})
    dialogue = generate_dialogue(messages, functions=functions, function_call="auto")
    msg = dialogue.choices[0].message
    # 2) 모델이 함수 호출을 요청했으면 검증/실행 후 결과를 모델에 전달
    if hasattr(msg, "function_call") and msg.function_call:
        try:
            raw_args = msg.function_call.arguments
            func_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            validated = validate_and_prepare_args(func_args)
            api_name = validated.pop("api_name")
            api_info = get_school_info(api_name, **validated)
        except Exception as e:
            messages.append({"role": "function", "name": msg.function_call.name if hasattr(msg.function_call, 'name') else 'get_school_info', "content": json.dumps({"error": str(e)}, ensure_ascii=False)})
            final = generate_dialogue(messages)
            return final.choices[0].message.content.strip()
        # 함수 실행 결과를 모델에게 전달하고 최종 응답을 요청
        try:
            func_result_content = json.dumps({"result": api_info}, ensure_ascii=False)
        except Exception:
            func_result_content = str(api_info)
        messages.append({"role": "function", "name": "get_school_info", "content": func_result_content})
        final = generate_dialogue(messages)
        return final.choices[0].message.content.strip()
    else:
        return getattr(msg, 'content', '').strip()

# 기존 Streamlit UI 구조
if "show_chat" not in st.session_state:
    st.session_state.show_chat = False
if not st.session_state.show_chat:
    st.image("https://github.com/hajing09-dev/ChatSHHS/blob/main/seohyun.png?raw=true", width=400)
    st.title("ChatSHHS")
    st.markdown("""
    ## 안내 및 주의 사항
    - 이 챗봇은 서현고등학교 관련 정보를 제공합니다.
    - 학교 공식 정보와 다를 수 있으니 참고용으로만 사용하세요.
    """)
    if st.button("채팅 시작하기"):
        st.session_state.show_chat = True
        st.rerun()
else:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ 이전", key="back_button"):
            st.session_state.show_chat = False
            st.rerun()
    with col2:
        theme = st.selectbox("테마 선택", ["라이트", "다크"], index=0)
        st.session_state.theme_mode = "dark" if theme == "다크" else "light"
    st.markdown(
        """
        <div style='display: flex; align-items: center; gap: 10px;'>
            <img src='https://github.com/hajing09-dev/ChatSHHS/blob/main/seohyun.png?raw=true' width='100'/>
            <h1 style='margin:0;'>ChatSHHS</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # 말풍선 색상 선택
    if st.session_state.theme_mode == 'dark':
        assistant_bg = '#222'
        assistant_color = '#fff'
        user_bg = '#333'
        user_color = '#fff'
        assistant_name = '#ffd600'
        user_name = '#4dd0e1'
        shadow = '#222'
    else:
        assistant_bg = '#fffde7'
        assistant_color = '#222'
        user_bg = '#e0f7fa'
        user_color = '#222'
        assistant_name = '#ffd600'
        user_name = '#0097a7'
        shadow = '#eee'
    
    def render_assistant_bubble(content):
        """챗봇의 말풍선을 렌더링합니다.

        Args:
            content (str): 표시할 메시지 텍스트.
        """
        st.markdown(f"""
        <div style='display:flex; align-items:center; text-align:left; background:{assistant_bg}; color:{assistant_color}; padding:8px 16px; border-radius:12px; margin:8px 0; max-width:70%; box-shadow:0 2px 8px {shadow};'>
            <img src='https://github.com/hajing09-dev/ChatSHHS/blob/main/seohyun.png?raw=true' width='32' style='margin-right:8px; border-radius:50%;'/>
            <div>
                <b style='color:{assistant_name};'>ChatSHHS</b><br>{content}
            </div>
        </div>
        """, unsafe_allow_html=True)

    def render_user_bubble(content):
        """유저의 말풍선을 렌더링합니다.

        Args:
            content (str): 표시할 메시지 텍스트.
        """
        st.markdown(f"""
        <div style='display:flex; flex-direction:row-reverse; align-items:center; text-align:right; background:{user_bg}; color:{user_color}; padding:8px 16px; border-radius:12px; margin:8px 0 8px auto; max-width:70%; box-shadow:0 2px 8px {shadow};'>
            <img src='https://cdn-icons-png.flaticon.com/512/1946/1946429.png' width='32' style='margin-left:8px; border-radius:50%;'/>
            <div>
                <b style='color:{user_name};'>나</b><br>{content}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 말풍선을 표시합니다.
    for message in st.session_state.messages:
        if message["role"] == 'assistant':
            render_assistant_bubble(message['content'])
        else:
            render_user_bubble(message['content'])
    if prompt := st.chat_input("질문을 입력하세요"):
        render_user_bubble(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("생성 중... 💬"):
            response = respond(prompt)
        render_assistant_bubble(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

#통합 코드

import streamlit as st
import requests
import xml.etree.ElementTree as ET
from openai import OpenAI
import datetime
import pytz
import re
import os
#급식 정보 호출
def lunch(date):
  url="https://open.neis.go.kr/hub/mealServiceDietInfo"
  service_key="13dfeef247464e6fbf4a5071623395ec"
  params={
      'KEY':service_key,
      'Type':'STRING',
      'MLSV_YMD':date,
      'pSize':'1',
      'ATPT_OFCDC_SC_CODE':'J10',
      'SD_SCHUL_CODE':'7530081'
  }
  response=requests.get(url,params=params)
  response=response.text
  if response.split('<MESSAGE>')[1].split('</MESSAGE>')[0]=='정상 처리되었습니다.':
    return response.split('<DDISH_NM><![CDATA[')[1].split(']]></DDISH_NM>')[0]
  else:
    return 'none'

#시간표
def schedule(date, grade, classnum):
  url="https://open.neis.go.kr/hub/hisTimetable"
  service_key="13dfeef247464e6fbf4a5071623395ec"
  params={
      'KEY':service_key,
      'Type':'STRING',
      'GRADE':grade,
      'CLASS_NM':classnum,
      'pSize':'20',
      'ATPT_OFCDC_SC_CODE':'J10',
      'SD_SCHUL_CODE':'7530081',
      'ALL_TI_YMD':date
  }
  response=requests.get(url,params=params)
  response=response.text
  root = ET.fromstring(response)
  if response.split('<MESSAGE>')[1].split('</MESSAGE>')[0]=='정상 처리되었습니다.':
    def try_int(v):
      try:
          return int(v)
      except (ValueError, TypeError):
          return v

    # 3) 모든 <row> 요소를 순회하며 딕셔너리로 변환
    rows = root.findall('.//row')
    result = ''
    for row in range(1,len(rows)+1):
       for child in rows[row-1]:
        if child.tag=='ITRT_CNTNT':
          result+=(str(row)+'교시: '+child.text.strip()+' ')

    # 만약 첫 번째 <row>만 필요하면 result[0] 사용
    return result
  else:
    return 'none'

school_info_dict = {
    "시도교육청코드": "ATPT_OFCDC_SC_CODE",
    "시도교육청명": "ATPT_OFCDC_SC_NM",
    "행정표준코드": "SD_SCHUL_CODE",
    "학교명": "SCHUL_NM",
    "영문학교명": "ENG_SCHUL_NM",
    "학교종류명": "SCHUL_KND_SC_NM",
    "시도명": "LCTN_SC_NM",
    "관할조직명": "JU_ORG_NM",
    "설립명": "FOND_SC_NM",
    "도로명우편번호": "ORG_RDNZC",
    "도로명주소": "ORG_RDNMA",
    "도로명상세주소": "ORG_RDNDA",
    "전화번호": "ORG_TELNO",
    "홈페이지주소": "HMPG_ADRES",
    "남녀공학구분명": "COEDU_SC_NM",
    "팩스번호": "ORG_FAXNO",
    "고등학교구분명": "HS_SC_NM",
    "산업체특별학급존재여부": "INDST_SPECL_CCCCL_EXST_YN",
    "고등학교일반전문구분명": "HS_GNRL_BUSNS_SC_NM",
    "특수목적고등학교계열명": "SPCLY_PURPS_HS_ORD_NM",
    "입시전후기구분명": "ENE_BFE_SEHF_SC_NM",
    "주야구분명": "DGHT_SC_NM",
    "설립일자": "FOND_YMD",
    "개교기념일": "FOAS_MEMRD",
    "수정일자": "LOAD_DTM"
}


#학교 기본 정보
def inform(info_type):
  url="https://open.neis.go.kr/hub/schoolInfo"
  service_key="13dfeef247464e6fbf4a5071623395ec"
  params={
      'KEY':service_key,
      'Type':'STRING',
      'pSize':'10',
      'ATPT_OFCDC_SC_CODE':'J10',
      'SD_SCHUL_CODE':'7530081'
  }
  response=requests.get(url,params=params)
  response=response.text
  root = ET.fromstring(response)

# 2) 숫자로 보이는 문자열을 int로 변환해주는 헬퍼
  def try_int(v):
      try:
          return int(v)
      except (ValueError, TypeError):
          return v

  # 3) 첫 번째 <row> 요소를 찾아 딕셔너리로 변환
  row = root.find('row')
  row_dict = {}
  if row is not None:
      for child in row:
          text = child.text.strip() if child.text else ''
          row_dict[child.tag] = try_int(text)
  return row_dict[info_type]
def year_sch(date):
  url="https://open.neis.go.kr/hub/SchoolSchedule"
  service_key="13dfeef247464e6fbf4a5071623395ec"
  params={
      'KEY':service_key,
      'Type':'STRING',
      'pSize':'1',
      'ATPT_OFCDC_SC_CODE':'J10',
      'SD_SCHUL_CODE':'7530081',
      'AA_YMD':date
  }
  response=requests.get(url,params=params).text
  if '해당하는' in response:
    return 'None'
  else:
    return response.split('EVENT_NM')[1]

def convert_relative_date_in_text(text, today_kst):
    """사용자 입력에서 상대 날짜 표현을 YYYYMMDD로 변환합니다."""
    
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
    # 한국 시간대로 오늘 날짜 설정
    kst = pytz.timezone('Asia/Seoul')
    today_kst = datetime.datetime.now(kst).date()
    today = today_kst.isoformat()
    
    # 사용자 입력에서 상대 날짜를 절대 날짜로 변환
    converted_prompt = convert_relative_date_in_text(prompt, today_kst)

    # API 키 로드: secrets.toml 또는 환경 변수 사용
    try:
        api_key = st.secrets["openai"]["api_key"]
    except:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        st.error("⚠️ OpenAI API 키가 설정되지 않았습니다. .streamlit/secrets.toml 파일에 추가하거나 OPENAI_API_KEY 환경 변수를 설정해주세요.")
        st.stop()

    # OpenAI 클라이언트 초기화
    client = OpenAI(api_key=api_key)

    messages = [
        {"role": "system", "content": f'''너는 서현고등학교 구성원들을 돕는 유용한 ChatSHHS이고 오늘 날짜는 {today}이야.

참고: 사용자가 "다음주 월요일" 같은 상대 날짜를 말하면, 이미 서버에서 절대 날짜(예: 2025년 12월 29일)로 변환되어 전달됩니다.

질문마다 ***매번*** 다음 순서를 따라:
1. 사용자의 질문이 너의 지식 밖이고 현재까지 API에서 얻은 결과로 알 수 없어 추가적으로 API를 불러와야 하는거라면 'API: '라 쓴 후 아래 API 표를 참고해 API 명과 그 뒤 {{}}(있다면)로 된 정보를 줘.
***모르는 정보라면 그에 맞는 API를 불러와***
2. 너가 답변을 아는 질문일 때만 사용자에 대답해. 그땐 API를 불러오지마.

예시:
2025년 06월 14일 2학년 6반 시간표 뭐야?
-> API: schedule, 20250614, 2, 6
그럼 5반은?
-> API: schedule, 20250614, 2, 5

API 표:
-시간표: schedule, {{YYYYMMDD}}, {{grade}}, {{class}}
-학교 기본 정보(주소, 전화번호, 개교기념일 등): inform
-학사일정: year_sch, {{YYYYMMDD}}
-급식정보: lunch, {{YYYYMMDD}}
        '''},
    ]+st.session_state.messages

    def generate_dialogue(messages, model="gpt-4.1-mini-2025-04-14", max_tokens=150,
                          temperature=0.7, top_p=1.0, frequency_penalty=0.0, presence_penalty=0.0):
        response = client.chat.completions.create(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty
        )
        return response


    messages.append({"role": "user", "content": "지어내지 말고 API 호출하기!:" + converted_prompt})
    dialogue = generate_dialogue(messages)

        # 결과를 대화 형식으로 출력
    for choice in dialogue.choices:
            message_content = choice.message.content.strip()
            res = message_content.split("\n\n")[0]
            if res.startswith("API"):
                res = res[5:]
                res = res.split(", ")
                if res[0] == "schedule":
                    api_info = schedule(res[1], res[2], res[3])
                elif res[0] == "inform":
                    messages.append({"role": "system", "content": str(school_info_dict) + "\n이 딕셔너리에서 필요한 정보에 대해 반드시 영문코드'만' 출력해. 예:학교명 -> SCHUL_NM / 없다면 NONE"})
                    dialogue = generate_dialogue(messages)
                    messages.pop()
                    for choice in dialogue.choices:
                        message_content = choice.message.content.strip()
                        res = message_content.split("\n\n")[0]
                        if res == "NONE":
                            api_info = "None"
                        else:
                            api_info = str(inform(res))
                elif res[0] == "year_sch":
                    api_info = year_sch(res[1])
                elif res[0] == "lunch":
                    api_info = lunch(res[1])

                messages.append({"role": "system", "content": f'''이 내용을 이용해 사용자의 질문에 답변해.*주의: 지금은 API를 불러오는 것이 아닌, 그 결과를 바탕으로 정확하게 답변할 때야
                API 결과: {api_info}'''})
                dialogue = generate_dialogue(messages)
                for choice in dialogue.choices:
                    message_content = choice.message.content.strip()
                    res = message_content.split("\n\n")[0]
                    return res

            else:
                return res


# 공통 처리 함수: 사용자 프롬프트를 받아서 화면에 표시하고 응답을 생성해 세션에 저장
def process_user_prompt(prompt_text):
    # 세션에 사용자 요청을 추가하고 챗봇 응답을 생성해 응답을 세션에 추가합니다.
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    with st.spinner("생성 중... 💬"):
        response = respond(prompt_text)
    st.session_state.messages.append({"role": "assistant", "content": response})




# UI 상태 변수
if "show_chat" not in st.session_state:
    st.session_state.show_chat = False

if not st.session_state.show_chat:
    st.image("https://github.com/hajing09-dev/ChatSHHS/blob/main/seohyun.png?raw=true", width=400)
    st.title("ChatSHHS")
    st.markdown("""
    ## 안내 및 주의 사항
    - 이 챗봇은 서현고등학교 관련 정보를 제공합니다.
    - 학교 공식 정보와 다를 수 있으니 참고용으로만 사용하세요.
    """) #안내문
    if st.button("채팅 시작하기"):
        st.session_state.show_chat = True
        st.rerun()
else:
    if st.button("⬅️ 이전", key="back_button"):
        st.session_state.show_chat = False
        st.rerun()
    st.markdown(
        """
        <div style='display: flex; align-items: center; gap: 10px;'>
            <img src='https://github.com/hajing09-dev/ChatSHHS/blob/main/seohyun.png?raw=true' width='100'/>
            <h1 style='margin:0;'>ChatSHHS</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 추천 질문 버튼 상태 초기화 (한 번 사용하면 사라짐)
    if "recommended_used" not in st.session_state:
        st.session_state.recommended_used = False
    if "queued_prompt" not in st.session_state:
        st.session_state.queued_prompt = ""

    # 로고 바로 아래에 추천 질문을 표시 (한 번 사용하면 숨김)
    if not st.session_state.recommended_used:
        recommended_questions = [
            "어제 급식 알려줘",
            "오늘 급식",
            "이번 주 학사일정",
            "2학년 6반 시간표"
        ]
        st.markdown("**추천 질문**")
        cols = st.columns(len(recommended_questions))
        for q, col in zip(recommended_questions, cols):
            if col.button(q):
                # 버튼 클릭 시 즉시 사용자 말풍선을 동일하게 렌더링한 뒤 프롬프트를 큐에 넣고 추천 질문은 다시 표시하지 않음
                st.markdown(f"""
                <div style='display:flex; flex-direction:row-reverse; align-items:center; text-align:right; background:#e0f7fa; padding:8px 16px; border-radius:12px; margin:8px 0 8px auto; max-width:70%; box-shadow:0 2px 8px #eee;'>
                    <img src='https://cdn-icons-png.flaticon.com/512/1946/1946429.png' width='32' style='margin-left:8px; border-radius:50%;'/>
                    <div>
                        <b>나</b><br>{q}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.session_state.queued_prompt = q
                st.session_state.recommended_used = True
                st.rerun()

    # 만약 버튼으로 큐에 들어온 프롬프트가 있으면 처리하고 새로고침
    if st.session_state.get("queued_prompt"):
        temp_q = st.session_state.queued_prompt
        st.session_state.queued_prompt = ""
        process_user_prompt(temp_q)
        st.rerun()

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun (커스텀 방향)
    for message in st.session_state.messages:
        if message["role"]=='assistant':
            st.markdown(f"""
            <div style='display:flex; align-items:center; text-align:left; background:#fffde7; padding:8px 16px; border-radius:12px; margin:8px 0; max-width:70%; box-shadow:0 2px 8px #eee;'>
                <img src='https://github.com/hajing09-dev/ChatSHHS/blob/main/seohyun.png?raw=true' width='32' style='margin-right:8px; border-radius:50%;'/>
                <div>
                    <b>ChatSHHS</b><br>{message['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style='display:flex; flex-direction:row-reverse; align-items:center; text-align:right; background:#e0f7fa; padding:8px 16px; border-radius:12px; margin:8px 0 8px auto; max-width:70%; box-shadow:0 2px 8px #eee;'>
                <img src='https://cdn-icons-png.flaticon.com/512/1946/1946429.png' width='32' style='margin-left:8px; border-radius:50%;'/>
                <div>
                    <b>나</b><br>{message['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # React to user input (입력창 처리 부분은 아래에서 통합 처리)

    # 기존 텍스트 입력창은 페이지 맨 아래에 위치시키면 사실상 고정 입력처럼 동작합니다.
    # 채팅 입력 처리: 입력이 제출되면 공통 함수로 처리하고 새로고침
    if prompt := st.chat_input("질문을 입력하세요"):
        process_user_prompt(prompt)
        st.rerun()


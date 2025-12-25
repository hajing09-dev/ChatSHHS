# ChatSHHS

서현고등학교 학생들을 위한 AI 챗봇입니다.

## 기능

- 🍽️ 급식 정보 조회
- 📚 시간표 조회
- 📅 학사일정 확인
- 🏫 학교 기본 정보 제공
- 💬 자연스러운 대화형 인터페이스

## 필요한 것

- OpenAI API 키 (GPT-4)
- NEIS 서비스 키 (한국 교육청 API)

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run ChatSHHS.py
```

그 후 `.streamlit/secrets.toml`에 API 키 추가:
```toml
[openai]
api_key = "your-api-key"

[neis]
service_key = "your-neis-key"
```

## 배포
https://chatshhs.streamlit.app/ <-- 실행해보기

Streamlit Cloud에서 GitHub 저장소 연동 후 배포 가능합니다.

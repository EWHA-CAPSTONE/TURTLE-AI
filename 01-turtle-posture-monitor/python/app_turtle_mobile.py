import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
import os, requests, json

# === 비밀번호 인증 ===
PASSWORD = "1886"

# 세션 상태 초기화
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 인증 안 된 경우 → 비밀번호 입력창 표시 후 return
if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align:center;'>🔐 접속 인증</h2>", unsafe_allow_html=True)

    input_pw = st.text_input("비밀번호를 입력하세요", type="password")

    if st.button("로그인"):
        if input_pw == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ 비밀번호가 올바르지 않습니다.")

    st.stop()  # ❗ 인증 전에는 아래 코드 실행 금지

# === 절대 경로 기반 프로젝트 루트 설정 ===
BASE_DIR = Path(__file__).resolve().parents[1]   
print(f"📁 BASE_DIR = {BASE_DIR}")

# === .env 로드 ===
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH, override=True)

# === 환경 변수 불러오기 ===
api_key = os.getenv("OPENAI_API_KEY")

# === LLM 프롬프트 ===
template = """
당신은 친근하고 정확한 자세 코치입니다. 
아래 JSON 데이터를 바탕으로 **1분 단위 측정 세션 보고서**를 작성하세요.

🧩 규칙:
- JSON 안의 데이터만 사용하세요. 추가 계산이나 새로운 수치를 만들어내지 마세요.

ㄴㅅ

[JSON 구조]
- summary: 전체 통계 (참고용). 'total_segments'나 'avg_forward_head_per_segment' 같은 값은 단순 기술 수치이므로 보고서에 직접 언급하지 마세요.
- details: 각 1분 단위(time 필드)의 측정 구간별 데이터를 포함합니다.
- time: 측정된 1분 구간 (예: "16:00:00-16:01:00")
- forward_head_count: 해당 시간 동안 거북목 자세로 감지된 횟수 (즉, 숙임 발생 횟수)
- total_samples: 해당 구간 동안 센서가 수집한 전체 데이터 수 (즉, 총 측정 횟수)
- forward_head_ratio: 거북목 비율 (forward_head_count / total_samples)
- **총 측정 시간은 details의 time 필드 구간을 연속적으로 계산해 판단하세요.**

[보고서 멘트]
- 데이터 사용: 
JSON 안의 데이터만 사용합니다.
summary는 참고용이며, 실제 해석은 details의 데이터를 기반으로 합니다.
새로운 수치 계산은 절대 하지 않습니다.

- 핵심 해석 기준:
중심 지표: forward_head_ratio
각 시간대의 변화를 자연스럽게 서술하세요.
초반(첫 1/3), 중반(중간 1/3), 후반(마지막 1/3) 구간의 특징을 나눠 해석하세요.

- 표현 방식:
숫자 비율 대신 행동 묘사로 표현합니다.
    예: "forward_head_ratio가 0.49" → "해당 구간의 절반 가까이 고개를 숙이고 있었습니다."
시간은 반드시 숫자 + “분” 형식으로 언급합니다.
    예: "16:00:00-16:01:00" → "16분 구간에서"

- 문체 및 말투:
기술 용어 대신 일상 언어를 사용하세요.
긍정적이고 격려하는 말투로 작성합니다.
    예: “좋아요!”, “아주 잘하고 계세요!”

- 피드백 구성:
보고서 말미에 행동 개선 팁을 구체적으로 제시합니다.
    예: “20초마다 어깨를 돌려보세요.”
숫자는 꼭 필요한 경우에만 1문장당 1개 이하로 사용합니다.

---

📈 세션 상태 판정 기준:
- 평균 숙임 비율 0~25% → ✅ 정상
- 평균 숙임 비율 25~35% → ⚠️ 주의
- 평균 숙임 비율 35% 이상 → 🔴 위험
(판정은 전체 구간의 forward_head_ratio 평균으로 간접 판단해도 됩니다.)

🪞 작성 방식:
- 보고서는 총 5단락으로 구성하세요.
  ① 세션 상태  
  ② 핵심 지표  
  ③ 구간별 분석 (초반 / 중반 / 후반)  
  ④ Top3 순간  
  ⑤ 피드백  
- 각 단락은 두 줄 띄우기로 구분합니다.
- 피드백 단락에서는 “이유 + 행동 제안 + 격려 마무리”를 포함하세요.
---

📋 보고서 구성:

세션 상태:  
(time 구간 전체를 기반으로 평균 숙임 비율을 판단하여 ‘정상’, ‘주의’, ‘위험’ 중 하나 선택하고 한 문장으로 요약.)

핵심 지표:  
- 총 측정 시간: details의 time 구간 길이를 합산하여 표현 (예: "약 10분간 측정")  
- 평균 숙임 비율: forward_head_ratio 전체 평균을 행동 기반 문장으로 표현

구간별 분석:  
- 초반 특징: (처음 약 3분, 첫 9개 구간 중심으로)  
- 중반 특징: (중간 3분, 중간 9개 구간 중심으로)  
- 후반 특징: (마지막 3분, 마지막 구간 중심으로)

Top3 순간:  
- forward_head_ratio가 높은 상위 3개 시간대를 각각 줄바꿈(\n)하여 표현합니다.  
- 각 구간은 다음 형식을 따릅니다:
  ① 시간대 + 상황 설명 + 행동 해석
  - TOP1 특징: (상황 한 줄 설명 + 한 줄 해석)  
  - TOP2 특징: (상황 한 줄 설명 + 한 줄 해석)     
  - TOP3 특징: (상황 한 줄 설명 + 한 줄 해석)  

피드백:  
- 습관 개선, 스트레칭 제안, 장기 유지 팁 등을 2~3문장으로 서술
- 문체는 “설명 → 제안 → 격려” 순서로 작성

형식:
- 각 문단은 두 줄 띄우기(\n\n) 로 구분합니다.
- 총 분량은 약 1000자 내외로 충분히 서술합니다.
- 데이터 나열이 아닌, 시간의 흐름에 따른 행동 패턴 스토리로 구성합니다.

---

BEGIN JSON
{json_summary}
END JSON
"""

prompt = ChatPromptTemplate.from_template(template)

# === LLM 체인 ===
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    api_key=api_key,
)

parser = StrOutputParser()
chain = prompt | llm | parser

# === Streamlit 기본 설정 ===
st.set_page_config(page_title="거북목 자세 분석 리포트", page_icon="🐢", layout="centered")

st.markdown("""
<style>

/* 기본 폰트 & 배경 */
body, [data-testid="stAppViewContainer"] {
    background-color: white;
    font-family: 'Noto Sans KR', sans-serif;
    padding: 0;
    margin: 0;
}

/* 모바일 뷰포트 대응 */
@media (max-width: 768px) {
    h1 {
        font-size: 36px !important;   /* 기존 70px 축소 */
        line-height: 1.2;
        margin-bottom: 20px;
    }

    .date-box, .report-box {
        padding: 18px !important;     /* 박스 패딩 축소 */
        margin-bottom: 20px !important;
    }

    div[data-testid="column"] {
        flex-direction: column !important;
        display: block !important;    /* 컬럼이 모바일에서 아래로 떨어지도록 */
        width: 100% !important;
    }

    /* 버튼 크기 모바일 최적화 */
    div.stButton > button:first-child {
        padding: 12px 12px !important;
        font-size: 16px !important;
        width: 100% !important;
    }
}

/* 박스 공통 스타일 */
.report-box {
    background-color: #ffffff;
    border-radius: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    padding: 35px;
    min-height: 400px;
}

.date-box {
    background-color: #ffffff;
    border-radius: 15px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    padding: 25px;
    text-align: center;
}

/* 버튼 스타일 */
div.stButton > button:first-child {
    background-color: #43A047;
    color: white;
    font-weight: bold;
    border-radius: 8px;
    padding: 10px 20px;
    width: 100%;
}

div.stButton > button:hover {
    background-color: #2E7D32;
}

</style>
""", unsafe_allow_html=True)

# === HEADER ===
st.markdown("""
<h1 style='font-size:30px; text-align:center;'>
    <span style="font-size:30px; vertical-align:middle;">🐢</span>
    거북목 자세 분석 리포트
</h1>
""", unsafe_allow_html=True)

# === UI 구성 ===
col1, col2 = st.columns([1, 2])

# === 달력 ===
with col1:
    st.markdown("<div class='date-box'>", unsafe_allow_html=True)
    st.subheader("📅 날짜 선택")

    selected_date = st.date_input(
        "측정 날짜를 선택하세요",
        value=datetime.today(),
        min_value=datetime.today() - timedelta(days=30),
        max_value=datetime.today(),
        format="YYYY/MM/DD"
    )

    generate_report = st.button("📄 리포트 생성하기", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
# === 리포트 UI ===
with col2:
    report_box = st.container()

    with report_box:
        if not generate_report:
            st.info("왼쪽에서 날짜를 선택하고 [📄 리포트 생성하기] 버튼을 눌러주세요.")
            st.stop()

        # ----------------------------------------------------
        # 리포트 생성 로직 시작
        # ----------------------------------------------------

        date_str = selected_date.strftime("%Y%m%d")
        json_url = f"https://raw.githubusercontent.com/EWHA-CAPSTONE/TURTLE-AI/main/01-turtle-posture-monitor/data_json/data_posture_{date_str}_summary.json"

        # 1) GitHub 요청
        try:
            response = requests.get(json_url)
        except Exception as e:
            st.error(f"❌ GitHub 요청 자체 실패: {e}")
            st.stop()

        # 2) 파일 존재 여부 체크
        if response.status_code != 200:
            st.error(
                f"❌ 해당 날짜({selected_date.strftime('%Y/%m/%d')})의 JSON 데이터가 GitHub에 없습니다.\n"
                f"URL: {json_url}"
            )
            st.stop()

        # 3) 정상 로딩
        json_summary = response.text

        # 4) AI 분석
        with st.spinner("📊 AI 분석 중..."):
            report = chain.invoke({"json_summary": json_summary})

        # 5) 출력 UI
        st.markdown("### 💬 코치 피드백")
        st.markdown(
            f"""
            <div style="
                background-color: #F1F8E9;
                border-radius: 12px;
                padding: 25px;
                margin-top: 20px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.08);
                font-size: 1rem;
                line-height: 1.6;
            ">
                {report}
            </div>
            """,
            unsafe_allow_html=True,
        )

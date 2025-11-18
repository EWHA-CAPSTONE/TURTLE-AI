import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
import os


# === 1️⃣ 절대 경로 기반 프로젝트 루트 설정 ===
BASE_DIR = Path(__file__).resolve().parents[1]   # 0.1 → langchain
print(f"📁 BASE_DIR = {BASE_DIR}")

# === 2️⃣ .env 로드 ===
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH, override=True)

# === 3️⃣ 환경 변수 불러오기 ===
api_key = "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"

# === LLM 프롬프트 ===
template = """
당신은 친근하고 정확한 자세 코치입니다. 아래 JSON 데이터를 바탕으로 **1분 단위 측정 세션 보고서**를 작성하세요.

🧩 규칙:
- JSON 안의 데이터만 사용하세요. 추가 계산이나 새로운 수치를 만들어내지 마세요.
- JSON 구조는 다음과 같습니다:
  - summary: 전체 통계 (참고용). 'total_segments'나 'avg_forward_head_per_segment' 같은 값은 단순 기술 수치이므로 보고서에 직접 언급하지 마세요.
  - details: 각 1분 단위(time 필드)의 측정 구간별 데이터를 포함합니다.
    - time: 측정된 1분 구간 (예: "16:00:00-16:01:00")
    - forward_head_count: 해당 시간 동안 거북목 자세로 감지된 횟수 (즉, 숙임 발생 횟수)
    - total_samples: 해당 구간 동안 센서가 수집한 전체 데이터 수 (즉, 총 측정 횟수)
    - forward_head_ratio: 거북목 비율 (forward_head_count / total_samples)
- **총 측정 시간은 details의 time 필드 구간을 연속적으로 계산해 판단하세요.**
- 보고서에서는 forward_head_ratio를 중심으로 각 시간대의 행동 변화를 해석하세요.
  (예: "forward_head_ratio가 0.49" → "해당 구간의 절반 가까이 고개를 숙이고 있었습니다.")
- 'segments'나 숫자 집계는 언급하지 말고, 시간 흐름에 따라 자연스럽게 이야기하세요.
- 분석 시 초반(첫 1/3), 중반(중간 1/3), 후반(마지막 1/3) 구간의 특징을 구분해 주세요.
- 보고서는 반드시 **한국어**로 작성하고, 문장은 간결하지만 구체적으로 써주세요.
- 각 항목은 **두 줄 띄기(\\n\\n)** 로 구분해 시각적으로 읽기 좋게 만드세요.
- 전체 분량은 약 1000자 정도로 충분히 길게 작성하세요.
- 비율(%)은 사용자가 이해하기 쉽게 **행동 기반 표현으로 바꾸세요.**
  예: "숙임 비율이 30%" → "고개를 숙이고 있었던 시간이 전체의 약 3분의 1 정도였습니다."
- 숫자는 꼭 필요한 경우만 쓰고, 하나의 문장에 1개 이하로 제한하세요.
- 데이터 나열 대신, 사용자의 **시간 흐름에 따른 행동 패턴**을 자연스럽게 묘사하세요.
- 친근하고 격려하는 말투를 사용하세요. (예: “좋아요!”, “아주 잘하고 계세요!”)
- 결과를 읽는 사람은 일반 사용자입니다. 기술 용어를 쓰지 마세요.
- 피드백 항목에서는 행동 개선 팁을 구체적으로 제시하세요. (예: “20초마다 어깨를 돌려보세요.”)
- 문장은 모바일로 읽기 쉽게 짧게 끊어주세요.

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
  예: “중반 이후 고개 숙임이 잦았어요. 15분마다 어깨를 돌려주면 좋아요 💪 꾸준히 유지해봐요 😊”

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
- forward_head_ratio가 높은 상위 3개 시간대의 공통 패턴과 집중도 변화 설명

피드백:  
- 습관 개선, 스트레칭 제안, 장기 유지 팁 등을 2~3문장으로 서술
- 문체는 “설명 → 제안 → 격려” 순서로 작성
  예: “중반부에 집중이 잠시 흐트러졌어요. 이럴 땐 자리에서 일어나 어깨를 쭉 펴주세요 🙆‍♀️ 아주 잘하고 계세요 👍”

---

### JSON 데이터 ###
BEGIN JSON
{json_summary}
END JSON
"""


prompt = ChatPromptTemplate.from_template(template)

# === LLM 체인 ===
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    api_key=api_key,
)

parser = StrOutputParser()
chain = prompt | llm | parser

# === Streamlit 기본 설정 ===
st.set_page_config(page_title="거북목 자세 분석 레포트", page_icon="🐢", layout="wide")

# === CSS ===
st.markdown("""
<style>
body, [data-testid="stAppViewContainer"] {
    background-color: white;
    font-family: 'Noto Sans KR', sans-serif;
}
.title {
    text-align: center;
    color: #2E7D32;
    font-weight: 800;
    font-size: 2rem;
    margin-bottom: 1.5em;
}
.report-box {
    background-color: #ffffff;
    border-radius: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    padding: 35px;
    min-height: 600px;
}
.date-box {
    background-color: #ffffff;
    border-radius: 15px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    padding: 25px;
    text-align: center;
}
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
st.markdown("<h1 style='font-size:70px; text-align:center;'>🐢 거북목 자세 분석 레포트</h1>", unsafe_allow_html=True)

# === UI 구성 ===
col1, col2 = st.columns([1, 2])

# 📅 왼쪽
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

    generate_report = st.button("📄 레포트 생성하기", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# 🧾 오른쪽
with col2:
    report_box = st.container()

    with report_box:
        if generate_report:
            date_str = selected_date.strftime("%Y%m%d")
            data_dir = Path(__file__).resolve().parent / "data_json"
            json_file = data_dir / f"data_posture_{date_str}_summary.json"

            if json_file.exists():
                with open(json_file, "r", encoding="utf-8") as f:
                    json_summary = f.read()

                with st.spinner("📊 AI 분석 중..."):
                    report = chain.invoke({"json_summary": json_summary})

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
                    unsafe_allow_html=True
                )

            else:
                st.error(f"❌ 해당 날짜({selected_date.strftime('%Y/%m/%d')})의 데이터 파일이 없습니다.")
        else:
            st.info("왼쪽에서 날짜를 선택하고 [📄 레포트 생성하기] 버튼을 눌러주세요.")
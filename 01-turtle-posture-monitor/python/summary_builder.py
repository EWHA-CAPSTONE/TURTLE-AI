import pandas as pd
from datetime import datetime
from pathlib import Path
import json

# ---- 기준 경로 설정 (python/ 폴더의 상위 폴더 기준) ----
BASE_DIR = Path(__file__).resolve().parents[1]
CSV_DIR = BASE_DIR / "data_csv"
JSON_DIR = BASE_DIR / "data_json"

# ---- 오늘 날짜 기준 파일명 ----
today = datetime.now().strftime("%Y%m%d")

# ---- 최신 CSV 파일 찾기 ----
csv_files = sorted(CSV_DIR.glob(f"data_posture_{today}_*.csv"))
if not csv_files:
    raise FileNotFoundError(f"⚠️ {CSV_DIR} 내에 data_posture_{today}_*.csv 파일이 없습니다.")

CSV_FILE = csv_files[-1]
print(f"불러온 파일: {CSV_FILE.name}")

# ---- CSV 로드 ----
df = pd.read_csv(CSV_FILE)

df.columns = ["timestamp", "theta_neck"]

# ---- timestamp 변환 ----
df["timestamp"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S", errors="coerce")

# ---- 임계값 기준 (30도 이상 = 거북목 자세) ----
THRESH_DEG = 30
df["is_forward_head"] = df["theta_neck"].abs() > THRESH_DEG

# ---- 1분 단위 집계 ----
count_1min = df.resample("1T", on="timestamp")["is_forward_head"].sum()
total_1min = df.resample("1T", on="timestamp")["is_forward_head"].count()

# ---- summary 계산 ----
total_segments = len(count_1min)
total_forward_head_count = int(count_1min.sum())
avg_forward_head_per_seg = (
    round(total_forward_head_count / total_segments, 2) if total_segments > 0 else 0.0
)

# ---- details 생성 ----
details = []
for time, count in count_1min.items():
    total = total_1min.get(time, 0)
    ratio = round(count / total, 3) if total > 0 else 0.0
    details.append({
        "time": f"{time.strftime('%H:%M')}-{(time + pd.Timedelta(minutes=1)).strftime('%H:%M')}",
        "forward_head_count": int(count),
        "total_samples": int(total),
        "forward_head_ratio": ratio
    })

# ---- 최종 JSON 구조 ----
summary_json = {
    "summary": {
        "total_segments": int(total_segments),
        "total_forward_head_count": total_forward_head_count,
        "avg_forward_head_per_segment": avg_forward_head_per_seg
    },
    "details": details
}

# ---- JSON 저장 ----
JSON_DIR.mkdir(exist_ok=True)
out_file = JSON_DIR / f"data_posture_{today}_summary.json"

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(summary_json, f, ensure_ascii=False, indent=2)

# ---- 결과 출력 ----
print(json.dumps(summary_json, ensure_ascii=False, indent=2))
print(f"요약 JSON (1분 단위) 저장 완료: {out_file}")
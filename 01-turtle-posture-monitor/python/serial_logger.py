import serial
import csv
from datetime import datetime
from pathlib import Path

# ---- 시리얼 포트 설정 ----
ser = serial.Serial('COM3', 9600, timeout=1)

# ---- CSV 저장 경로 ----
BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "data_csv"
CSV_DIR.mkdir(exist_ok=True)

# ---- 파일 이름 ----
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
CSV_FILE = CSV_DIR / f"data_posture_{timestamp}.csv"

# ---- CSV 파일 생성 ----
with open(CSV_FILE, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['timestamp', 'theta_neck_deg'])

    print(f"📡 자세 데이터 기록 시작 (파일: {CSV_FILE}) — Ctrl+C로 종료")

    try:
        while True:
            raw_line = ser.readline().decode(errors='ignore').strip()
            if not raw_line:
                continue

            try:
                theta_neck = float(raw_line)
                now = datetime.now().strftime('%H:%M:%S')

                # CSV 기록
                writer.writerow([now, theta_neck])
                print(f"[{now}] θ_neck={theta_neck:.2f}°")

            except ValueError:
                # 숫자 변환 실패 = 상태 메시지
                if "Invalid" in raw_line:
                    print("⚠️ 센서 측정 오류 — 값 무시됨")
                elif "Sensors ready" in raw_line:
                    print("✅ 센서 초기화 완료")
                elif "Calibration complete" in raw_line:
                    print("✅ Calibration 완료 — 이제 자세 측정 시작!")
                elif "Calibrating" in raw_line:
                    print("🔵 보정 중... (고개를 정자세로 유지)")
                else:
                    print(f"ℹ️ 기타 출력: {raw_line}")

    except KeyboardInterrupt:
        print("\n🛑 종료됨. CSV 파일이 저장되었습니다.")
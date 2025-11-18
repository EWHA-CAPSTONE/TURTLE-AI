#include <Wire.h>
#include <Adafruit_VL53L0X.h>

Adafruit_VL53L0X lox_upper = Adafruit_VL53L0X();
Adafruit_VL53L0X lox_lower = Adafruit_VL53L0X();

#define XSHUT_UPPER 6
#define XSHUT_LOWER 5
#define R_PIN 8
#define G_PIN 9
#define B_PIN 10

const float ALPHA = 0.5411; // 위 센서 각도 31°
const float BETA  = 0.035; // 아래 센서 각도 2°
const float d = 46.0;       // 센서 간 거리 (mm)
const float THRESHOLD = 30.0 * (3.141592 / 180.0); // 30°

float theta0 = 0;           // 초기 기준 각도 (정자세)
bool calibrated = false;    // 보정 완료 여부
unsigned long calibStart = 0;
const unsigned long CALIB_DURATION = 5000; // 5초 캘리브레이션

void setRGB(bool r, bool g, bool b) {
  digitalWrite(R_PIN, r ? HIGH : LOW);
  digitalWrite(G_PIN, g ? HIGH : LOW);
  digitalWrite(B_PIN, b ? HIGH : LOW);
}

void setup() {
  Serial.begin(9600);
  pinMode(XSHUT_UPPER, OUTPUT);
  pinMode(XSHUT_LOWER, OUTPUT);
  pinMode(R_PIN, OUTPUT);
  pinMode(G_PIN, OUTPUT);
  pinMode(B_PIN, OUTPUT);

  setRGB(false, false, false);

  // 센서 초기화
  digitalWrite(XSHUT_UPPER, LOW);
  digitalWrite(XSHUT_LOWER, LOW);
  delay(10);

  digitalWrite(XSHUT_UPPER, HIGH);
  delay(10);
  if (!lox_upper.begin(0x30)) {
    Serial.println(F("❌ Failed to boot upper sensor"));
    while (1);
  }

  digitalWrite(XSHUT_LOWER, HIGH);
  delay(10);
  if (!lox_lower.begin(0x31)) {
    Serial.println(F("❌ Failed to boot lower sensor"));
    while (1);
  }

  Serial.println(F("✅ Sensors ready."));
  Serial.println(F("➡️ Starting calibration for 5 seconds... Keep your head straight."));
  setRGB(false, false, true);  // 🔵 캘리브레이션 중
  calibStart = millis();
}

void loop() {
  VL53L0X_RangingMeasurementData_t m_upper, m_lower;
  lox_upper.rangingTest(&m_upper, false);
  lox_lower.rangingTest(&m_lower, false);

  int a = (m_upper.RangeStatus != 4) ? m_upper.RangeMilliMeter : -1;
  int b = (m_lower.RangeStatus != 4) ? m_lower.RangeMilliMeter : -1;

  if (a > 0 && b > 0) {
    float numerator = (-a * cos(ALPHA) + b * cos(BETA));
    float denominator = ( d + a * sin(ALPHA) - b * sin(BETA));
    float theta = fabs(atan2(numerator, denominator));

    // ───────────── 캘리브레이션 단계 ─────────────
    if (!calibrated) {
      if (millis() - calibStart < CALIB_DURATION) {
        static float sumTheta = 0;
        static int count = 0;
        sumTheta += theta;
        count++;
        Serial.print("Calibrating... θ = ");
        Serial.print(theta * 180.0 / 3.141592, 2);
        Serial.println("°");
      } else {
        theta0 = theta; // 평균 대신 마지막 값으로 기준
        calibrated = true;
        setRGB(false, true, false); // 🟢 보정 완료
        Serial.println(F("✅ Calibration complete! Start posture monitoring."));
      }
      delay(200);
      return;
    }

    // ───────────── 보정 이후 (실시간 측정) ─────────────
    float theta_neck = theta - theta0;
    float theta_deg = theta_neck * 180.0 / 3.141592;

    Serial.print("θ_neck = ");
    Serial.print(theta_deg, 2);
    Serial.println("°");

    if (fabs(theta_neck) > THRESHOLD)
      setRGB(true, false, false);  // 🔴 거북목
    else
      setRGB(false, true, false);  // 🟢 정상
  } 
  else {
    Serial.println("⚠️ Invalid measurement");
    setRGB(false, false, false); // ⚫ 센서 오류 시 LED OFF
  }

  delay(200);
}
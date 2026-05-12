# ⚡ Circuit Plan — 회로 설계 계획

> 현재 아두이노 기반 LED 피드백 회로와,  
> 추후 라즈베리파이 GPIO로 전환했을 때의 배선 계획을 담고 있습니다.

---

## 1. 현재 구성 — 아두이노 LED 피드백

### 개요
- PC의 `control_node.py` 가 정렬 완료를 판단
- 시리얼 통신(USB)으로 아두이노에 신호 전송
- 아두이노가 LED 점등

### 회로 구성

```
PC (control_node.py)
        │
    USB 시리얼
        │
   [Arduino UNO]
        │
   Digital Pin 13 ──── 저항(220Ω) ──── LED(녹색) ──── GND
   Digital Pin 12 ──── 저항(220Ω) ──── LED(적색) ──── GND
```

### 핀 정의

| 핀 | 색상 | 의미 |
|----|------|------|
| D13 | 녹색 LED | 정렬 완료 |
| D12 | 적색 LED | 정렬 중 / 오차 있음 |

### 아두이노 시리얼 프로토콜
```
수신 문자  동작
'A'     → 녹색 LED ON, 적색 LED OFF (Aligned)
'R'     → 적색 LED ON, 녹색 LED OFF (Running)
'S'     → 모든 LED OFF (Stop)
```

---

## 2. 전환 구성 — 라즈베리파이 GPIO 직접 제어

### 개요
- 아두이노 없이 라즈베리파이 GPIO 핀으로 직접 LED / 부저 제어
- `control_node.py` 에서 `RPi.GPIO` 또는 `gpiozero` 로 직접 출력
- 시리얼 통신 불필요 → 지연 감소

### 회로 구성

```
[Raspberry Pi 5]
        │
GPIO 17 ──── 저항(330Ω) ──── LED(녹색) ──── GND   ← 정렬 완료
GPIO 27 ──── 저항(330Ω) ──── LED(적색) ──── GND   ← 정렬 중
GPIO 22 ──── 저항(1kΩ)  ──── 부저(Active) ── GND  ← 정렬 완료 알림
        │
GPIO 16 ──┐
GPIO 20 ──┤ L298N 모터드라이버 IN1~IN4          ← 모터 방향 제어
GPIO 21 ──┤
GPIO 26 ──┘
        │
GPIO 12 ──── L298N ENA (PWM)                   ← 좌측 모터 속도
GPIO 13 ──── L298N ENB (PWM)                   ← 우측 모터 속도
```

### GPIO 핀 정의

| GPIO | 역할 | 종류 |
|------|------|------|
| GPIO 17 | 녹색 LED (정렬 완료) | Digital OUT |
| GPIO 27 | 적색 LED (정렬 중) | Digital OUT |
| GPIO 22 | 부저 (정렬 완료 알림) | Digital OUT |
| GPIO 16 | L298N IN1 (모터A 방향) | Digital OUT |
| GPIO 20 | L298N IN2 (모터A 방향) | Digital OUT |
| GPIO 21 | L298N IN3 (모터B 방향) | Digital OUT |
| GPIO 26 | L298N IN4 (모터B 방향) | Digital OUT |
| GPIO 12 | L298N ENA (모터A 속도) | PWM OUT |
| GPIO 13 | L298N ENB (모터B 속도) | PWM OUT |

### 전원 설계 (중요)

```
[리튬 배터리 12V]
        ├──── L298N 모터 전원 (12V)
        └──── 강압 컨버터(12V→5V) ──── 라즈베리파이 5V 전원
```

> ⚠️ 모터와 라즈베리파이 전원은 반드시 분리할 것.  
> 모터 기동 시 전압 강하로 라즈베리파이가 리셋될 수 있음.

---

## 3. 현재 vs 전환 비교

| 항목 | 아두이노 (현재) | 라즈베리파이 GPIO (전환) |
|------|----------------|--------------------------|
| LED 제어 | 시리얼 통신 경유 | GPIO 직접 출력 |
| 모터 제어 | 없음 (Gazebo) | GPIO PWM → L298N |
| 추가 부품 | Arduino UNO | L298N, 강압 컨버터 |
| 지연 | 시리얼 통신 지연 있음 | 거의 없음 |
| 코드 변경 | arduino/*.ino | control_node.py + motor_driver_node.py |

---

## 4. 라즈베리파이 GPIO 제어 코드 예시

```python
# motor_driver_node.py (예시)
import RPi.GPIO as GPIO
import rclpy
from geometry_msgs.msg import Twist

# 핀 설정
IN1, IN2 = 16, 20   # 모터A 방향
IN3, IN4 = 21, 26   # 모터B 방향
ENA, ENB = 12, 13   # PWM 속도
LED_GREEN = 17
LED_RED   = 27
BUZZER    = 22

GPIO.setmode(GPIO.BCM)
# ... (초기화 생략)

def cmd_vel_callback(msg):
    linear  = msg.linear.x
    angular = msg.angular.z
    # angular 값으로 좌/우 모터 속도 차등 제어
    # ...
```

---

## 📝 참고

- 전환 비전 전체 계획: `hardware_vision/EXTENSION_PLAN.md`
- 현재 아두이노 코드: `arduino/led_feedback/led_feedback.ino`

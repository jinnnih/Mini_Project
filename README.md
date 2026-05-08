# 🚗 Vision-Guided Parking & Carwash Alignment System

**ROS2 + OpenCV 기반 차량 정렬 유도 시스템**  
K-Digital 스마트 모빌리티 자율주행 부트캠프 — 연희직업학교

![ROS2](https://img.shields.io/badge/ROS2-Jazzy-blue)
![OpenCV](https://img.shields.io/badge/Vision-OpenCV_4.6-teal)
![Gazebo](https://img.shields.io/badge/Sim-Gazebo_8.11-orange)
![Docker](https://img.shields.io/badge/Env-Docker-blue)
![XQuartz](https://img.shields.io/badge/GUI-XQuartz-purple)
![Python](https://img.shields.io/badge/Lang-Python-yellow)

---

## 🖥 개발 환경

| 구분 | 내용 |
|------|------|
| **호스트 머신** | MacBook Pro M2 (macOS) |
| **가상화** | VMware Fusion → Ubuntu 26.04 |
| **ROS 실행** | Docker 컨테이너 (`ros:jazzy` 이미지) |
| **ROS 버전** | ROS2 Jazzy |
| **Gazebo 버전** | Gazebo Sim 8.11.0 |
| **OpenCV 버전** | 4.6.0 |
| **GUI 출력** | XQuartz (Mac → Docker GUI 포워딩) |
| **영상 입력** | Gazebo 가상 카메라 (`/camera/image_raw` 토픽) |
| **편집기** | VS Code (Mac + Docker 양쪽 사용) |

> ⚠️ M2 Mac 환경 특이사항: Ubuntu ARM64 Desktop ISO 미지원으로 Docker 기반 개발환경 채택. XQuartz로 Gazebo GUI를 Mac 화면에 포워딩.

---

## 🛠 기술 스택

| Category | Technology |
|----------|------------|
| Robotics | ROS2 Jazzy, Gazebo Sim 8.11 |
| Vision | OpenCV 4.6, Roboflow |
| Hardware | Arduino (LED 피드백) |
| Language | Python, C++ |
| Infra | Docker (`ros:jazzy`), VMware, XQuartz |

---

## 📁 프로젝트 구조

```
.
├── scripts/
│   ├── vision_node.py     # OpenCV 차선 검출 + 오차 계산 → ROS2 퍼블리시
│   └── control_node.py    # 오차 기반 cmd_vel 제어 + 정렬 판단 로직
├── simulation/            # Gazebo 월드 파일, 카메라 설정
├── arduino/               # Arduino: 정렬 상태별 LED 피드백
└── README.md
```

---

## 🧠 시스템 파이프라인

```mermaid
flowchart TD
    A[🎥 Gazebo 가상 카메라] -->|/camera/image_raw| B[cv_bridge 변환]
    B --> C[OpenCV 처리\nHSV → ROI → Canny → Hough]
    C --> D[차선 중심 오차 계산]
    D -->|오차값 퍼블리시| E[ROS2 Topic]
    E --> F[Control Node\ncmd_vel 생성]
    F --> G[🚗 Gazebo 차량 제어]
    F --> H[💡 Arduino LED 피드백]
```

---

## 📅 개발 일정 (매주 금요일)

| 회차 | 날짜 | 주제 | 주요 작업 | 결과물 |
|------|------|------|-----------|--------|
| ✅ Day 1 | 04.24 (금) | 환경 설정 | VMware Ubuntu 설치, ROS2 버전 충돌 → Docker 채택, ros:jazzy 컨테이너 구축, Gazebo 8.11 설치, XQuartz GUI 세팅 | 개발환경 구축 완료 |
| 👉 Day 2 | 05.08 (금) | Vision Pipeline | HSV + Canny + Hough 차선 검출, 오차 계산 | 차선 검출 영상 + 오차값 출력 |
| ⬜ Day 3 | 05.15 (금) | ROS2 + Gazebo 통합 | vision_node ↔ control_node, cmd_vel 제어 | Gazebo 차량 정렬 시뮬레이션 |
| ⬜ Day 4 | 05.22 (금) | 통합 + 마무리 | Arduino LED 연동, 시스템 통합 테스트 | 데모 영상 + 포트폴리오 완성 |

---

## 💡 핵심 기능

- **Precise Alignment** — 픽셀 기반 차선 중심 오차 계산으로 정밀 정렬
- **Dual Mode** — 주차장 / 세차장 모드 전환 지원
- **Hybrid Vision** — OpenCV 전통 기법 + Roboflow AI 데이터 활용
- **Hardware Feedback** — Arduino LED로 정렬 상태 실시간 표시
- **Full Simulation** — Gazebo 가상환경에서 실제 로봇 없이 검증

---

## ▶️ 실행 방법

> 🔧 **Day 4 마감 후 실제 명령어로 업데이트 예정**

### 0. 사전 준비 (최초 1회)
```bash
# Mac에 XQuartz 설치 후 로그아웃/로그인
brew install --cask xquartz
```

### 1. XQuartz 실행 및 Docker 컨테이너 시작
```bash
# Mac 터미널에서
xhost + 127.0.0.1
docker exec -it ros2_jazzy bash
```

### 2. 컨테이너 안에서 ROS2 + Gazebo 환경 설정
```bash
source /opt/ros/jazzy/setup.bash
export DISPLAY=host.docker.internal:0
```

### 3. Gazebo 시뮬레이션 실행
```bash
# TODO: launch 파일명 확정 후 업데이트
ros2 launch simulation parking_world.launch.py
```

### 4. Vision 노드 실행
```bash
ros2 run parking_alignment vision_node
```

### 5. Control 노드 실행
```bash
ros2 run parking_alignment control_node
```

---

## ✨ Optional (시간 여유 시)

- YOLO 모델 적용
- Flask 웹 대시보드
- 일본어 UI (전공 활용)

---

## 👤 Developer

- **과정** : K-Digital 스마트 모빌리티 자율주행 부트캠프
- **학교** : 연희직업학교

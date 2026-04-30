# 🚗 Vision-Guided Parking & Carwash Alignment System

ROS & OpenCV 기반 차량 정렬 유도 시스템

------------------------------------------------------------------------

## 📁 Project Structure

    .
    ├── arduino/          # Arduino: 상태 표시 (LED)
    ├── scripts/          # ROS 노드
    │   ├── vision_node.py    # OpenCV 인식 처리
    │   └── control_node.py   # 제어 로직 (cmd_vel)
    ├── simulation/       # Gazebo 환경
    └── README.md

------------------------------------------------------------------------

## 🛠 Tech Stack

  Category   Technology
  ---------- --------------------
  Robotics   ROS Noetic, Gazebo
  Vision     OpenCV, Roboflow
  Hardware   Arduino
  Language   Python, C++

------------------------------------------------------------------------

## 📅 Progress Log

### 🟢 Week 1 --- Hardware & Environment (04.24)

-   ROS Noetic + OpenCV 개발 환경 구축 완료\
-   cv_bridge 기반 ROS ↔ OpenCV 연동 검증\
-   Arduino 시리얼 통신 구성 및 데이터 송수신 확인

------------------------------------------------------------------------

### ⚪ Week 2 --- Vision (05.08)

-   HSV + ROI 기반 영상 전처리 구성\
-   Canny & Hough Transform으로 차선 검출 구현\
-   Roboflow 데이터셋 적용 및 인식 성능 테스트

------------------------------------------------------------------------

### ⚪ Week 3 --- AI & Logic (05.15)

-   차량 중심 대비 차선 중심 오차 계산 구현\
-   오차 기반 정렬 상태 판단 로직 설계\
-   주차장 / 세차장 모드 분리 설계

------------------------------------------------------------------------

### ⚪ Week 4 --- Integration (05.22)

-   ROS Topic 기반 cmd_vel 제어 구현\
-   Gazebo 차량 정렬 시뮬레이션 완료\
-   Arduino LED 상태 피드백 연동\
-   시스템 통합 테스트 및 시연 준비

------------------------------------------------------------------------

## 🧠 System Architecture

    Camera / Gazebo
            ↓
         OpenCV
            ↓
       Error Calc
            ↓
         ROS Topic
            ↓
       Control Node
            ↓
     Gazebo / Arduino

------------------------------------------------------------------------

## 💡 Core Features

-   Precise Alignment: 픽셀 기반 오차 계산 정렬\
-   Dual Mode: 주차장 / 세차장 모드 지원\
-   Hybrid Vision: OpenCV + Roboflow 데이터 활용\
-   Hardware Feedback: Arduino LED 상태 표시

------------------------------------------------------------------------

## 🚀 Optional (시간 여유 시)

-   YOLO 적용
-   Flask 대시보드
-   일본어 UI

------------------------------------------------------------------------

## 📌 Key Point

-   Vision + Control 통합 프로젝트\
-   시뮬레이션 + 하드웨어 연동\
-   AI 데이터 활용 기반 확장 구조

------------------------------------------------------------------------

## 👤 Developer

-   K-Digital 스마트 모빌리티 부트캠프

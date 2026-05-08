# 📋 AutoWash EasyAlign Bot — 개발 로그

> 다른 Claude 인스턴스가 이 파일을 읽으면 프로젝트 진행 상황을 바로 파악할 수 있습니다.
> README.md에 전체 프로젝트 개요가 있으니 함께 참고하세요.

---

## ✅ Day 1 — 2025-04-24 (완료)

**주제**: 환경 설정

- Docker `ros:jazzy` 컨테이너 구축
- Gazebo Sim 8.11 설치
- VS Code Dev Containers 세팅
- ROS2 Jazzy 워크스페이스 초기화

---

## ✅ Day 2 — 2026-05-08 (완료)

**주제**: Vision Pipeline + Gazebo 연결 준비

### 완성된 기능

#### vision_node.py
- HSV 필터링으로 주황색 기둥 검출 (H:10~20, S:200~255, V:200~255)
- findContours로 좌/우 기둥 윤곽 추출
- 기둥 중심 오차 계산 (`error = pillar_center - car_center`)
- `/lane_error` 토픽으로 오차값 퍼블리시 (Float32)
- **ROS2 이미지 토픽 구독** (`/camera/image_raw`) — cv_bridge 사용
- Gazebo 카메라 없을 때 테스트 이미지 자동 대체 (폴백)
- 결과 이미지 저장: `/home/zeenee/result.png`

#### control_node.py
- `/lane_error` 구독 → PID 제어 계산
- `/cmd_vel` 토픽으로 조향 명령 퍼블리시 (Twist)
- 오차 10px 이내 → 정렬 완료 판단 후 정지
- PID 게인: Kp=0.005, Ki=0.0001, Kd=0.002

#### 두 노드 통신 테스트 결과
```
[vision_node] Pillar error: 20.00px
[control_node] ↰ 좌측 조향 | error: 20.0px | steering: 0.142
```
→ lane_error 토픽 통신 정상 확인 ✅

#### Gazebo 세계 파일 (carwash.world)
- gz-sim 8 필수 시스템 플러그인 추가:
  - `gz-sim8-physics-system`
  - `gz-sim8-user-commands-system`
  - `gz-sim8-scene-broadcaster-system`
  - `gz-sim8-sensors-system`
- 세차장 환경: 주황색 기둥 2개, 노란 레일, 회색 바닥
- **로봇 차량 모델 world 파일에 직접 포함**:
  - base_link (차체), 좌/우 바퀴, 카메라 링크
  - `gz-sim8-diff-drive-system` 플러그인 (cmd_vel 수신 → 바퀴 제어)
  - 카메라 센서: 640×480, 30fps, `/camera/image_raw` 토픽
- SDF 유효성 검사 통과 (`gz sdf -k` → Valid)

#### launch 파일 (carwash.launch.py)
- `ros_gz_bridge` 추가:
  - `/camera/image_raw`: gz → ROS2 (sensor_msgs/Image)
  - `/cmd_vel`: ROS2 → gz (geometry_msgs/Twist)
- 월드 경로: `ament_index`로 자동 탐색

#### package.xml
- `cv_bridge`, `ros_gz_bridge` 의존성 추가

### 오늘 확인된 제약사항
- **VMware 3D 가속 미활성화** → Gazebo 카메라 센서 렌더링 불가
  - 오류: `VMware: No 3D enabled (0, Success)`
  - 원인: M2 Mac + VMware Fusion에서 3D 가속 설정이 꺼진 상태
  - 해결: VM 종료 후 VMware Fusion → Settings → Display → "Accelerate 3D Graphics" 체크

---

## ⬜ Day 3 — 2026-05-15 (예정)

**주제**: ROS2 + Gazebo 통합

### Day 3 시작 전 체크리스트
- [ ] VMware Fusion → Display → **"Accelerate 3D Graphics"** 활성화
- [ ] VM 재시작 후 `glxinfo | grep renderer` 로 확인
      → `SVGA3D` 또는 `llvmpipe` 나오면 성공

### Day 3 작업 목표
1. Gazebo 카메라 렌더링 확인 (`/camera/image_raw` 토픽 등장 여부)
2. `ros2 launch parking_vision carwash.launch.py` 전체 실행
3. Gazebo 차량이 vision_node 오차값 기반으로 실제 이동하는지 확인
4. 기둥 중앙 정렬 후 자동 정지 확인

### Day 3 실행 명령어
```bash
# 터미널 하나에서:
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch parking_vision carwash.launch.py
```

---

## ⬜ Day 4 — 2026-05-22 (예정)

**주제**: 통합 + 마무리

- Arduino LED 연동 (정렬 완료 시 점등)
- 시스템 통합 테스트
- 데모 영상 촬영
- 포트폴리오 완성

---

## 📁 주요 파일 위치

```
ros2_ws/src/Mini_Project/src/parking_vision/
├── parking_vision/
│   ├── vision_node.py       # 메인 비전 노드 (수정됨)
│   └── control_node.py      # PID 제어 노드
├── simulation/
│   ├── worlds/carwash.world # Gazebo 세계 파일 (수정됨)
│   └── models/carwash_pillar/model.sdf
├── launch/
│   └── carwash.launch.py    # 전체 실행 launch (수정됨)
├── package.xml              # 의존성 추가됨
└── setup.py
```

## 🛠 빌드 방법

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select parking_vision
source install/setup.bash
```

---

## 💬 Claude에게

- 사용자는 한국어로 대화합니다. 한국어로 답변해주세요.
- 영어 타이핑만 가능하지만 한국어를 읽고 씁니다.
- 이 프로젝트는 K-Digital 스마트 모빌리티 자율주행 부트캠프 미니 프로젝트입니다.
- GitHub: https://github.com/jinnnih/Mini_Project

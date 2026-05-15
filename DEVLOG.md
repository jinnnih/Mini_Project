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

## ✅ Day 2 — 2026-05-08 (완료, 추가 세션 포함)

**주제**: Vision Pipeline + Gazebo 완전 통합

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

### 추가 세션 — Gazebo 완전 통합 완료

#### 문제 해결 과정
1. **패키지 구조 버그 발견**: `colcon`이 `src/Mini_Project/src/` (바깥 패키지)를 빌드하는데, 수정은 `src/Mini_Project/src/parking_vision/` (안쪽)에만 했던 문제 → 바깥 경로 파일 동기화로 해결
2. **VMware 3D 가속**: VMware Fusion → Settings → Display → "Accelerate 3D Graphics" 활성화
3. **소프트웨어 렌더링**: 환경변수 `LIBGL_ALWAYS_SOFTWARE=1 MESA_GL_VERSION_OVERRIDE=4.5` 추가 → Gazebo GUI + 카메라 센서 모두 정상 렌더링
4. **기둥 색상 조정**: SDF에 `<emissive>0.8 0.3 0 1</emissive>` 추가 → 조명에 관계없이 주황색 유지
5. **HSV 범위 조정**: `H:10~20, S:200, V:200` → `H:5~35, S:100, V:80` (소프트웨어 렌더링 색상 대응)

#### 최종 확인된 동작
```
[vision_node] Pillar error: -1.00px   ← 기둥 감지 성공!
L:56 R:584                             ← 좌/우 기둥 X좌표
Error: 0.0px (화면 출력)               ← 거의 정중앙 정렬
```

#### 확인된 토픽 (전체 파이프라인)
- `/camera/image_raw` — Gazebo → ros_gz_bridge → vision_node ✅
- `/lane_error` — vision_node → control_node ✅
- `/cmd_vel` — control_node → ros_gz_bridge → Gazebo DiffDrive ✅
- `/model/robot_car/odometry` — 로봇 위치 정보 ✅

#### Gazebo 실행 명령어 (소프트웨어 렌더링)
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
DISPLAY=:0 LIBGL_ALWAYS_SOFTWARE=1 MESA_GL_VERSION_OVERRIDE=4.5 \
  gz sim ~/ros2_ws/install/parking_vision/share/parking_vision/simulation/worlds/carwash.world -r
```
또는 launch 파일로 전체 실행:
```bash
ros2 launch parking_vision carwash.launch.py
```

---

## ✅ Day 3 — 2026-05-15 (완료)

**주제**: 3단계 자율주행 시스템 완성 + 전체 시뮬레이션 검증

### 완성된 기능

#### 3-Phase 상태머신 (vision_node.py)

| 단계 | 이름 | 동작 | 전환 조건 |
|------|------|------|-----------|
| Phase 1 | PARKING | 파란 마커(HSV 100-130) 감지 + 정렬 | marker_found=True + abs(error)<25px × 8틱 |
| Phase 2 | LINE_FOLLOW | 직선 전진 (0.2 m/s, steering=0) | phase2_ticks>200 + pillar_seen × 8틱 |
| Phase 3 | PILLAR_ALIGN | 주황 기둥 감지 + PID 정렬 | pillar_found=True + abs(error)<10px × 5틱 |
| STOPPED | — | 정지 | — |

#### 이중 카메라 합성 뷰
- `/camera/image_raw` — 로봇 1인칭 카메라 (전방 주시)
- `/overhead/image_raw` — 탑뷰 카메라 (x=-1, z=10, pitch=π/2)
- 합성 이미지 저장: `/home/zeenee/result.png`

#### 월드 레이아웃 (carwash.world)
- x=-5: 로봇 시작 위치
- x=-3.5: 파란 정차 마커 (Phase 1 타깃)
- x=-3 ~ x=2.5: 흰 가이드 라인
- x=3, y=±1.2: 주황 기둥 2개 (Phase 3 타깃)

### 해결된 버그

1. **노드 이중 실행 → 상태 진동** (`PARKING↔LINE_FOLLOW` 빠른 토글)
   - 원인: 구 프로세스 미종료 상태에서 재실행
   - 해결: 실행 전 `ps aux | grep -E "vision|control|gz|ros2" | ... | xargs -r kill -9`

2. **error=0이 Phase 전환 차단**
   - 원인: 마커가 화면 정중앙이면 error=0 → 이전 조건 `error != 0` 차단
   - 해결: `marker_found` 불리언 플래그 도입

3. **Phase 2→3 너무 이른 전환** (주행 4초 만에 기둥 감지)
   - 원인: 소프트웨어 렌더링에서 emissive 기둥이 6m 거리에서도 큰 면적
   - 해결: `phase2_ticks > 200` 타임가드 (20초 이상 주행 후에만 기둥 체크)

4. **PID 적분 windup → 급격한 회전**
   - 원인: Phase 2 직선 주행 중 적분 누적 → steer=-0.36 → 180도 회전
   - 해결: 클램핑 `max(-80, min(80, integral + error))` + Phase 2에서 angular.z=0 고정

5. **Phase 3에서 기둥 미감지** (error=0.0 계속)
   - 원인: `h > w * 1.2` 조건이 기둥 하단부(납작한 형태)를 필터링
   - 해결: `h > w * 0.3`으로 완화, 면적 기준 150→100px

6. **Phase 3 STOPPED 미도달**
   - 해결: `pillar_found=True + abs(error)<10px × 5틱` 정상 정렬 완료
   - 폴백: `phase3_ticks > 50` (5초 기둥 미감지 → 기둥 사이 진입으로 간주)

### 최종 시뮬레이션 결과 (launch_v7.txt)

```
[vision_node] Vision Node Started | Phase 1: PARKING DETECT
[vision_node] → Phase 2: LINE FOLLOW 시작         ← 파란 마커 정렬 완료
[vision_node] [DRIVE] tick:200/200 pillar_seen:0  ← 20초 직선 주행
[vision_node] → Phase 3: PILLAR ALIGN 시작        ← 기둥 근접 감지
[vision_node] [PHASE3] error: 43px → 22px → 8px  ← PID 수렴
[vision_node] ✅ 정렬 완료! STOPPED               ← 완료!
```

**result.png**: 탑뷰에서 파란 로봇이 주황 기둥 두 개 사이 정중앙에 정렬 확인 ✅

### Day 3 실행 명령어
```bash
# 구 프로세스 정리
ps aux | grep -E "vision|control|gz|ros2" | grep -v grep | awk '{print $2}' | xargs -r kill -9

# 빌드 후 실행
source /opt/ros/jazzy/setup.bash && colcon build --packages-select parking_vision
source install/setup.bash
LIBGL_ALWAYS_SOFTWARE=1 MESA_GL_VERSION_OVERRIDE=4.5 ros2 launch parking_vision carwash.launch.py
```

---

## ✅ Day 3 Part 2 — 2026-05-15 (완료)

**주제**: U자형 경로 + 세차장 세계 리빌드 + 360도 바퀴 개념 도입

### 배경 / 동기

Day 3 기본 시뮬레이션(직선 주행)이 완료됐지만 세계가 너무 단순했음.
- "세차장이라고 말 안 하면 모를 정도" → 세차장 건물, 커브, 도로 레인 마킹 필요
- 직선 단순 경로 → U자형(직진 → 우회전 → 직진 → 우회전 → 직진) 경로로 개선
- 현대 360도 바퀴(메카넘/옴니 휠) 개념 도입 요청

---

### 변경 사항

#### 1. Gazebo 세계 전면 재구성 (`carwash.world`)

| 구성요소 | 설명 |
|---|---|
| 도로 세그먼트 | `road_seg1`(동쪽), `road_seg2`(남쪽), `road_seg3`(서쪽) 3개 구간 |
| 커브 | 좌우 도로 경계 커브 모델 추가 |
| 흰색 레인 마킹 | 세그먼트별 중앙선 + 코너 대각선 마킹 (emissive 0.9) |
| 파란 정차 마커 | x=-3, y=0 (Phase 1 타깃) |
| 세차장 건물 | 북벽/남벽/후벽/지붕/캐노피 회색 구조물 |
| 주황 기둥 | `pillar_north`(0, -2.2), `pillar_south`(0, -3.8) + 상단 크로스바 |
| 오버헤드 카메라 | (-0.4, -1.5, z=5.5), pitch=π/2, FOV=1.5708 |

**U자형 레이아웃 (x-y 평면):**
```
로봇시작(-4,0.5) ──→ 파란마커(-3,0) ──→ 코너1(2,0)
                                              ↓
                                         코너2(2,-3)
                                              ↓
세차장입구(0,-3) ←──────────────────────────
```

#### 2. 레인 추종 (`vision_node.py` — `_follow_lane`)

- 하단 40% ROI에서 흰색 픽셀(H:0-180, S:0-35, V:200-255) 검출
- 최대 윤곽 중심 → error = cx - width//2
- Seg1/Seg2 직선 구간에서 정상 동작 확인 (error=1~3px)
- **코너 문제**: 90° 코너에서 레인이 소실되면 error=0 → 직진해버림

#### 3. U자형 코너 해결 — 타이밍 기반 웨이포인트 시퀀스 (`control_node.py`)

순수 레인 추종으로는 코너를 신뢰성 있게 돌기 어려움.
→ Phase 2를 5개 서브-상태로 분리:

| 서브-상태 | 동작 | 틱 수 | 시간 (10Hz) |
|---|---|---|---|
| SEG1 (동진) | linear.x=0.15, angular.z=0 | 380 | ~38s |
| TURN1 (우회전) | linear.x=0, angular.z=-0.8 | 22 | ~2.2s |
| SEG2 (남진) | linear.x=0.15, angular.z=0 | 200 | ~20s |
| TURN2 (우회전) | linear.x=0, angular.z=-0.8 | 22 | ~2.2s |
| SEG3 (서진) | linear.x=0.15, angular.z=0 | — | 기둥 감지까지 |

- Phase 전환 시 `phase2_sub`, `phase2_ctrl_ticks` 리셋
- SEG3 진입 후 vision_node가 기둥 감지 시 Phase 3 자동 전환

#### 4. 360도 바퀴 (메카넘/옴니 휠) 개념 도입

현대 자동차의 360도 이동 바퀴 개념을 코드에 반영:

- **Phase 1 (PARKING)**: 현재 `angular.z`로 회전 정렬 → 메카넘 시 `linear.y`로 횡이동 정렬 가능
- **Phase 3 (PILLAR_ALIGN)**: 기둥 오차에 `linear.y` 적용 시 더 정밀한 횡이동 정렬 가능
- DiffDrive 플러그인은 `linear.y` 무시 → 메카넘 전환 시 플러그인을 `gz-sim8-mecanum-drive-system`으로 교체 필요
- 코드 내 주석으로 업그레이드 포인트 명시:
  ```python
  # 메카넘 휠(360도) 업그레이드 시: linear.y로 횡이동 정렬
  # twist.linear.y = -lateral_error * Kp_lateral
  ```

#### 5. Phase 2→3 타임가드 조정

- `phase2_ticks > 500` 유지 (총 틱 SEG1+TURN1+SEG2+TURN2 ≈ 624이므로 SEG3 진입 즈음에 자동 해제)

---

### 확인된 동작

| 항목 | 결과 |
|---|---|
| 레인 추종 (직선 구간) | ✅ error=1~3px, 흰 선 박스 result.png 확인 |
| 코너 통과 | ✅ 타이밍 시퀀스로 해결 (설계 완료) |
| 세차장 건물/기둥 렌더링 | ✅ 소프트웨어 렌더링에서 emissive 색상 정상 |

---

## ⬜ Day 4 — 2026-05-22 (예정)

**주제**: 통합 + 마무리

- 타이밍 시퀀스 틱값 현장 튜닝 (SEG1_TICKS, TURN_TICKS, SEG2_TICKS)
- 메카넘 휠 플러그인 교체 실험 (선택)
- Arduino LED 연동 (정렬 완료 시 점등)
- 시스템 통합 테스트 + 데모 영상 촬영
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

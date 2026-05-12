# 📔 AutoWash EasyAlign Bot — 개발일지

---

## Day 1 — 2025.04.24 (금)

### 목표
개발 환경 구축

### 작업 내용

**환경 선택 및 구성**
- MacBook Pro M2 환경에서 ROS2 개발환경 구성 시작
- Ubuntu ARM64 Desktop ISO 미지원 문제 확인 → Docker 기반 개발환경으로 전환 결정
- `ros:jazzy` 이미지 기반 Docker 컨테이너 구축
- Gazebo Sim 8.11.0 설치 완료
- XQuartz 설치 (Mac → Docker GUI 포워딩 목적)
- VS Code Dev Containers 익스텐션 설치 및 컨테이너 연결

### 결과물
- `ros2_jazzy` Docker 컨테이너 구축 완료
- ROS2 Jazzy + Gazebo 8.11 설치 완료
- VS Code ↔ Docker 컨테이너 연결 완료

### 이슈 및 해결
- M2 Mac ARM64 아키텍처로 인해 Ubuntu Desktop ISO 직접 설치 불가 → Docker로 우회

---

## Day 2 — 2025.05.08 (금)

### 목표
Vision Pipeline 구현 + ROS2 노드 통신 확인 + Gazebo 세차장 월드 작성

---

### 오전 — 환경 점검 및 프로젝트 방향 확정

**Docker 컨테이너 재실행**
- Docker Desktop 실행 오류 발생 (데몬 미실행 상태)
- Docker Desktop GUI에서 컨테이너 재생 버튼으로 해결
- `ros2_jazzy` 컨테이너 정상 실행 확인

```bash
docker ps
# CONTAINER ID: 7ff99cd485f3 | IMAGE: ros:jazzy | STATUS: Up
```

**개발환경 확인**
```
Python 3.12.3 ✅
OpenCV 4.6.0 ✅
ROS2 Jazzy ✅
```

**프로젝트 방향 확정**
- 기존: 단순 차선 따라가기
- 변경: 자동세차장 입구 기둥 인식 → 차량 정렬 유도
- 참고: 현대자동차그룹 AI 주차 로봇(Parking Robot) 컨셉 응용
- Gazebo 가상환경에서 시뮬레이션으로 구현하기로 결정

---

### 오후 1 — Vision Pipeline 구현

**vision_node.py 작성**

ROS2 Node 구조로 작성. 핵심 로직은 `detect_pillar_error()` 함수.

1차: 차선 검출 (HSV + Canny + Hough) 버전으로 시작
- 흰색 + 노란색 차선 동시 검출
- 좌/우 차선 분리 후 오차 계산
- 테스트 결과: `Lane error: -4.19px` 정상 출력 확인

```
[parking] Lane error: -4.19px ✅
```

**결과 이미지 시각화 확인**
- Docker → Mac으로 이미지 복사 후 확인
- 초록선(검출된 차선), 파란선(차선 중심), 빨간선(차량 중심) 정상 표시
- 오차 `-4.2px` → 차량이 중심에서 왼쪽으로 4.2픽셀 치우침 확인

---

### 오후 2 — 기둥 검출로 업그레이드

**프로젝트 핵심 타겟 변경**
- 차선 검출 → 세차장 입구 기둥 검출로 전환
- 기둥: 주황색 원통 2개 (좌/우)
- 검출 방식: HSV 필터 + findContours (Canny 제거)

**HSV 값 디버깅 과정**
```python
# 기둥 BGR값: (0, 120, 255)
# HSV 변환 결과 확인
hsv[240, 240] → [14, 255, 255]

# 필터 범위 확정
lower_orange = np.array([10, 200, 200])
upper_orange = np.array([20, 255, 255])
```

**findContours 적용**
- Canny 엣지 후 findContours → 면적 0 문제 발생
- 원인: 엣지 라인은 면적이 0
- 해결: 마스크에 직접 findContours 적용

```python
# 수정 전 (문제)
edges = cv2.Canny(mask, 50, 150)
contours, _ = cv2.findContours(edges, ...)  # 면적 0

# 수정 후 (해결)
contours, _ = cv2.findContours(mask, ...)  # 면적 정상
```

**기둥 검출 최종 확인**
```
윤곽선 수: 2
면적: 19160.0, x:380, y:0, w:41, h:480  ← 오른쪽 기둥
면적: 19160.0, x:220, y:0, w:41, h:480  ← 왼쪽 기둥
```

**비대칭 테스트 (오차 검증)**
- 기둥 위치를 의도적으로 비대칭 배치
- 결과: `Pillar error: 20.00px` → 오차 정상 계산 확인

---

### 오후 3 — control_node PID 업그레이드

**기존 control_node 분석**
- 단순 if/else 조향 로직 (오차 크면 꺾고, 작으면 정지)
- 문제: 차량이 지그재그로 흔들릴 수 있음

**PID 제어 추가**
```python
# PID 게인값
Kp = 0.005  # 비례: 오차가 크면 많이 꺾기
Ki = 0.0001  # 적분: 누적 오차 보정
Kd = 0.002  # 미분: 급격한 움직임 방지

steering = Kp * error + Ki * integral + Kd * derivative
```

**두 노드 통신 확인**
```
vision_node  →  /lane_error 토픽  →  control_node
```

```
[vision_node]:  [carwash] Pillar error: -4.19px
[control_node]: ✅ 정렬 완료! 정지
```

---

### 오후 4 — Gazebo 세차장 월드 + 패키지 구성

**Gazebo 세차장 월드 작성 (`carwash.world`)**
- 회색 바닥 (도로)
- 주황색 기둥 2개 (세차장 입구)
- 노란색 바닥 레일 2개

**차량 모델 작성 (`model.sdf`)**
- 차량 본체 (파란색 박스)
- 카메라 센서 장착 (`/camera/image_raw` 토픽)
- diff_drive 플러그인 (`/cmd_vel` 토픽)

**launch 파일 작성 (`carwash.launch.py`)**
- Gazebo + vision_node + control_node 한번에 실행

**패키지 빌드 성공**
```bash
colcon build --packages-select parking_vision
# Finished <<< parking_vision [0.53s] ✅
```

---

### 오후 5 — GitHub 업로드

**커밋 내역**
```
feat: vision_node - HSV 기둥 검출 + findContours + 오차 계산
feat: control_node - PID 제어 + 정렬 완료 판단 로직
feat: Gazebo 세차장 월드 - 입구 기둥 2개 + 바닥 레일 추가
feat: launch 파일 - ROS2 + Gazebo 통합 실행 설정
chore: ROS2 패키지 설정 - setup.py, package.xml, .gitignore
docs: README 업데이트 - 프로젝트명 AutoWash EasyAlign Bot + 배경 수정
```

---

### 오후 6 — Ubuntu 24.04 환경 전환 시작

**배경**
- Docker + XQuartz 환경에서 Gazebo GUI OpenGL 렌더링 문제 발생
- M2 Mac ARM64 + Docker 조합의 구조적 한계
- Ubuntu 24.04 Desktop ARM64 (Noble) VM으로 전환 결정

**진행 상황**
- Ubuntu 24.04.3 Desktop ARM64 ISO 다운로드 완료
- VMware Fusion에 Ubuntu 24.04 설치 완료
- VMware Tools 설치 (클립보드 공유 활성화)
- VM 설정: CPU 4코어, 메모리 6GB
- ROS2 Jazzy 설치 진행 중

---

### Day 2 결과물 요약

```
✅ vision_node.py — 주황색 기둥 HSV 검출 + findContours + 오차 계산 + ROS2 퍼블리시
✅ control_node.py — PID 제어 + 정렬 완료 판단
✅ carwash.world — Gazebo 세차장 입구 (기둥 2개 + 레일)
✅ model.sdf — 카메라 장착 차량 모델
✅ carwash.launch.py — 통합 실행 launch 파일
✅ 패키지 빌드 성공
✅ 두 노드 ROS2 토픽 통신 확인
✅ GitHub 커밋 6개 push 완료
✅ Ubuntu 24.04 VM 환경 구축 시작
```

### 다음 목표 (Day 3 — 05.15)
- Ubuntu 24.04에 ROS2 Jazzy + Gazebo 설치 완료
- Gazebo GUI 정상 실행 확인
- vision_node ↔ control_node ↔ Gazebo 차량 통합 연결
- 차량 정렬 시뮬레이션 동작 확인

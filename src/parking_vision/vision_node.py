import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Int32
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


PARKING = 0
LINE_FOLLOW = 1
PILLAR_ALIGN = 2
STOPPED = 3

PHASE_LABEL = {
    PARKING: 'PHASE1: PARKING DETECT',
    LINE_FOLLOW: 'PHASE2: LINE FOLLOW',
    PILLAR_ALIGN: 'PHASE3: PILLAR ALIGN',
    STOPPED: 'STOPPED',
}


class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')
        self.error_pub = self.create_publisher(Float32, 'lane_error', 10)
        self.phase_pub = self.create_publisher(Int32, 'vision_phase', 10)
        self.bridge = CvBridge()

        self.latest_frame = None
        self.overhead_frame = None

        self.create_subscription(Image, '/camera/image_raw', self.image_callback, 10)
        self.create_subscription(Image, '/overhead/image_raw', self.overhead_callback, 10)
        self.create_timer(0.1, self.timer_callback)

        self.phase = PARKING
        self.aligned_count = 0
        self.marker_found = False
        self.pillar_found = False
        self.pillar_seen_count = 0
        self.phase2_ticks = 0  # Phase 2 진입 후 경과 틱 (0.1s 단위)
        self.phase3_ticks = 0  # Phase 3 진입 후 경과 틱 (0.1s 단위)

        self.get_logger().info('Vision Node Started | Phase 1: PARKING DETECT')

    def image_callback(self, msg):
        self.latest_frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def overhead_callback(self, msg):
        self.overhead_frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def timer_callback(self):
        frame = self.latest_frame if self.latest_frame is not None else self._test_image()

        if self.phase == PARKING:
            result, error = self._detect_parking_marker(frame)
        elif self.phase == LINE_FOLLOW:
            # 직선 전진 단계: 기둥 감지 여부만 체크, 에러는 0으로 유지
            result, error = self._drive_to_pillars(frame)
        elif self.phase == PILLAR_ALIGN:
            result, error = self._detect_pillars(frame)
        else:
            result = frame.copy()
            error = 0.0
            cv2.putText(result, '✅ ALIGNED & STOPPED', (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        self._update_phase(error)

        composite = self._make_composite(result)
        cv2.imwrite('/home/zeenee/result.png', composite)

        err_msg = Float32()
        err_msg.data = float(error)
        self.error_pub.publish(err_msg)

        phase_msg = Int32()
        phase_msg.data = self.phase
        self.phase_pub.publish(phase_msg)

        self.get_logger().info(f'[{PHASE_LABEL[self.phase]}] error: {error:.1f}px')

    def _update_phase(self, error):
        if self.phase == PARKING:
            # marker_found=True이고 오차가 작으면 카운트 (error=0도 정렬 완료로 인정)
            if self.marker_found and abs(error) < 25.0:
                self.aligned_count += 1
                if self.aligned_count >= 8:  # 0.8초 정렬 유지
                    self.phase = LINE_FOLLOW
                    self.aligned_count = 0
                    self.get_logger().info('→ Phase 2: LINE FOLLOW 시작')
            else:
                self.aligned_count = 0

        elif self.phase == LINE_FOLLOW:
            self.phase2_ticks += 1
            # 최소 200틱(20초) 주행 후 기둥 근접 감지 허용
            if self.phase2_ticks > 200 and self.pillar_found:
                self.pillar_seen_count += 1
                if self.pillar_seen_count >= 8:
                    self.phase = PILLAR_ALIGN
                    self.aligned_count = 0
                    self.pillar_seen_count = 0
                    self.phase2_ticks = 0
                    self.phase3_ticks = 0
                    self.get_logger().info('→ Phase 3: PILLAR ALIGN 시작')
            elif not self.pillar_found:
                self.pillar_seen_count = 0
            if self.phase2_ticks % 20 == 0:  # 2초마다 진행 로그
                self.get_logger().info(
                    f'[DRIVE] tick:{self.phase2_ticks}/200 pillar_seen:{self.pillar_seen_count}')

        elif self.phase == PILLAR_ALIGN:
            self.phase3_ticks += 1
            if self.pillar_found and abs(error) < 10.0:
                self.aligned_count += 1
                if self.aligned_count >= 5:
                    self.phase = STOPPED
                    self.get_logger().info('✅ 정렬 완료! STOPPED')
            elif not self.pillar_found and self.phase3_ticks > 50:
                # 5초 이상 기둥 미감지 → 기둥 사이 진입 완료로 간주
                self.phase = STOPPED
                self.get_logger().info('✅ 기둥 사이 진입 완료! STOPPED')
            else:
                self.aligned_count = 0

    def _detect_parking_marker(self, frame):
        """파란색 정차구역 마커 검출."""
        height, width = frame.shape[:2]
        result = frame.copy()

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([100, 80, 60]), np.array([130, 255, 255]))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours or max(cv2.contourArea(c) for c in contours) < 150:
            self.marker_found = False
            cv2.putText(result, 'PARKING MARKER: 탐색중...', (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
            return result, 0.0

        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        cx = x + w // 2
        error = cx - width // 2
        self.marker_found = True

        cv2.rectangle(result, (x, y), (x + w, y + h), (255, 100, 0), 2)
        cv2.line(result, (cx, 0), (cx, height), (255, 50, 0), 2)
        cv2.line(result, (width // 2, 0), (width // 2, height), (0, 0, 200), 2)
        cv2.putText(result, f'PARKING | error:{error:.0f}px', (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 100, 0), 2)
        self._draw_aligned_count(result)
        return result, error

    def _detect_guide_line(self, frame):
        """흰색 바닥 유도선 검출 (하단 ROI)."""
        height, width = frame.shape[:2]
        result = frame.copy()

        roi_top = height // 2
        roi = frame[roi_top:, :]
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_roi, np.array([0, 0, 160]), np.array([180, 60, 255]))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours or max(cv2.contourArea(c) for c in contours) < 80:
            cv2.putText(result, 'LINE FOLLOW: 탐색중...', (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
            return result, 0.0

        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        cx = x + w // 2
        error = cx - width // 2

        cv2.rectangle(result, (x, y + roi_top), (x + w, y + h + roi_top), (0, 220, 220), 2)
        cv2.line(result, (cx, 0), (cx, height), (0, 200, 200), 2)
        cv2.line(result, (width // 2, 0), (width // 2, height), (0, 0, 200), 2)
        cv2.putText(result, f'LINE FOLLOW | error:{error:.0f}px', (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 220), 2)
        return result, error

    def _drive_to_pillars(self, frame):
        """Phase 2: 직선 전진. 기둥이 충분히 크게 보일 때(가까워졌을 때)만 Phase 3 전환."""
        height, width = frame.shape[:2]
        result = frame.copy()

        # 근거리 기둥 감지: 면적 800px 이상 = 약 1~2m 이내
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([5, 100, 80]), np.array([35, 255, 255]))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.pillar_found = any(
            cv2.contourArea(c) > 800
            for c in contours
            if cv2.contourArea(c) > 800
        )

        status = '기둥 근접 감지!' if self.pillar_found else '전진 중...'
        cv2.putText(result, f'DRIVE → CARWASH | {status}', (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 220), 2)
        cv2.putText(result, f'pillar_cnt:{self.pillar_seen_count}/8', (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 0), 2)
        return result, 0.0  # 항상 error=0 (직선 주행)

    def _detect_pillars(self, frame):
        """주황색 기둥 검출 (기존 로직)."""
        height, width = frame.shape[:2]
        result = frame.copy()

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([5, 100, 80]), np.array([35, 255, 255]))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        left_x = right_x = None

        for cnt in contours:
            if cv2.contourArea(cnt) < 100:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            if h > w * 0.3:
                cx = x + w // 2
                cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 0), 2)
                if cx < width // 2:
                    left_x = cx
                else:
                    right_x = cx

        car_center = width // 2

        if left_x is not None and right_x is not None:
            pillar_center = (left_x + right_x) // 2
        elif left_x is not None:
            pillar_center = left_x + 100
        elif right_x is not None:
            pillar_center = right_x - 100
        else:
            self.pillar_found = False
            cv2.putText(result, 'PILLAR: 탐색중...', (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
            return result, 0.0

        self.pillar_found = True

        error = pillar_center - car_center
        cv2.line(result, (pillar_center, 0), (pillar_center, height), (255, 50, 0), 2)
        cv2.line(result, (car_center, 0), (car_center, height), (0, 0, 200), 2)
        cv2.putText(result, f'PILLAR | error:{error:.0f}px', (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(result, f'L:{left_x} R:{right_x}', (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 0), 2)
        self._draw_aligned_count(result)
        return result, error

    def _draw_aligned_count(self, frame):
        h = frame.shape[0]
        cv2.putText(frame, f'align_cnt:{self.aligned_count}', (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

    def _make_composite(self, robot_view):
        """로봇 카메라 뷰 + 탑뷰 합성 이미지."""
        h, w = robot_view.shape[:2]

        if self.overhead_frame is not None:
            top_view = cv2.resize(self.overhead_frame, (w, h))
        else:
            top_view = np.zeros((h, w, 3), dtype=np.uint8)
            cv2.putText(top_view, 'TOP VIEW: 대기중', (w // 2 - 100, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)

        # 레이블 바 추가
        bar_h = 30
        for view, label, color in [
            (robot_view, 'ROBOT CAM', (50, 150, 255)),
            (top_view, 'TOP VIEW', (100, 255, 100)),
        ]:
            cv2.rectangle(view, (0, 0), (w, bar_h), (20, 20, 20), -1)
            cv2.putText(view, label, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        # 현재 단계 표시
        phase_text = PHASE_LABEL[self.phase]
        cv2.putText(robot_view, phase_text, (8, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        return np.hstack([robot_view, top_view])

    def _test_image(self):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (80, 80, 80)
        # 파란색 정차 마커 테스트
        cv2.rectangle(img, (260, 280), (380, 430), (200, 50, 0), -1)
        return img


def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Int32
from sensor_msgs.msg import Image
import cv2
import numpy as np
from cv_bridge import CvBridge

APPROACH = 0
ALIGN = 1
ENTER = 2
STOPPED = 3

PHASE_NAME = {
    APPROACH: 'APPROACH',
    ALIGN: 'ALIGN',
    ENTER: 'ENTER',
    STOPPED: 'STOPPED',
}


class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')
        self.bridge = CvBridge()

        self.create_subscription(Image, '/camera/image_raw', self.image_callback, 10)
        self.create_subscription(Image, '/overhead/image_raw', self.overhead_callback, 10)
        self.error_pub = self.create_publisher(Float32, 'lane_error', 10)
        self.phase_pub = self.create_publisher(Int32, 'vision_phase', 10)

        self.phase = APPROACH
        self.approach_count = 0
        self.aligned_count = 0
        self.enter_ticks = 0
        self.hub_found = False
        self.hub_px = 0
        self.latest_overhead = None

        self.get_logger().info('Vision Node Started | Phase: APPROACH')

    def overhead_callback(self, msg):
        try:
            self.latest_overhead = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception:
            pass

    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception:
            return

        result, error, hub_found, hub_px = self._detect_hubs(frame)
        self.hub_found = hub_found
        self.hub_px = hub_px

        self._update_phase(error)

        error_msg = Float32()
        error_msg.data = float(error)
        self.error_pub.publish(error_msg)

        phase_msg = Int32()
        phase_msg.data = self.phase
        self.phase_pub.publish(phase_msg)

        self.get_logger().info(
            f'[{PHASE_NAME[self.phase]}] hub:{hub_found} px:{hub_px} error:{error:.1f}px')

        self._save_result(result)

    def _detect_hubs(self, frame):
        """좌/우 절반 분리로 앞바퀴 허브 중심 오차 계산.
        소프트웨어 렌더링 노이즈에 강건한 모멘트 기반 감지."""
        height, width = frame.shape[:2]
        result = frame.copy()
        mid = width // 2

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([5, 100, 80]), np.array([35, 255, 255]))

        total_px = cv2.countNonZero(mask)
        if total_px < 80:
            cv2.putText(result, f'[{PHASE_NAME[self.phase]}] 휠허브 탐색중...',
                        (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
            return result, 0.0, False, 0

        # 이미지를 좌/우 절반으로 분리 → 각 절반의 무게중심 = 허브 중심
        left_mask = mask[:, :mid]
        right_mask = mask[:, mid:]

        left_px = cv2.countNonZero(left_mask)
        right_px = cv2.countNonZero(right_mask)

        if left_px < 40 or right_px < 40:
            cv2.putText(result, f'[{PHASE_NAME[self.phase]}] 허브 한쪽만 감지',
                        (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            return result, 0.0, False, 0

        M_l = cv2.moments(left_mask)
        M_r = cv2.moments(right_mask)

        if M_l['m00'] == 0 or M_r['m00'] == 0:
            return result, 0.0, False, 0

        left_cx = int(M_l['m10'] / M_l['m00'])
        left_cy = int(M_l['m01'] / M_l['m00'])
        right_cx = int(M_r['m10'] / M_r['m00']) + mid
        right_cy = int(M_r['m01'] / M_r['m00'])

        hub_mid_x = (left_cx + right_cx) // 2
        error = float(hub_mid_x - mid)

        # 시각화
        cv2.circle(result, (left_cx, left_cy), 10, (0, 255, 100), 3)
        cv2.circle(result, (right_cx, right_cy), 10, (0, 255, 100), 3)
        cv2.line(result, (hub_mid_x, 0), (hub_mid_x, height), (0, 220, 220), 2)
        cv2.line(result, (mid, 0), (mid, height), (0, 0, 220), 1)
        cv2.putText(result,
                    f'[{PHASE_NAME[self.phase]}] error:{error:.0f}px L:{left_px} R:{right_px}',
                    (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 220), 2)

        return result, error, True, left_px + right_px

    def _update_phase(self, error):
        if self.phase == APPROACH:
            # hub_px > 400: robot is within ~2m of the wheel hubs
            if self.hub_found and abs(error) < 40.0 and self.hub_px > 400:
                self.approach_count += 1
                if self.approach_count >= 5:
                    self.phase = ALIGN
                    self.approach_count = 0
                    self.aligned_count = 0
                    self.get_logger().info('→ Phase: ALIGN (횡이동 정렬 시작)')
            else:
                self.approach_count = 0

        elif self.phase == ALIGN:
            if self.hub_found and abs(error) < 8.0:
                self.aligned_count += 1
                if self.aligned_count >= 10:
                    self.phase = ENTER
                    self.aligned_count = 0
                    self.enter_ticks = 0
                    self.get_logger().info('→ Phase: ENTER (차량 하부 직진 진입)')
            elif self.hub_found:
                self.aligned_count = 0

        elif self.phase == ENTER:
            self.enter_ticks += 1
            if self.enter_ticks > 2500:
                self.phase = STOPPED
                self.get_logger().info('✅ STOPPED — 차량 하부 진입 완료!')

    def _save_result(self, robot_view):
        h, w = robot_view.shape[:2]
        if self.latest_overhead is not None:
            overhead = cv2.resize(self.latest_overhead, (w, h))
            combined = np.hstack([robot_view, overhead])
        else:
            combined = robot_view
        cv2.imwrite('/home/zeenee/result.png', combined)


def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
import cv2
import numpy as np


class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')
        self.publisher_ = self.create_publisher(Float32, 'lane_error', 10)
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.cap = cv2.VideoCapture(0)
        self.mode = 'carwash'
        self.get_logger().info(f'Vision Node Started | Mode: {self.mode}')

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            frame = self.create_test_image()

        result, error = self.detect_pillar_error(frame)

        cv2.imwrite('/home/result.png', result)

        msg = Float32()
        msg.data = float(error)
        self.publisher_.publish(msg)
        self.get_logger().info(f'[{self.mode}] Pillar error: {error:.2f}px')

    def create_test_image(self):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (80, 80, 80)
        # 왼쪽 기둥을 오른쪽으로 살짝 이동 (차가 왼쪽으로 치우친 상황)
        cv2.rectangle(img, (260, 0), (300, 480), (0, 120, 255), -1)
        cv2.rectangle(img, (380, 0), (420, 480), (0, 120, 255), -1)
        return img

    def detect_pillar_error(self, frame):
        height, width = frame.shape[:2]
        result = frame.copy()

        # 1. HSV 변환
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 2. 주황색 필터
        lower_orange = np.array([10, 200, 200])
        upper_orange = np.array([20, 255, 255])
        mask = cv2.inRange(hsv, lower_orange, upper_orange)

        # 3. 마스크에 바로 윤곽선 검출 (Canny 제거)
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        left_x = None
        right_x = None

        for cnt in contours:
            if cv2.contourArea(cnt) < 500:
                continue

            x, y, w, h = cv2.boundingRect(cnt)

            if h > w * 1.5:
                cx = x + w // 2
                cv2.rectangle(result, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.circle(result, (cx, height//2), 5, (0, 255, 0), -1)

                if cx < width // 2:
                    left_x = cx
                else:
                    right_x = cx

        # 4. 오차 계산
        car_center = width // 2

        if left_x is not None and right_x is not None:
            pillar_center = (left_x + right_x) // 2
        elif left_x is not None:
            pillar_center = left_x + 100
        elif right_x is not None:
            pillar_center = right_x - 100
        else:
            self.get_logger().warn('기둥 미검출')
            return result, 0.0

        error = pillar_center - car_center

        # 5. 시각화
        cv2.line(result, (pillar_center, 0),
                 (pillar_center, height), (255, 0, 0), 2)
        cv2.line(result, (car_center, 0),
                 (car_center, height), (0, 0, 255), 2)
        cv2.putText(result, f"Error: {error:.1f}px", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(result, f"L:{left_x} R:{right_x}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        return result, error


def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
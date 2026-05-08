import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')
        self.publisher_ = self.create_publisher(Float32, 'lane_error', 10)
        self.bridge = CvBridge()
        self.latest_frame = None

        self.subscription = self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10)
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.mode = 'carwash'
        self.get_logger().info(f'Vision Node Started | Mode: {self.mode}')

    def image_callback(self, msg):
        self.latest_frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def timer_callback(self):
        if self.latest_frame is not None:
            frame = self.latest_frame
        else:
            frame = self.create_test_image()

        result, error = self.detect_pillar_error(frame)
        cv2.imwrite('/home/zeenee/result.png', result)

        msg = Float32()
        msg.data = float(error)
        self.publisher_.publish(msg)
        self.get_logger().info(f'[{self.mode}] Pillar error: {error:.2f}px')

    def create_test_image(self):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (80, 80, 80)
        cv2.rectangle(img, (260, 0), (300, 480), (0, 120, 255), -1)
        cv2.rectangle(img, (380, 0), (420, 480), (0, 120, 255), -1)
        return img

    def detect_pillar_error(self, frame):
        height, width = frame.shape[:2]
        result = frame.copy()

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower_orange = np.array([5, 100, 80])
        upper_orange = np.array([35, 255, 255])
        mask = cv2.inRange(hsv, lower_orange, upper_orange)

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

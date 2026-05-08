import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from geometry_msgs.msg import Twist


class ControlNode(Node):
    def __init__(self):
        super().__init__('control_node')
        self.subscription = self.create_subscription(
            Float32, 'lane_error', self.error_callback, 10)
        self.publisher_ = self.create_publisher(Twist, 'cmd_vel', 10)

        # 정렬 완료 임계값 (픽셀)
        self.threshold = 10.0

        # PID 게인값
        self.Kp = 0.005
        self.Ki = 0.0001
        self.Kd = 0.002

        # PID 내부 상태
        self.prev_error = 0.0
        self.integral = 0.0

        self.get_logger().info('Control Node Started (PID)')

    def error_callback(self, msg):
        error = msg.data
        twist = Twist()

        if abs(error) < self.threshold:
            # 정렬 완료
            self.get_logger().info('✅ 정렬 완료! 정지')
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            self.integral = 0.0
            self.prev_error = 0.0
        else:
            # PID 계산
            self.integral += error
            derivative = error - self.prev_error
            steering = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
            self.prev_error = error

            twist.linear.x = 0.1  # 전진 속도
            twist.angular.z = -steering  # 조향

            direction = '↰ 좌측' if error > 0 else '↱ 우측'
            self.get_logger().info(
                f'{direction} 조향 | error: {error:.1f}px | steering: {steering:.4f}')

        self.publisher_.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = ControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
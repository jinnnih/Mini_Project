import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Int32
from geometry_msgs.msg import Twist


PARKING = 0
LINE_FOLLOW = 1
PILLAR_ALIGN = 2
STOPPED = 3

PHASE_NAME = {PARKING: 'PARKING', LINE_FOLLOW: 'LINE_FOLLOW',
              PILLAR_ALIGN: 'PILLAR_ALIGN', STOPPED: 'STOPPED'}


class ControlNode(Node):
    def __init__(self):
        super().__init__('control_node')
        self.create_subscription(Float32, 'lane_error', self.error_callback, 10)
        self.create_subscription(Int32, 'vision_phase', self.phase_callback, 10)
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)

        self.threshold = 10.0
        self.Kp = 0.005
        self.Ki = 0.0001
        self.Kd = 0.002
        self.prev_error = 0.0
        self.integral = 0.0

        self.phase = PARKING
        self.get_logger().info('Control Node Started | Phase 1: PARKING')

    def phase_callback(self, msg):
        new_phase = msg.data
        if new_phase != self.phase:
            self.phase = new_phase
            self.integral = 0.0
            self.prev_error = 0.0
            self.get_logger().info(f'→ Phase: {PHASE_NAME.get(self.phase)}')

    def error_callback(self, msg):
        error = msg.data
        twist = Twist()

        if self.phase == STOPPED:
            self.cmd_pub.publish(twist)
            return

        steering = self._pid(error)

        if self.phase == PARKING:
            # 정차구역 마커 정렬: 매우 천천히 전진하며 측면 보정
            twist.linear.x = 0.05
            twist.angular.z = -steering
            self.get_logger().info(
                f'[PARKING] error:{error:.1f}px steer:{steering:.4f}')

        elif self.phase == LINE_FOLLOW:
            # 직선 전진 (steering 없음) — 기둥 감지될 때까지 정속 주행
            twist.linear.x = 0.2
            twist.angular.z = 0.0
            self.get_logger().info('[DRIVE→CARWASH] 전진 중')

        elif self.phase == PILLAR_ALIGN:
            # 기둥 미감지(error=0)여도 천천히 전진 — vision_node가 STOPPED 전환 담당
            speed = 0.05 if abs(error) < self.threshold else 0.08
            twist.linear.x = speed
            twist.angular.z = -steering
            direction = '↰ 좌측' if error > 0 else ('↱ 우측' if error < 0 else '→ 직진')
            self.get_logger().info(
                f'[PILLAR_ALIGN] {direction} error:{error:.1f}px steer:{steering:.4f}')

        self.cmd_pub.publish(twist)

    def _pid(self, error):
        self.integral = max(-80.0, min(80.0, self.integral + error))  # windup 방지
        derivative = error - self.prev_error
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        self.prev_error = error
        return output


def main(args=None):
    rclpy.init(args=args)
    node = ControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

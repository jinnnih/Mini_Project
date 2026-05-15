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

# Phase 2 U자형 경로 서브-상태
SEG1 = 0   # 동쪽 직진
TURN1 = 1  # CW 90° 우회전
SEG2 = 2   # 남쪽 직진
TURN2 = 3  # CW 90° 우회전
SEG3 = 4   # 서쪽 직진 (세차장 입구 진입)

SEG1_TICKS = 380   # ~38s at 10Hz
TURN_TICKS = 22    # ~2.2s (90° turn at angular=0.8 rad/s)
SEG2_TICKS = 200   # ~20s
SEG3_LABEL = {SEG1: 'SEG1:동진', TURN1: 'TURN1:우회전',
              SEG2: 'SEG2:남진', TURN2: 'TURN2:우회전', SEG3: 'SEG3:서진→입구'}


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
        self.phase2_sub = SEG1
        self.phase2_ctrl_ticks = 0

        self.get_logger().info('Control Node Started | Phase 1: PARKING')

    def phase_callback(self, msg):
        new_phase = msg.data
        if new_phase != self.phase:
            self.phase = new_phase
            self.integral = 0.0
            self.prev_error = 0.0
            if new_phase == LINE_FOLLOW:
                self.phase2_sub = SEG1
                self.phase2_ctrl_ticks = 0
            self.get_logger().info(f'→ Phase: {PHASE_NAME.get(self.phase)}')

    def error_callback(self, msg):
        error = msg.data
        twist = Twist()

        if self.phase == STOPPED:
            self.cmd_pub.publish(twist)
            return

        steering = self._pid(error)

        if self.phase == PARKING:
            # 정차구역 마커 정렬: 천천히 전진하며 각도 보정
            # 메카넘 휠(360도) 업그레이드 시: linear.y로 횡이동 정렬
            # twist.linear.y = -steering  # (DiffDrive 미지원, 메카넘 휠 시 활성화)
            twist.linear.x = 0.05
            twist.angular.z = -steering
            self.get_logger().info(
                f'[PARKING] error:{error:.1f}px steer:{steering:.4f}')

        elif self.phase == LINE_FOLLOW:
            self.phase2_ctrl_ticks += 1

            if self.phase2_sub == SEG1:
                # 동쪽 직진
                twist.linear.x = 0.15
                twist.angular.z = 0.0
                if self.phase2_ctrl_ticks >= SEG1_TICKS:
                    self.phase2_sub = TURN1
                    self.phase2_ctrl_ticks = 0
                    self.get_logger().info('[LINE_FOLLOW] SEG1 완료 → TURN1 우회전 시작')

            elif self.phase2_sub == TURN1:
                # 첫 번째 CW 90° 우회전
                twist.linear.x = 0.0
                twist.angular.z = -0.8
                if self.phase2_ctrl_ticks >= TURN_TICKS:
                    self.phase2_sub = SEG2
                    self.phase2_ctrl_ticks = 0
                    self.get_logger().info('[LINE_FOLLOW] TURN1 완료 → SEG2 남진 시작')

            elif self.phase2_sub == SEG2:
                # 남쪽 직진
                twist.linear.x = 0.15
                twist.angular.z = 0.0
                if self.phase2_ctrl_ticks >= SEG2_TICKS:
                    self.phase2_sub = TURN2
                    self.phase2_ctrl_ticks = 0
                    self.get_logger().info('[LINE_FOLLOW] SEG2 완료 → TURN2 우회전 시작')

            elif self.phase2_sub == TURN2:
                # 두 번째 CW 90° 우회전
                twist.linear.x = 0.0
                twist.angular.z = -0.8
                if self.phase2_ctrl_ticks >= TURN_TICKS:
                    self.phase2_sub = SEG3
                    self.phase2_ctrl_ticks = 0
                    self.get_logger().info('[LINE_FOLLOW] TURN2 완료 → SEG3 서진(세차장 입구) 시작')

            elif self.phase2_sub == SEG3:
                # 서쪽 직진 — vision_node가 기둥 감지 후 Phase 3 전환 담당
                twist.linear.x = 0.15
                twist.angular.z = 0.0

            self.get_logger().info(
                f'[LINE_FOLLOW] {SEG3_LABEL[self.phase2_sub]} tick:{self.phase2_ctrl_ticks}')

        elif self.phase == PILLAR_ALIGN:
            # 기둥 오차 기반 PID 정렬
            # 메카넘 휠(360도) 업그레이드 시: linear.y로 횡이동 정렬 (더 정밀)
            # twist.linear.y = -steering  # (DiffDrive 미지원, 메카넘 휠 시 활성화)
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

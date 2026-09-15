import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.qos import QoSProfile, ReliabilityPolicy
from tf_transformations import euler_from_quaternion

topic1 = "cmd_vel"
topic2 = "odom"
rate_msg = 2

robot_pose = [0, 0, 0]


def odometry_callback(msg):
    robot_pose[0] = msg.pose.pose.position.x
    robot_pose[1] = msg.pose.pose.position.y
    robot_pose[2] = euler_from_quaternion(
        [
            msg.pose.pose.orientation.x,
            msg.pose.pose.orientation.y,
            msg.pose.pose.orientation.z,
            msg.pose.pose.orientation.w,
        ]
    )[2]


def main(args=None):
    rclpy.init(args=args)
    testNode = Node("test_node")

    controlVelocity = Twist()
    controlVelocity.linear.x = 4.0
    controlVelocity.linear.y = 0.0
    controlVelocity.linear.z = 0.0

    controlVelocity.angular.x = 0.0
    controlVelocity.angular.y = 0.0
    controlVelocity.angular.z = 8.0

    publisher = testNode.create_publisher(Twist, topic1, 10)
    subscriber = testNode.create_subscription(
        Odometry,
        topic2,
        odometry_callback,
        10,
    )
    _ = subscriber

    def timer_callback():
        testNode.get_logger().info(f"{robot_pose}")
        publisher.publish(controlVelocity)

    testNode.create_timer(1.0 / rate_msg, timer_callback)

    rclpy.spin(testNode)

    testNode.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

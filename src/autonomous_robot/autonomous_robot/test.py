import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

topic1 = "cmd_vel"
rate_msg = 2


def main(args=None):
    rclpy.init(args=args)
    controlVelocity = Twist()
    odometry = Odometry()

    controlVelocity.linear.x = 4.0
    controlVelocity.linear.y = 0.0
    controlVelocity.linear.z = 0.0

    controlVelocity.angular.x = 0.0
    controlVelocity.angular.y = 0.0
    controlVelocity.angular.z = 8.0

    testNode = Node("test_node")
    publisher = testNode.create_publisher(Twist, topic1, 1)
    rate = testNode.create_rate(rate_msg)

    while rclpy.ok():
        print("sending control message")
        publisher.publish(controlVelocity)
        rclpy.spin_once(testNode)
        rate.sleep()

    testNode.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

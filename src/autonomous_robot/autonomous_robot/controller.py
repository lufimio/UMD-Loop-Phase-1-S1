import rclpy
import random
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from custom_interfaces.msg import Obstacles, Obstacle, Waypoints
from geometry_msgs.msg import Point


class ControllerNode(Node):
    def __init__(self, obstacle_count, waypoint_count) -> None:
        super().__init__("controller_node")
        self.obstacle_publisher = self.create_publisher(
            Obstacles,
            "obstacles",
            QoSProfile(
                depth=10,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            ),
        )

        self.waypoint_publisher = self.create_publisher(
            Waypoints,
            "waypoints",
            QoSProfile(
                depth=10,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            ),
        )

        self.initObstacles(obstacle_count)
        self.initWaypoints(waypoint_count)

        self.obstacle_publisher.publish(self.obstacles)
        self.waypoint_publisher.publish(self.waypoints)

    def initObstacles(self, count):
        self.obstacles = Obstacles()
        offsets = [
            (2.0, 0.0),
            (3.0, 2.3),
            (2.8, -2.7),
            (0.9, -4.6),
            (-0.9, 2.9),
            (-0.8, -1.9),
            (-3.6, 0.9),
            (-3.6, -3.3),
        ]

        for x, y in offsets:
            height = random.uniform(0.5, 0.8)
            obstacle = Obstacle()
            obstacle.pose.position.x = x
            obstacle.pose.position.y = y
            obstacle.pose.position.z = height / 2
            obstacle.pose.orientation.w = 1.0
            obstacle.size.x = random.uniform(0.4, 0.6)
            obstacle.size.y = random.uniform(0.4, 0.6)
            obstacle.size.z = height
            self.get_logger().info(
                f"Generated Obstacle: {x}, {y} {obstacle.size.x}x{obstacle.size.y}"
            )
            self.obstacles.obstacles.append(obstacle)

    def initWaypoints(self, count, clearance=0.8):
        self.waypoints = Waypoints()
        x_min, x_max, y_min, y_max = -4.0, 5.0, -4.0, 4.0

        def obstacle_radius(obstacle):
            return max(obstacle.size.x, obstacle.size.y) / 2.0

        def min_distance_to_obstacles(x, y):
            dist = float("inf")
            for obstacle in self.obstacles.obstacles:
                ox = obstacle.pose.position.x
                oy = obstacle.pose.position.y
                d = ((x - ox) ** 2 + (y - oy) ** 2) ** 0.5
                d -= obstacle_radius(obstacle)
                dist = min(dist, d)
            return dist

        attempts = 0
        max_attempts = 10000
        while len(self.waypoints.waypoints) < count and attempts < max_attempts:
            attempts += 1
            x = random.uniform(x_min, x_max)
            y = random.uniform(y_min, y_max)

            if min_distance_to_obstacles(x, y) <= clearance:
                continue

            if (x * x) + (y * y) <= 1.3:
                continue

            if any(
                (x - wp.x) ** 2 + (y - wp.y) ** 2 <= clearance**2
                for wp in self.waypoints.waypoints
            ):
                continue

            self.get_logger().info(f"Generated Point: {x}, {y}")
            point = Point()
            point.x = float(x)
            point.y = float(y)
            point.z = 0.0
            self.waypoints.waypoints.append(point)


def main(args=None):
    rclpy.init(args=args)
    publisher = ControllerNode(3, 3)
    rclpy.spin(publisher)
    publisher.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

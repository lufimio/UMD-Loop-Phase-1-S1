import math
import itertools
import heapq
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from custom_interfaces.msg import Obstacles, Waypoints
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage
from tf_transformations import euler_from_quaternion, quaternion_from_euler


class RobotNode(Node):
    def __init__(self) -> None:
        super().__init__("robot_controller")
        self.robot_size = (1.0, 0.6)
        self.robot_pose = (0, 0, 0)
        self.obstacles = None
        self.waypoints = None
        self.path = None
        self.drive_timer = None
        self.target_point_index = 0
        self.wait_counter = 0
        self.current_segment_stage = "turn"

        self.publisher = self.create_publisher(Twist, "cmd_vel", 1)
        self.odometry_subscription = self.create_subscription(
            TFMessage, "/world/empty/dynamic_pose/info", self.update_odometry, 10
        )

        self.obstacles_subscription = self.create_subscription(
            Obstacles,
            "obstacles",
            self.initialize_obstacles,
            QoSProfile(
                depth=10,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            ),
        )

        self.waypoints_subscription = self.create_subscription(
            Waypoints,
            "waypoints",
            self.initialize_waypoints,
            QoSProfile(
                depth=10,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            ),
        )

    def update_odometry(self, odom):
        self.robot_pose = (
            odom.transforms[0].transform.translation.x,
            odom.transforms[0].transform.translation.y,
            euler_from_quaternion(
                [
                    odom.transforms[0].transform.rotation.x,
                    odom.transforms[0].transform.rotation.y,
                    odom.transforms[0].transform.rotation.z,
                    odom.transforms[0].transform.rotation.w,
                ]
            )[2],
        )

    def initialize_obstacles(self, obstacles):
        if self.obstacles is not None:
            self.generate_path()
            return

        self.obstacles = []
        for obstacle in obstacles.obstacles:
            self.obstacles.append(
                (
                    (
                        obstacle.pose.position.x,
                        obstacle.pose.position.y,
                        euler_from_quaternion(
                            [
                                obstacle.pose.orientation.x,
                                obstacle.pose.orientation.y,
                                obstacle.pose.orientation.z,
                                obstacle.pose.orientation.w,
                            ]
                        )[2],
                    ),
                    (obstacle.size.x, obstacle.size.y),
                )
            )

        self.generate_path()

    def initialize_waypoints(self, waypoints):
        if self.waypoints is not None:
            self.generate_path()
            return

        self.waypoints = []
        for waypoint in waypoints.waypoints:
            self.waypoints.append((waypoint.x, waypoint.y))

        self.generate_path()

    def inflate_obstacle(self, obstacle):
        (x, y, _), (sx, sy) = obstacle
        r = (
            math.hypot(
                self.robot_size[0] / 2.0,
                self.robot_size[1] / 2.0,
            )
            + 0.05
        )
        return (
            x - sx / 2.0 - r,
            y - sy / 2.0 - r,
            x + sx / 2.0 + r,
            y + sy / 2.0 + r,
        )

    # https://www.geeksforgeeks.org/computer-graphics/liang-barsky-algorithm/
    def segment_intersects_rect(self, a, b, rect):
        xmin, ymin, xmax, ymax = rect
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        p = (-dx, dx, -dy, dy)
        q = (
            a[0] - xmin,
            xmax - a[0],
            a[1] - ymin,
            ymax - a[1],
        )
        t_min = 0.0
        t_max = 1.0

        for pi, qi in zip(p, q):
            if abs(pi) < 1e-12:
                if qi < 0:
                    return False
                continue

            t = qi / pi
            if pi < 0:
                if t > t_max:
                    return False
                t_min = max(t_min, t)
            else:
                if t < t_min:
                    return False
                t_max = min(t_max, t)
        return t_min <= t_max

    def is_path_clear(self, a, b, obstacles):
        for i, obstacle in enumerate(obstacles):
            if self.segment_intersects_rect(a, b, obstacle):
                # self.get_logger().error(
                #     f"BLOCKED {a} -> {b} by obstacle {i} {obstacle}"
                # )
                return False
        return True

    def generate_graph(self, nodes, obstacles):
        graph = [[] for _ in nodes]

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                if self.is_path_clear(nodes[i], nodes[j], obstacles):
                    dx = nodes[i][0] - nodes[j][0]
                    dy = nodes[i][1] - nodes[j][1]
                    distance = math.hypot(dx, dy)

                    graph[i].append((j, distance))
                    graph[j].append((i, distance))

        return graph

    def generate_path(self):
        if self.obstacles is None or self.waypoints is None:
            return

        obstacles = [self.inflate_obstacle(obstacle) for obstacle in self.obstacles]
        self.path = []

        for start, goal in itertools.pairwise([(0.0, 0.0), *self.waypoints]):
            if self.is_path_clear(start, goal, obstacles):
                segment = [start, goal]
            else:  # run A*
                nodes = [start, goal]
                for xmin, ymin, xmax, ymax in obstacles:
                    nodes.extend(
                        [
                            (xmin - 0.1, ymin - 0.1),
                            (xmin - 0.1, ymax + 0.1),
                            (xmax + 0.1, ymin - 0.1),
                            (xmax + 0.1, ymax + 0.1),
                        ]
                    )

                graph = self.generate_graph(nodes, obstacles)

                for i, node in enumerate(nodes):
                    self.get_logger().info(f"node {i}: {node}, edges={graph[i]}")

                goal_index = 1
                distances = {0: 0.0}
                previous = {}
                queue = [(0.0, 0)]

                while queue:
                    _, current = heapq.heappop(queue)

                    if current == goal_index:
                        break

                    for neighbor, cost in graph[current]:
                        new_distance = distances[current] + cost

                        if new_distance < distances.get(neighbor, float("inf")):
                            distances[neighbor] = new_distance
                            previous[neighbor] = current

                            dx = nodes[neighbor][0] - goal[0]
                            dy = nodes[neighbor][1] - goal[1]
                            heuristic = math.hypot(dx, dy)

                            heapq.heappush(
                                queue,
                                (new_distance + heuristic, neighbor),
                            )

                if goal_index not in previous:
                    self.get_logger().error(
                        f"there is no path between {start} and {goal}"
                    )
                    return

                indices = []
                current = goal_index

                while current != 0:
                    indices.append(current)
                    current = previous[current]

                indices.append(0)
                indices.reverse()
                segment = [nodes[i] for i in indices]
            self.path.extend(segment[1:])
        self.get_logger().info(f"generated path: {self.path}")

        self.target_point_index = 0
        self.current_segment_stage = "turn"

        if self.drive_timer is not None:
            self.drive_timer.cancel()
        self.drive_timer = self.create_timer(0.025, self.tick_chassis)

    def tick_chassis(self):
        if self.path is None or not self.path:
            return

        if self.target_point_index >= len(self.path):
            self.publisher.publish(Twist())
            self.drive_timer.cancel()
            return

        rx, ry, r0 = self.robot_pose
        gx, gy = self.path[self.target_point_index]

        dx = gx - rx
        dy = gy - ry

        distance = math.hypot(dx, dy)

        goal_heading = math.atan2(dy, dx)

        heading_error = math.atan2(
            math.sin(goal_heading - r0), math.cos(goal_heading - r0)
        )

        cmd_vel = Twist()

        # Reached waypoint
        if distance < 0.08:
            self.get_logger().info(
                f"Reached waypoint {self.target_point_index}: "
                f"robot=({rx:.3f}, {ry:.3f}) "
                f"target=({gx:.3f}, {gy:.3f}) "
                f"distance={distance:.3f}"
            )

            self.target_point_index += 1

            if self.target_point_index >= len(self.path):
                self.publisher.publish(Twist())
                self.drive_timer.cancel()
                return

        else:
            # Turn toward target
            cmd_vel.angular.z = max(-1.0, min(1.0, 2.0 * heading_error))

            # Don't drive forward while badly misaligned
            heading_scale = max(0.0, math.cos(heading_error))

            cmd_vel.linear.x = min(0.6, 0.8 * distance) * heading_scale

        self.publisher.publish(cmd_vel)


def main(args=None):
    rclpy.init(args=args)
    publisher = RobotNode()
    rclpy.spin(publisher)
    publisher.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

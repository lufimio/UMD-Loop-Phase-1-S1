import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from custom_interfaces.msg import Obstacles, Obstacle, Waypoints
from geometry_msgs.msg import Point, Pose
from ros_gz_interfaces.srv import SpawnEntity


class SpawnerNode(Node):
    obstacleCounter = 0
    waypointCounter = 0

    def __init__(self) -> None:
        super().__init__("spawner_node")
        self.world_name = "empty"
        service_name = f"/world/{self.world_name}/create"
        self.spawn_client = self.create_client(SpawnEntity, service_name)

        while not self.spawn_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Waiting for Gazebo...")
        self.get_logger().info("Gazebo spawn service available.")

        self.spawned_obstacles = False
        self.obstacleSubscription = self.create_subscription(
            Obstacles,
            "obstacles",
            self.spawn_all_obstacles,
            QoSProfile(
                depth=10,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            ),
        )

        self.spawned_waypoints = False
        self.waypointsSubscription = self.create_subscription(
            Waypoints,
            "waypoints",
            self.spawn_all_waypoints,
            QoSProfile(
                depth=10,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            ),
        )

    def spawn_all_obstacles(self, obstacles: Obstacles):
        if self.spawned_obstacles:
            return

        for obstacle in obstacles.obstacles:
            self.spawn_obstacle(obstacle)
        self.spawned_obstacles = True

    def spawn_obstacle(self, obstacle: Obstacle):
        self.obstacleCounter += 1
        sdf = f"""
        <?xml version="1.0" ?>
        <sdf version="1.9">

          <model name="obstacle #{self.obstacleCounter}">
            <static>true</static>
            <link name="link">

              <collision name="collision">
                <geometry>
                  <box>
                    <size>
                      {obstacle.size.x} {obstacle.size.y} {obstacle.size.z}
                    </size>
                  </box>
                </geometry>
              </collision>

              <!-- Visual geometry -->
              <visual name="visual">
                <geometry>
                  <box>
                    <size>
                      {obstacle.size.x} {obstacle.size.y} {obstacle.size.z}
                    </size>
                  </box>
                </geometry>

                <material>
                  <ambient>0.1 0.8 0.1 1</ambient>
                  <diffuse>0.1 0.8 0.1 1</diffuse>
                </material>

              </visual>

            </link>

          </model>
        </sdf>
        """

        request = SpawnEntity.Request()
        request.entity_factory.name = f"obstacle #{self.obstacleCounter}"
        request.entity_factory.sdf = sdf
        request.entity_factory.pose = obstacle.pose
        request.entity_factory.relative_to = "world"
        request.entity_factory.allow_renaming = True

        future = self.spawn_client.call_async(request)
        future.add_done_callback(
            lambda future: self.spawn_callback(
                future, f"obstacle #{self.obstacleCounter}"
            )
        )

    def spawn_all_waypoints(self, waypoints: Waypoints):
        if self.spawned_waypoints:
            return

        for point in waypoints.waypoints:
            self.spawn_waypoint(point)
        self.spawned_waypoints = True

    def spawn_waypoint(self, point):
        self.waypointCounter += 1

        sdf = f"""
        <?xml version="1.0" ?>
        <sdf version="1.9">
        <model name="waypoint #{self.waypointCounter}">
            <static>true</static>

            <link name="link">
            <visual name="visual">
                <geometry>
                <cylinder>
                    <radius>0.15</radius>
                    <length>0.01</length>
                </cylinder>
                </geometry>

                <material>
                <ambient>1 1 0 1</ambient>
                <diffuse>1 1 0 1</diffuse>
                </material>
            </visual>
            </link>
        </model>
        </sdf>
        """

        pose = Pose()
        pose.position.x = point.x
        pose.position.y = point.y
        pose.position.z = point.z
        pose.orientation.w = 1.0

        request = SpawnEntity.Request()
        request.entity_factory.name = f"waypoint #{self.waypointCounter}"
        request.entity_factory.sdf = sdf
        request.entity_factory.pose = pose
        request.entity_factory.relative_to = "world"
        request.entity_factory.allow_renaming = True

        future = self.spawn_client.call_async(request)
        future.add_done_callback(
            lambda future: self.spawn_callback(
                future, f"waypoint #{self.waypointCounter}"
            )
        )

    def spawn_callback(self, future, name):
        try:
            response = future.result()
            if response.success:
                self.get_logger().info(f'Successfully spawned "{name}"')
            else:
                self.get_logger().error(f'Failed to spawn "{name}"')
        except Exception as e:
            self.get_logger().error(f'Exception while spawning "{name}": {e}')


def main(args=None):
    rclpy.init(args=args)
    publisher = SpawnerNode()
    rclpy.spin(publisher)
    publisher.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

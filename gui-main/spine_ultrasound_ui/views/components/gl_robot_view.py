import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Slot, QTimer
from PySide6.QtGui import QVector3D, QQuaternion, QMatrix4x4

class GLRobotView(QWidget):
    """
    基于 OpenGL 的 3D 机器人姿态和路径预览组件
    使用 pyqtgraph.opengl 实现高性能 3D 渲染
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 创建 OpenGL 视图窗口
        self.gl_view = gl.GLViewWidget()
        self.layout.addWidget(self.gl_view)

        # 设置相机参数
        self.gl_view.setCameraPosition(distance=2.0, elevation=30, azimuth=45)

        # 创建坐标系网格
        self._create_coordinate_grid()

        # 创建机器人模型
        self.robot_model = None
        self._create_robot_model()

        # 创建路径轨迹
        self.path_curve = None
        self.path_points = []

        # 扫描路径预览
        self.preview_path = None

        # 设置背景色，与浅色工作台主题保持一致
        self.gl_view.setBackgroundColor('#F7F8FA')

        # 性能优化：减少重绘频率
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(50)  # 20 FPS

    def _create_coordinate_grid(self):
        """创建坐标系网格"""
        # 地面网格
        grid = gl.GLGridItem()
        grid.setSize(2, 2, 0.1)
        grid.setSpacing(0.1, 0.1, 0.1)
        self.gl_view.addItem(grid)

        # 坐标轴
        axis = gl.GLAxisItem()
        axis.setSize(0.5, 0.5, 0.5)
        self.gl_view.addItem(axis)

    def _create_robot_model(self):
        """创建简化的机器人模型"""
        # 创建机器人基座 (圆柱体)
        base = gl.MeshData.cylinder(rows=10, cols=20, radius=[0.1, 0.1], length=0.1)
        self.base_mesh = gl.GLMeshItem(meshdata=base, color=(0.5, 0.5, 0.5, 1.0))
        self.gl_view.addItem(self.base_mesh)

        # 创建机器人手臂 (多个连杆)
        self.arm_links = []
        for i in range(3):  # 3个连杆
            link = gl.MeshData.cylinder(rows=8, cols=16, radius=[0.03, 0.03], length=0.3)
            link_mesh = gl.GLMeshItem(meshdata=link, color=(0.7, 0.7, 0.7, 1.0))
            self.arm_links.append(link_mesh)
            self.gl_view.addItem(link_mesh)

        # 创建末端执行器 (超声探头)
        probe = gl.MeshData.cylinder(rows=6, cols=12, radius=[0.05, 0.02], length=0.15)
        self.probe_mesh = gl.GLMeshItem(meshdata=probe, color=(0.2, 0.8, 0.2, 1.0))
        self.gl_view.addItem(self.probe_mesh)

    @Slot(np.ndarray, np.ndarray)
    def update_robot_pose(self, position: np.ndarray, quaternion: np.ndarray):
        """
        更新机器人姿态
        position: [x, y, z]
        quaternion: [w, x, y, z] 或 [x, y, z, w]
        """
        # 转换四元数格式 (假设输入是 [x,y,z,w])
        if len(quaternion) == 4:
            q = QQuaternion(quaternion[3], quaternion[0], quaternion[1], quaternion[2])
        else:
            q = QQuaternion(quaternion[0], quaternion[1], quaternion[2], quaternion[3])

        # 创建变换矩阵
        transform = QMatrix4x4()
        transform.translate(QVector3D(*position))
        transform.rotate(q)

        # 更新末端执行器位置
        self.probe_mesh.setTransform(transform)

        # 简化的手臂运动学 (实际应该使用真实的FK)
        self._update_arm_kinematics(position, q)

        # 添加到路径轨迹
        self.path_points.append(position.copy())
        if len(self.path_points) > 1000:  # 限制路径长度
            self.path_points.pop(0)

    def _update_arm_kinematics(self, end_pos: np.ndarray, end_ori: QQuaternion):
        """简化的手臂运动学更新"""
        # 这里应该使用真实的机器人运动学
        # 为演示目的，使用简化的几何关系

        base_pos = np.array([0, 0, 0.05])  # 基座位置

        # 连杆1: 从基座到肘部
        elbow_pos = end_pos * 0.5 + base_pos * 0.5
        elbow_pos[2] += 0.1

        # 连杆2: 从肘部到腕部
        wrist_pos = end_pos * 0.8 + elbow_pos * 0.2

        # 更新连杆位置
        if len(self.arm_links) >= 3:
            # 连杆1
            transform1 = QMatrix4x4()
            transform1.translate(QVector3D(*((base_pos + elbow_pos) * 0.5)))
            self.arm_links[0].setTransform(transform1)

            # 连杆2
            transform2 = QMatrix4x4()
            transform2.translate(QVector3D(*((elbow_pos + wrist_pos) * 0.5)))
            self.arm_links[1].setTransform(transform2)

            # 连杆3
            transform3 = QMatrix4x4()
            transform3.translate(QVector3D(*((wrist_pos + end_pos) * 0.5)))
            self.arm_links[2].setTransform(transform3)

    @Slot(list)
    def set_preview_path(self, path_points: list):
        """
        设置扫描路径预览
        path_points: List of [x, y, z] points
        """
        if not path_points:
            return

        # 清除旧的预览路径
        if self.preview_path:
            self.gl_view.removeItem(self.preview_path)

        # 创建新的预览路径
        points = np.array(path_points)
        self.preview_path = gl.GLLinePlotItem(pos=points, color=(1, 1, 0, 0.7), width=3)
        self.gl_view.addItem(self.preview_path)

    def _update_display(self):
        """定期更新显示"""
        # 更新路径轨迹
        if self.path_points:
            points = np.array(self.path_points)
            if self.path_curve:
                self.gl_view.removeItem(self.path_curve)

            self.path_curve = gl.GLLinePlotItem(pos=points, color=(0, 1, 1, 0.8), width=2)
            self.gl_view.addItem(self.path_curve)

    def clear_path(self):
        """清除路径轨迹"""
        self.path_points.clear()
        if self.path_curve:
            self.gl_view.removeItem(self.path_curve)
            self.path_curve = None

    def set_camera_view(self, distance: float = None, elevation: float = None, azimuth: float = None):
        """设置相机视角"""
        self.gl_view.setCameraPosition(
            distance=distance or 2.0,
            elevation=elevation or 30,
            azimuth=azimuth or 45
        )

    def reset_camera(self):
        """重置相机到默认位置"""
        self.set_camera_view()

    def get_current_pose(self) -> tuple:
        """获取当前机器人末端姿态"""
        # 这里应该返回实际的机器人姿态
        # 为演示目的返回默认值
        return np.array([0.5, 0.0, 0.3]), np.array([1.0, 0.0, 0.0, 0.0])

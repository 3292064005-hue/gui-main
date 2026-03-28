import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Slot

class USImageView(QWidget):
    """
    医疗级高性能超声图像渲染组件
    基于 pyqtgraph，直接利用 OpenGL 纹理加速，CPU 占用极低
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 1. 创建高性能 GraphicsLayoutWidget
        self.glw = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.glw)

        # 2. 创建 ViewBox (允许缩放、平移) 和 ImageItem (核心渲染器)
        self.view = self.glw.addViewBox()
        self.view.setAspectLocked(True) # 保持超声图像物理比例不变

        self.image_item = pg.ImageItem()
        self.view.addItem(self.image_item)

        # 3. 性能优化设置
        # 禁用默认的 auto-downsampling，防止超声斑锐度丢失
        self.image_item.setAutoDownsample(False)

        # 4. 设置查找表 (LUT) 以增强对比度 (医疗超声专用)
        # 使用标准灰度查找表，适合超声图像
        lut = pg.HistogramLUTWidget()
        lut.setImageItem(self.image_item)
        # 可以在这里添加lut到布局，但为了简化界面，我们使用默认设置

    @Slot(np.ndarray)
    def update_frame(self, frame_data: np.ndarray):
        """
        接收来自共享内存或独立进程的 numpy 数组并立即渲染
        frame_data: shape (H, W) or (H, W, 3), dtype uint8
        """
        # autoLevels=False 极其重要，防止每一帧都在 CPU 上计算最大最小值，极大地提升性能
        # 假设超声图像是 8 位灰度图 (0-255)
        self.image_item.setImage(frame_data, autoLevels=False, levels=(0, 255))

    def set_roi(self, x, y, width, height):
        """
        设置感兴趣区域 (ROI) 用于放大显示
        """
        self.view.setRange(QtCore.QRectF(x, y, width, height))

    def reset_view(self):
        """
        重置视图到适应图像大小
        """
        self.view.autoRange()

    def get_image_size(self):
        """
        获取当前显示图像的尺寸
        """
        if self.image_item.image is not None:
            return self.image_item.image.shape
        return None
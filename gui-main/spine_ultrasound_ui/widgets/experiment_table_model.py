from typing import List, Optional

from PySide6.QtCore import QAbstractTableModel, Qt

from spine_ultrasound_ui.models import ExperimentRecord


class ExperimentTableModel(QAbstractTableModel):
    headers = ["实验编号", "创建时间", "状态", "Cobb角", "目标压力", "保存目录"]

    def __init__(self, data: Optional[List[ExperimentRecord]] = None):
        super().__init__()
        self._data = data or []

    def set_records(self, records: List[ExperimentRecord]) -> None:
        self.beginResetModel()
        self._data = records
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        rec = self._data[index.row()]
        columns = [
            rec.exp_id,
            rec.created_at,
            rec.state,
            f"{rec.cobb_angle:.1f}°",
            f"{rec.pressure_target:.2f} N",
            rec.save_dir,
        ]
        return columns[index.column()]

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.headers[section]
        return section + 1

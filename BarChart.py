from copy import copy
from typing import List, TYPE_CHECKING, TypeVar

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPaintEvent, QPainter, QPen, QPicture, QTransform
from PyQt5.QtWidgets import QWidget

from Axis import Orientation, ValueAxis
from DrawerConfig import DrawConfig, DrawingCache
from Types import ColorType

if TYPE_CHECKING:
    from DrawerBase import DrawerBase

T = TypeVar("T")

Layer = QPicture


def _generate_sequence(start, end, step):
    """输出[start, end)中的序列"""
    i = start
    while i < end:
        yield i
        i += step


def scale_from_mid(low, high, ratio):
    mid = (low + high) / 2
    scaled_range_2 = (high - low) / 2 * ratio
    return mid - scaled_range_2, mid + scaled_range_2


class ExtraDrawConfig(DrawConfig):

    def __init__(self):
        super().__init__()
        self.y_scale = 1.1
        padding = 100
        self.paddings = (padding, padding, padding, padding)

        self.box_edge_color = QColor("black")
        self.box_edge_width = 1

        self.axis_label_font = None
        self.axis_label_color = QColor("black")

        self.y_tick_count = 30
        self.y_grid_color = QColor("lightgray")  # 如果设置为None则不绘制网格


class BarChartWidget(QWidget):
    """
    用于管理二维平面图，目前只支持x坐标值为线性整数的图标。
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.plot_area_edge_color: "ColorType" = Qt.black

        self.axis_x = ValueAxis(Orientation.HORIZONTAL)
        self.axis_y = ValueAxis(Orientation.VERTICAL)

        self._draw_config = ExtraDrawConfig()
        self._drawers: List["DrawerBase"] = []

        self._draw_config.begin = 0
        self._draw_config.end = 10

        self._axis_layer = Layer()
        self._drawer_layers: List["Layer"] = []

    def add_drawer(self, drawer: "DrawerBase"):
        self._drawers.append(drawer)
        self._drawer_layers.append(Layer())

    def set_x_range(self, begin: int, end: int):
        self._draw_config.begin, self._draw_config.end = begin, end

    def plot_area(self, config: "ExtraDrawConfig") -> "QRectF":
        """
        在UI坐标系中计算出绘制区域
        内部绘制函数无需调用该函数，查看config.output这个缓存的值即可
        """
        output: QRectF = QRectF(self.rect())
        paddings = config.paddings
        output = output.adjusted(paddings[0], paddings[1], -paddings[2], -paddings[3])
        return output

    def drawer_to_ui(self, value: T, config: "ExtraDrawConfig"=None) -> T:
        """
        将value从drawer坐标系转到UI坐标系
        """
        if config is None:
            config = self._draw_config
        return config.drawing_cache.drawer_transform.map(value)

    #########################################################################
    # Re-implemented protected methods
    #########################################################################
    def paintEvent(self, event: "QPaintEvent"):
        # copy config: ensure config is not change while painting
        config = copy(self._draw_config)

        self._prepare_painting(config)

        primary_painter = QPainter(self)

        # clear background (for QOpenGLWidget)
        # primary_painter.drawRect(self.rect())

        axis_layer = self._paint_axis(config, self._axis_layer)
        axis_layer.play(primary_painter)

        # 绘制所有注册了的序列
        for i, s in enumerate(self._drawers):
            layer = self._drawer_layers[i]
            self._paint_drawer(s, layer, config)
            layer.play(primary_painter)

        primary_painter.end()
        event.accept()

    #########################################################################
    # Private methods
    #########################################################################
    def _paint_drawer(self, drawer: "DrawerBase", layer: "Layer", config: "ExtraDrawConfig"):
        painter = QPainter(layer)
        painter.setPen(QPen(Qt.transparent))

        self._switch_painter_to_drawer_coordinate(painter, config)

        drawer.draw(copy(config), painter)

        painter.end()

    def _paint_axis(self, config: "ExtraDrawConfig", layer: "Layer"):
        for axis in self.axis_x, self.axis_y:
            axis.prepare_draw(copy(config))
        painter = QPainter(layer)

        # first: grid
        for axis in self.axis_x, self.axis_y:
            axis.draw_grid(copy(config), painter)

        # second: edge box
        painter.setPen(QPen(QColor(self.plot_area_edge_color)))
        painter.drawRect(config.drawing_cache.plot_area)

        # last: labels
        for axis in self.axis_x, self.axis_y:
            axis.draw_labels(copy(config), painter)
        return layer

    def _prepare_painting(self, config):
        """
        提前计算一些在绘图时需要的数据
        """
        # get preferred y range
        preferred_configs = [s.prepare_draw(copy(config)) for s in self._drawers]
        y_low = min(preferred_configs, key=lambda c: c.y_low).y_low
        y_high = max(preferred_configs, key=lambda c: c.y_high).y_high

        # scale y range
        config.y_low, config.y_high = scale_from_mid(y_low, y_high, config.y_scale)

        # 一些中间变量，例如坐标转化矩阵
        self._prepare_drawing_cache(config)

    def _prepare_drawing_cache(self, config: "ExtraDrawConfig"):
        """
        生成一个矩阵用以将painter的坐标系从UI坐标系调整为drawer坐标系
        这样painter中的x和y轴就正好对应数据的x和y了

        """
        # 从UI坐标系到drawer坐标系的转化矩阵的构造顺序恰好相反，假设目前为drawer坐标系
        # 将drawer坐标转化为UI坐标
        drawer_area = QRectF(config.begin,
                             config.y_low,
                             max(config.end - config.begin, 1),
                             max(config.y_high - config.y_low, 1),
                             )
        plot_area = self.plot_area(config)
        # 应用这个坐标转化
        transform = self._coordinate_transform(drawer_area, plot_area)
        # 在UI坐标系中上下翻转图像
        transform *= QTransform.fromTranslate(0, self.size().height()).rotate(180, Qt.XAxis)

        # 保存一些中间变量
        drawing_cache = DrawingCache()
        drawing_cache.drawer_transform = transform
        drawing_cache.drawer_area = drawer_area
        drawing_cache.plot_area = plot_area
        config.drawing_cache = drawing_cache


    def _switch_painter_to_drawer_coordinate(self, painter: "Layer", config: "ExtraDrawConfig"):
        """
        将painter的坐标系从UI坐标系调整为drawer坐标系
        这样painter中的x和y轴就正好对应数据的x和y了

        如果要切换回来，调用painter.setWorldMatrixEnabled(False)即可
        """
        painter.setWorldTransform(config.drawing_cache.drawer_transform)
        painter.setWorldMatrixEnabled(True)

    def _coordinate_transform(self, input: QRectF, output: QRectF):
        rx, ry = output.width() / input.width(), output.height() / input.height()
        t = QTransform.fromTranslate(-input.left(), -input.top())
        t *= QTransform.fromScale(rx, ry)
        t *= QTransform.fromTranslate(output.left(), output.top())
        return t


## 简介
这是一个用来替代QtChart的模块----因为QtCharts性能糟糕无比(@Qt 5.12.0)，所以才有了这个模块。  
目前实现了K线图（CandleStickChart）以及柱状图。  

## 简单的用例
使用方式:
```python
from chart import *
# prepare data source
data_source = DataSource()
chart = ChartWidget()

# use HistogramDrawer to show these data
chart.add_drawer(HistogramDrawer(data_source))

# axis x, y
axis_x = ValueAxisX()
chart.add_axis(axis_x, ValueAxisY())
chart.show()

# add data
data_source.append(100)
data_source.append(110)
data_source.append(120)
data_source.append(90)
data_source.append(130)
data_source.extend([-130, -120])

# adjust data to show
chart.set_x_range(0, 7)

# adjust axis x to make result seems better.
axis_x.label_count = 7
```

## 使用指南

这个模块主要包含三部分内容：
 * DataSource 表示数据源
 * Drawer     将数据源可视化的东西
 * Chart      QtWidget

所以在使用该模块的时候，我们需要做三件事情：

 1. 准备数据--创建一个DataSource。  
 2. 选择如何呈现数据--选择一个Drawer。不同的Drawer能呈现的数据类型也各不相同。   
 3. 最后将Drawer放入Chart，以显示到显示器上。  

## DataSource for Drawer
下面的列表列出了各个Drawer及其可呈现的数据源类型：
 * CandleChartDrawer
   * DataSource\[CandleData]
   * CandleDataSource
 * BarChartDrawer:HistogramDrawer
   * DataSource\[float]
   * HistogramDataSource
 * TextLabelDrawer
   * DataSource\[TextLabelInfo]
   * TextLabelDataSource
   * DateTimeDataSource
   * ValueLabelDataSource
   * CandleLabelDataSource
 * LineGridDrawer
   * DataSource[float]
   * LineGridDataSource

## 高级用法
### 子图
使用AdvancedChartWidget可以方便地整合多个ChartWidget。
使用AdvancedChartWidget.add_chart()可以增加子图并设置子图所占空间比例。

### 颜色、样式设置
所有的样式都可以设置，包括颜色，字体，边框、是否显示等等。
任何与数据有关的样式设置都在drawer中有对应的属性。
与表格有关的样式属性都在chart中。

### 光标以及光标同步
在AdvancedChartWidget中可以创建一个光标，使用SubChartWrapper.create_cross_hair()可以创建默认的光标。
使用使用SubChartWrapper.linx_x_to()/link_y_to()可以同步两张图标中的X/Y光标。
 > 不是所有的Axis都支持光标，如果Axis不支持光标，会在绘图的时候抛出异常。  
 > 所有内置的Axis都支持光标。  
 
## 性能
我不敢说该模块的性能是非常高的。
在显示4000个K线的时候大概90FPS(8700K@4.3GHz)。
考虑到4K屏横轴也只有不到4000个像素点，所以这个性能应该不会造成瓶颈。  
Drawer每次绘图都是全部重绘，所以缩放、滚动、改变颜色等操作不会对绘制速率产生影响。  
这也正是不采用QtCharts的原因，QtCharts在显示几百个K线的时候，滚动、缩放就已经明显卡顿了（不可思议）  

## 扩展
这个模块是应vnpy的K线图而写的，所以只实现了必要的功能。  
理论上任何由X，Y序列构成的图表，都可以非常简单地用该模块绘制出来  
如果需要为该模块增加其他类型的图表，请派生ChartDrawerBase并重载prepare_draw和draw两个函数。  
具体的写法可以看docstring及其CandleChartDrawer或者BarChartDrawer的代码。  

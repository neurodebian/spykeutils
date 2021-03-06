""" Contains a helper class for creating windows containing guiqwt plots.
"""

from PyQt4 import QtGui
from guiqwt.baseplot import BasePlot
from guiqwt.plot import PlotManager
from guiqwt.tools import (SelectTool, RectZoomTool, BasePlotMenuTool,
                          DeleteItemTool, ItemListPanelTool,
                          AntiAliasingTool, AxisScaleTool, DisplayCoordsTool,
                          ExportItemDataTool, EditItemDataTool,
                          ItemCenterTool, SignalStatsTool)
from PyQt4.QtCore import Qt
from PyQt4.QtGui import (QDialog, QGridLayout, QToolBar, QHBoxLayout,
                         QVBoxLayout, QFrame, QWidget)
from guidata.configtools import get_icon
from guiqwt.config import _
        
class PlotDialog(QDialog, PlotManager):
    """ Implements a dialog to which an arbitrary number of plots can be
        added.

        This class implements a `QDialog` with a number of plots on it. The
        plot's axes can be arbitrarily synchronized and option checkboxes can
        be added which provide callbacks when the checkbox state changes.
    """

    def __init__(self, wintitle="guiqwt plot", icon="guiqwt.png",
                 toolbar=False, options=None, parent=None, panels=None):
        QDialog.__init__(self, parent)
        self.setWindowFlags(Qt.Window)

        # WidgetMixin copy
        PlotManager.__init__(self, main=self)
        
        self.main_layout = QVBoxLayout(self)
        self.color_layout = QHBoxLayout()
        self.plot_layout = QGridLayout()
        self.option_layout = QHBoxLayout()

        self.plot_widget = None

        if panels is not None:
            for panel in panels:
                self.add_panel(panel)

        self.toolbar = QToolBar(_("Tools"))
        if not toolbar:
            self.toolbar.hide()

        # Configuring widget layout
        self._setup_widget_properties(wintitle=wintitle, icon=icon)
        self._setup_widget_layout()
        
        # Options
        self.option_callbacks = {}
        self.legend = None
        
    def _setup_widget_properties(self, wintitle, icon):
        self.setWindowTitle(wintitle)
        if isinstance(icon, basestring):
            icon = get_icon(icon)
        self.setWindowIcon(icon)
        self.setMinimumSize(320, 240)
        self.resize(720, 540)
        
    def _setup_widget_layout(self):
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addLayout(self.color_layout)
        self.main_layout.addLayout(self.plot_layout)
        self.main_layout.addLayout(self.option_layout)
        self.setLayout(self.main_layout)
        
    def add_custom_curve_tools(self, antialiasing=True,
                               activate_zoom=True):
        """ Adds typically needed curve tools to the window.

        :param bool antialiasing: Determines if the antialiasing tool is
            added.
        :param bool activate_zoom: Determines if the zoom tool is activated
            initially (otherwise, the selection tool will be activated).
        """
        self.add_toolbar(self.toolbar)

        t = self.add_tool(SelectTool)
        if not activate_zoom:
            self.set_default_tool(t)
        t = self.add_tool(RectZoomTool)
        if activate_zoom:
            self.set_default_tool(t)
        self.add_tool(BasePlotMenuTool, "item")
        self.add_tool(ExportItemDataTool)
        try:
            import spyderlib.widgets.objecteditor  # analysis:ignore
            self.add_tool(EditItemDataTool)
        except ImportError:
            pass
        self.add_tool(ItemCenterTool)
        self.add_tool(DeleteItemTool)
        self.add_separator_tool()
        self.add_tool(BasePlotMenuTool, "grid")
        self.add_tool(BasePlotMenuTool, "axes")
        self.add_tool(DisplayCoordsTool)
        if self.get_itemlist_panel():
            self.add_tool(ItemListPanelTool)

        self.add_separator_tool()
        self.add_tool(SignalStatsTool)
        if antialiasing:
            self.add_tool(AntiAliasingTool)
        self.add_tool(AxisScaleTool)
        self.add_separator_tool()
        self.register_other_tools()
        self.add_separator_tool()
        self.get_default_tool().activate()
    
    def add_option(self, name, change_callback, active = False):
        """ Add an option (using a checkbox) to the window.

        :param str name: The name of the option.
        :param func change_callback: A function accepting the new state as
            a parameter. The function will be called whenever the state
            of the option changes.
        :param bool active: Determines if the option is activated initially.
        """
        checkBox = QtGui.QCheckBox(self)
        checkBox.setChecked(active)
        checkBox.setText(name)
        checkBox.stateChanged.connect(self._option_callback)
        self.option_callbacks[checkBox] = change_callback
        self.option_layout.addWidget(checkBox)

    def add_x_synchronization_option(self, active, ids = None):
        """ Offer an option for X axes synchronization.

        :param bool active: Determines whether the axes are synchronized
            initially.
        :param sequence ids: List of plot ids to synchronize.
        """
        if active and ids:
            self.synchronize_axis(BasePlot.X_BOTTOM, ids)
        self.add_option('Synchronize X Axes',
            PlotDialog._synchronization_option_x, active)

    def add_y_synchronization_option(self, active, ids = None):
        """ Offer an option for Y axes synchronization.

        :param bool active: Determines whether the axes are synchronized
            initially
        :param sequence ids: List of plot ids to synchronize.
        """
        if active and ids:
            self.synchronize_axis(BasePlot.Y_LEFT, ids)
        self.add_option('Synchronize Y Axes',
            PlotDialog._synchronization_option_y, active)

    def _synchronization_option_x(self, state):
        """ Callback for x-axis synchronization
        """
        if state:
            self.synchronize_axis(BasePlot.X_BOTTOM)
        else:
            self.unsynchronize_axis(BasePlot.X_BOTTOM)

    def _synchronization_option_y(self, state):
        """ Callback for y-axis synchronization
        """
        if state:
            self.synchronize_axis(BasePlot.Y_LEFT)
        else:
            self.unsynchronize_axis(BasePlot.Y_LEFT)
        
    def add_unit_color(self, color, name='Unit color:'):
        """ Create a small legend on top of the window with only one entry.

        :param str color: A Qt color name (e.g. '#ff0000')
        :param str name: The name of the legend item. It will be displayed
            on the left of the color.
        """
        label = QtGui.QLabel(self)
        label.setText(name)
        label.setAlignment(Qt.AlignRight)
        self.color_layout.addWidget(label)
        label = QtGui.QLabel(self)
        label.setStyleSheet('background-color:' + str(color))
        label.setFrameShape(QFrame.StyledPanel)
        label.setMaximumWidth(80)
        self.color_layout.addWidget(label)

    def add_custom_label(self, legend_string):
        """ Add a label on the right of the plots

        :param str legend_string: An arbitrary string (which can contain
            newlines) to display on the right of the plots
        """
        label = QtGui.QLabel(self)
        label.setText(legend_string)
        self.plot_layout.addWidget(label, 0, self.plot_layout.columnCount(),
            -1, 1)

    def add_color_legend(self, legend, show_option=None):
        """ Create a legend on the right of the plots with colors and names.

        :param sequence legend: List of (color, text) tuples, where `color`
            is a Qt color name (e.g. '#ff0000') and `text` is the
            corresponding text to display in the legend.
        :param bool show_option: Determines whether a toggle for the legend
            will be shown (if the parameter is not ``None``) and if the legend
            is visible initially (``True``/``False``).
        """
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)
        for l in legend:
            label = QtGui.QLabel(self)
            label.setStyleSheet('background-color:' + str(l[0]))
            label.setFrameShape(QFrame.StyledPanel)
            label.setMaximumWidth(80)
            label.setMaximumHeight(12)
            layout.addWidget(label, layout.rowCount(), 0, 1, 1)
            label = QtGui.QLabel(self)
            label.setText(l[1])
            layout.addWidget(label, layout.rowCount()-1, 1, 1, 1)

        self.plot_layout.addWidget(widget, 0, self.plot_layout.columnCount(),
            -1, 1)
        if show_option is not None:
            widget.setVisible(show_option)
            self.add_option('Show legend sidebar',
                lambda w,s : widget.setVisible(s),
                show_option)
    
    def add_legend_option(self, legends, active):
        """ Create a user option to show or hide a list of legend objects.

        :param sequence legends: The legend objects affected by the option.
        :param bool active: Determines whether the legends will be visible
            initially.
        """
        self.legends = legends
        self._set_legend_visibility(active)
        self.add_option('Show legend', self._legend_callback, active)
        if active:
            self._set_legend_visibility(True)
        
    def _option_callback(self, state):
        self.option_callbacks[self.sender()](self, state)

    #noinspection PyUnusedLocal
    def _legend_callback(self, win, state):
        self._set_legend_visibility(state > 0)
    
    def _set_legend_visibility(self, visible):
        for p in self.plots.itervalues():
            for l in self.legends:
                p.set_item_visible(l, visible)

    def add_plot_widget(self, plot_widget, plot_id, row=-1, column=0):
        """ Adds a guiqwt plot to the window.

        :param plot_widget: The plot to add.
        :type plot_widget: guiqwt plot widget
        :param int plot_id: The id of the new plot.
        :param int row: The row of the new plot. If this is -1, the new plot
            will be added in a new row (if `column` is 0) or
            in the last row.
        :param int column: The column of the new plot.
        """
        if row==-1:
            if column==0:
                row = self.plot_layout.rowCount()
            else:
                row = self.plot_layout.rowCount() - 1
        self.plot_layout.addWidget(plot_widget,row,column)
        new_plot = plot_widget.plot
        self.add_plot(new_plot, plot_id)
        
    def synchronize_axis(self, axis, plots = None):
        if plots is None:
            plots = self.plots.keys()
        PlotManager.synchronize_axis(self, axis, plots)
        
    def unsynchronize_axis(self, axis, plots = None):
        if plots is None:
            plots = self.plots.keys()
        for plot_id in plots:
            if not plot_id in self.synchronized_plots:
                continue
            synclist = self.synchronized_plots[plot_id]
            for plot2_id in plots:
                if plot_id==plot2_id:
                    continue
                item = (axis,plot2_id)
                if item in synclist:
                    synclist.remove(item)
        
    def plot_axis_changed(self, plot):
        ids = [k for k, p in self.plots.iteritems() if p == plot]
        if len(ids) < 1:
            return
        plot_id = ids[0]
        if plot_id not in self.synchronized_plots:
            return
        for (axis, other_plot_id) in self.synchronized_plots[plot_id]:
            scalediv = plot.axisScaleDiv(axis)
            other = self.get_plot(other_plot_id)
            lb = scalediv.lowerBound()
            ub = scalediv.upperBound()
            other.setAxisScale(axis, lb, ub)
            other.replot()
from guiqwt.builder import make
from guiqwt.baseplot import BasePlot
from guiqwt.plot import BaseCurveWidget
import quantities as pq

from dialogs import PlotDialog
import helper
from ..progress_indicator import ProgressIndicator
from ..correlogram import correlogram
from ..spyke_exception import SpykeException

@helper.needs_qt
def cross_correlogram(trains, bin_size, cut_off, border_correction,
                      unit=pq.ms, progress=ProgressIndicator()):
    """ Create (cross-)correlograms from a dictionary of SpikeTrain
        lists for different units.

    :param dict trains: Dictionary of SpikeTrain lists indexed by Unit
        objectss.
    :param bin_size: Bin size (time).
    :type bin_size: Quantity scalar
    :param cut_off: Cut off (end time of calculated correlogram).
    :type cut_off: Quantity scalar
    :param bool border_correction: Apply correction for less data at higher
        timelags (WARNING: Not perfect for bin_size != 1, especially
        with large `cut_off`).
    :param Quantity unit: Unit of X-Axis. If None, milliseconds are
        used.
    :param progress: Set this parameter to report progress.
    :type progress: :class:`spykeutils.progress_indicator.ProgressIndicator`
    """
    if not trains:
        raise SpykeException('No spike trains for correlogram')

    win_title = 'Correlogram'
    progress.begin('Creating correlogram')
    progress.set_status('Calculating...')
    win = PlotDialog(toolbar=True, wintitle=win_title)
    _correlogram_plot(win, trains, bin_size, cut_off, border_correction,
        progress, unit)

def _correlogram_plot(win, trains, bin_size, cut_off, border_correction,
                      progress, unit):
    """ Fill a plot window with correlograms.
    """
    correlograms, bins = correlogram(trains, bin_size, cut_off,
        border_correction, unit, progress)
    x = bins[:-1] + bin_size / 2

    crlgs = []
    indices = correlograms.keys()
    for i1 in xrange(len(indices)):
        for i2 in xrange(i1, len(indices)):
            crlgs.append((correlograms[indices[i1]][indices[i2]],
                indices[i1], indices[i2]))

    for i, c in enumerate(crlgs):
        legend_items = []
        pW = BaseCurveWidget(win)
        plot = pW.plot
        plot.set_antialiasing(True)
        plot.add_item(make.curve(x, c[0]))

        # Create legend
        color = helper.get_object_color(c[1])
        color_curve = make.curve([], [], c[1].name,
            color, 'NoPen', linewidth=1, marker='Rect',
            markerfacecolor=color, markeredgecolor=color)
        legend_items.append(color_curve)
        plot.add_item(color_curve)
        if c[1] != c[2]:
            color = helper.get_object_color(c[2])
            color_curve = make.curve([], [], c[2].name,
                color, 'NoPen', linewidth=1, marker='Rect',
                markerfacecolor=color, markeredgecolor=color)
            legend_items.append(color_curve)
            plot.add_item(color_curve)
        plot.add_item(make.legend(restrict_items=legend_items))

        columns = max(2, len(indices) - 3)
        if i >= len(correlograms) - columns:
            plot.set_axis_title(BasePlot.X_BOTTOM, 'Time')
            plot.set_axis_unit(BasePlot.X_BOTTOM, unit.dimensionality.string)
        if i % columns == 0:
            plot.set_axis_title(BasePlot.Y_LEFT, 'Correlation')
            plot.set_axis_unit(BasePlot.Y_LEFT, 'count/segment')

        win.add_plot_widget(pW, i, column=i%columns)

    win.add_x_synchronization_option(True, range(len(correlograms)))
    win.add_y_synchronization_option(False, range(len(correlograms)))
    win.add_custom_curve_tools()
    progress.done()
    win.show()

    return True
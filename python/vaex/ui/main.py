from __future__ import print_function
__author__ = 'breddels'

import sampy
import platform
import vaex.utils
import sys
import threading
import vaex.export
import vaex.utils
import vaex.promise

# py2/p3 compatibility
try:
	from urllib.parse import urlparse
except ImportError:
	from urlparse import urlparse



# help py2app, it was missing this import

try: # in Pyinstaller this doesn't work, and we can get away with not setting this, total mystery
	import sip
	sip.setapi('QVariant', 2)
	sip.setapi('QString', 2)
except:
	pass
darwin = "darwin" in platform.system().lower()
frozen = getattr(sys, 'frozen', False)


#print "DEFAULT ENCODING is: %s"%(sys.getdefaultencoding())
#print "FILE SYSTEM ENCODING is: %s"%(sys.getfilesystemencoding())
#if darwin:
if sys.getfilesystemencoding() == None: # TODO: why does this happen in pyinstaller?
	def getfilesystemencoding_wrapper():
		return "UTF-8"
	sys.getfilesystemencoding = getfilesystemencoding_wrapper


# on osx 10.8 we sometimes get pipe errors while printing, ignore these
#signal.signal(signal.SIGPIPE, signal.SIG_DFL)

try:
	import pdb
	import astropy.io.fits
	#pdb.set_trace()
except Exception as e:
	print(e)
	pdb.set_trace()
import vaex.ui.plot_windows as vp
from vaex.ui.ranking import *
import vaex.ui.undo
import vaex.kld
import vaex.utils
import vaex.dataset

#import subspacefind
#import ctypes

import imp

import vaex.logging
logger = vaex.logging.getLogger("vaex")

#import locale
#locale.setlocale(locale.LC_ALL, )

# samp stuff
#import astropy.io.votable


custom = None
custompath = path = os.path.expanduser('~/.vaex/custom.py')
#print path
if os.path.exists(path):
	customModule = imp.load_source('vaex.custom', path)
	#custom = customModule.Custom()
else:
	custom = None
	logger.debug("%s does not exist" % path)

#print "root path is", vaex.utils.get_root_path()


if getattr(sys, 'frozen', False):
	application_path = os.path.dirname(sys.executable)
elif __file__:
	application_path = os.path.dirname(__file__)


if not frozen: # astropy not working :s
	pass
	#import pdb
	#pdb.set_trace()
	# fix from Chris Beaumont
	#import astropy.logger
	#astropy.logger.log.disable_warnings_logging()
	__import__("astropy.io.votable")



# for osx
if "darwin" in platform.system().lower():
	application_path = os.path.abspath(".")


#from PySide import QtGui, QtCore
from vaex.ui.qt import *
from vaex.ui.table import *

from vaex.samp import Samp


def error(title, msg):
	print("Error", title, msg)

from vaex.dataset import *

possibleFractions = [10**base * f for base in [-3,-2,-1,0] for f in [0.25, 0.5, 0.75, 1.]]
possibleFractions.insert(0,10**-4)
#print possibleFractions

class DatasetSelector(QtGui.QListWidget):
	def __init__(self, parent):
		super(DatasetSelector, self).__init__(parent)
		#self.icon = QtGui.QIcon('icons/png/24x24/devices/memory.png')
		#self.icon_server = QtGui.QIcon('icons/png/24x24/devices/memory.png')
		self.icon = QtGui.QIcon(vp.iconfile('drive'))
		self.icon_server = QtGui.QIcon(vp.iconfile('server-cloud'))
		self.datasets = []
		self.signal_pick = vaex.events.Signal("pick")
		self.signal_add_dataset = vaex.events.Signal("add dataset")

		self.signal_add_dataset.connect(self.on_add_dataset)
		self.signal_dataset_select = vaex.events.Signal("dataset-select")
		self.currentItemChanged.connect(self.onDatasetSelected)
		#self.items

	def onDatasetSelected(self, data_item, previous):
		if data_item is not None:
			data = data_item.data(QtCore.Qt.UserRole)
			if hasattr(data, "toPyObject"):
				dataset = data.toPyObject()
				self.signal_dataset_select.emit(dataset)
			else:
				self.signal_dataset_select.emit(data)

	def on_add_dataset(self, dataset):
		#print "added dataset", dataset
		self.datasets.append(dataset)
		dataset.signal_pick.connect(self.on_pick)

	def on_pick(self, dataset, row):
		# broadcast
		logger.debug("broadcast pick")
		self.signal_pick.emit(dataset, row)

	def setBestFraction(self, dataset):
		Nmax = 1000*1000*10
		for fraction in possibleFractions[::-1]:
			N  = len(dataset)
			if N > Nmax:
				dataset.set_active_fraction(fraction)
			else:
				break

	def is_empty(self):
		return len(self.datasets) == 0

	def open(self, path, **kwargs):
		ds = vaex.open(path, **kwargs)
		return self.add(ds)

	def add(self, dataset):
		self.setBestFraction(dataset)
		item = QtGui.QListWidgetItem(self)
		item.setText(dataset.name)
		item.setIcon(self.icon_server if isinstance(dataset, vaex.dataset.DatasetRemote) else self.icon)
		item.setToolTip("file: " +dataset.filename)
		item.setData(QtCore.Qt.UserRole, dataset)
		self.setCurrentItem(item)
		self.signal_add_dataset.emit(dataset)
		return dataset



class Worker(QtCore.QThread):
	def __init__(self, parent, name, func, *args, **kwargs):
		QtCore.QThread.__init__(self, parent=None)
		self.func = func
		self.args = args
		self.kwargs = kwargs
		self.name = name
		self.signal = QtCore.SIGNAL("signal")

	def run(self):
		time.sleep(0.1)
		print("in thread", self.currentThreadId())
		self.result = self.func(*self.args, **self.kwargs)
		print("result:", self.result)
		#self.emit(self.signal, self.result)
		#self.exec_()


def MyStats(object):
	def __init__(self, data):
		self.data = data

	def __call___(self, args):
		print(args)
		#stat_name, column_name = args
		#print "do", stat_name, "on", column_name
		return 1
		#f = stats[stat_name]
		#return column_name, stat_name, f(self.data.columns[column_name])

#stats = {"minimum": lambda x: str(np.nanmin(x)), "maximum": lambda x: str(np.nanmax(x)), "mean": lambda x: str(np.mean(x)), "std": lambda x: str(np.std(x)), "median": lambda x: str(np.median(x))}
stats = {"minimum": lambda x: str(np.nanmin(x)), "maximum": lambda x: str(np.nanmax(x)), "mean": lambda x: str(np.mean(x)), "std": lambda x: str(np.std(x))}
def statsrun(args):
	columns, stat_name, column_name = args
	f = stats[stat_name]
	#print args
	return 1

class StatWorker(QtCore.QThread):
	def __init__(self, parent, data):
		QtCore.QThread.__init__(self, parent=parent)
		self.data = data

	def run(self):
		time.sleep(0.1)
		print("in thread", self.currentThreadId())
		jobs = [(stat_name, column_name) for stat_name in list(stats.keys()) for column_name in list(self.data.columns.keys())]
		@parallelize(cores=QtCore.QThread.idealThreadCount())
		def dostats(args, data=self.data):
			stat_name, column_name = args
			columns = data.columns
			f = stats[stat_name]
			result = f(columns[column_name][slice(*data.current_slice)])
			print(result)
			return result
		values = dostats(jobs)
		self.results = {}
		for job, value in zip(jobs, values):
			stat_name, column_name = job
			if stat_name not in self.results:
				self.results[stat_name] = {}
			self.results[stat_name][column_name] = value
		print("results", self.results)




from vaex.parallelize import parallelize


class StatisticsDialog(QtGui.QDialog):
	def __init__(self, parent, data):
		super(StatisticsDialog, self).__init__(parent)
		self.data = data

		#self.form_layout = QtGui.QFormLayout()
		#self.min = QtGui.QLabel('...computing...', self)
		#self.form_layout.addRow('Minimum:', self.min)
		#self.setLayout(self.form_layout)

		self.boxlist = QtGui.QHBoxLayout(self)

		self.headers = ['minimum', 'maximum', 'mean', 'std']

		#WorkerMinimum = lambda parent, data, column_name: Worker(parent, 'minimum', lambda data, column_name: str(min(data.columns[column_name])), data=data, column_name=column_name)
		#WorkerMaximum = lambda parent, data, column_name: Worker(parent, 'maximum', lambda data, column_name: str(max(data.columns[column_name])), data=data, column_name=column_name)
		#self.workers = {'minimum':WorkerMinimum, 'maximum': WorkerMaximum}

		self.table = QtGui.QTableWidget(data.nColumns, len(self.headers), self)
		self.table.setHorizontalHeaderLabels(self.headers)
		self.table.setVerticalHeaderLabels(list(self.data.columns.keys()))




		#pool = multiprocessing.Pool() #processes=QtCore.QThread.idealThreadCount())
		#print "jobs:", jobs
		worker = StatWorker(self, self.data)
		def onFinish(worker=worker):
			for column, stat in enumerate(self.headers):
				for row, column_name in enumerate(self.data.columns.keys()):
					value = worker.results[stat][column_name]
					item = QtGui.QTableWidgetItem(value)
					self.table.setItem(row, column, item)


		worker.finished.connect(onFinish)
		worker.start()
		#for name in self.header:
		#for column_name in self.data.colums.keys():
		#	self.table.set
		#worker.finished.connect(onFinish)
		if 0:
			self.worker_list = [] # keep references
			def onFinish():
				for column, stat in enumerate(self.headers):
					for row, column_name in enumerate(self.data.columns.keys()):
						value = worker.results[stat][column_name]
						item = QtGui.QTableWidgetItem(worker.result)
						self.table.setItem(row, column, item)
			for column, stat in enumerate(self.headers):
				for row, column_name in enumerate(self.data.columns.keys()):
					worker = self.workers[stat](parent, data, column_name)
					def onFinish(worker=worker, row=row, column=column):
						print("finished running", worker.result)
						item = QtGui.QTableWidgetItem(worker.result)
						self.table.setItem(row, column, item)
					worker.finished.connect(onFinish)
					print("starting", row, column)
					worker.start(QtCore.QThread.IdlePriority)
					self.worker_list.append(worker) # keeps reference to avoid GC


		self.boxlist.addWidget(self.table)
		self.setLayout(self.boxlist)




		if 0:
			#w1 = Worker(self, lambda data: str(min(data.columns.items()[0])), self.data)
			self.w1 = Worker(self, self.test, self.data)
			#self.connect(self.w1, self.w1.signal, self.setmin)
			def setmin():
				print(self.min.setText(self.w1.result))
			self.w1.finished.connect(setmin)
			self.w1.start()

	def test(self, data):
		print("test")
		data = list(data.columns.values())[0]
		return str(min(data))
		#return "test"
	def onFinish(self, worker):
		print("worker", worker)
		#print "setting", result
		#self.min = str


class DatasetPanel(QtGui.QFrame):
	def __init__(self, parent, dataset_list):
		super(DatasetPanel, self).__init__(parent)

		self.jobsManager = vaex.dataset.JobsManager()
		self.dataset = None
		self.dataset_list = dataset_list
		self.app = parent

		self.undoManager = vaex.ui.undo.UndoManager()

		self.form_layout = QtGui.QFormLayout()

		self.name = QtGui.QLabel('', self)
		self.form_layout.addRow('Name:', self.name)

		self.label_columns = QtGui.QLabel('', self)
		self.form_layout.addRow('Columns:', self.label_columns)

		self.label_length = QtGui.QLabel('', self)
		self.form_layout.addRow('Length:', self.label_length)

		#self.histogramButton = QtGui.QPushButton('histogram (1d)', self)
		self.button_histogram = QtGui.QToolButton(self)
		self.button_histogram.setText('histogram (1d)')
		self.form_layout.addRow('Plotting:', self.button_histogram)

		self.button_2d = QtGui.QToolButton(self)
		self.button_2d.setText('x/y density')
		self.form_layout.addRow('', self.button_2d)

		self.button_3d = QtGui.QToolButton(self)
		self.button_3d.setText('x/y/z density')
		self.form_layout.addRow('', self.button_3d)
		if 0:


			self.scatter1dSeries = QtGui.QPushButton('series', self)
			self.form_layout.addRow('', self.scatter1dSeries)

			self.scatter2dSeries = QtGui.QPushButton('x/y series', self)
			self.form_layout.addRow('', self.scatter2dSeries)

		if 0:
			self.serieSlice = QtGui.QToolButton(self)
			self.serieSlice.setText('serie slice')
			self.form_layout.addRow('', self.serieSlice)

		self.statistics = QtGui.QPushButton('Statistics', self)
		self.form_layout.addRow('Data:', self.statistics)

		self.rank = QtGui.QPushButton('Rank subspaces', self)
		self.form_layout.addRow('', self.rank)

		self.table = QtGui.QPushButton('Open table', self)
		self.form_layout.addRow('', self.table)

		if 0:
			self.button_variables = QtGui.QPushButton('Variables', self)
			self.form_layout.addRow('', self.button_variables)


		self.fractionLabel = QtGui.QLabel('Fraction used: ...')
		self.fractionWidget = QtGui.QWidget(self)
		self.fractionLayout = QtGui.QHBoxLayout(self.fractionWidget)
		self.fractionSlider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
		self.fractionSlider.setMinimum(0)
		self.fractionSlider.setMaximum(len(possibleFractions)-1)
		self.numberLabel = QtGui.QLabel('')

		self.fractionLayout.addWidget(self.fractionSlider)
		self.fractionLayout.addWidget(self.numberLabel)
		self.fractionWidget.setLayout(self.fractionLayout)
		#self.fractionSlider.setTickInterval(len(possibleFractions))
		self.form_layout.addRow(self.fractionLabel, self.fractionWidget)


		self.fractionSlider.sliderReleased.connect(self.onFractionSet)
		self.fractionSlider.valueChanged.connect(self.onValueChanged)
		self.onValueChanged(0)


		self.button_histogram.clicked.connect(self.onOpenHistogram)
		self.statistics.clicked.connect(self.onOpenStatistics)
		self.button_2d.clicked.connect(self.onOpenScatter)
		self.button_3d.clicked.connect(self.onOpenScatter3d)
		#self.scatter1dSeries.clicked.connect(self.onOpenScatter1dSeries)
		#self.scatter2dSeries.clicked.connect(self.onOpenScatter2dSeries)
		#self.serieSlice.clicked.connect(self.onOpenSerieSlice)
		self.rank.clicked.connect(self.onOpenRank)
		self.table.clicked.connect(self.onOpenTable)

		self.setLayout(self.form_layout)
		self.signal_open_plot = vaex.events.Signal("open plot")

	def onOpenStatistics(self):

		if self.dataset is not None:
			dialog = StatisticsDialog(self, self.dataset)
			dialog.show()

	def onOpenScatter(self):
		if self.dataset is not None:
			xname, yname = self.dataset.column_names[:2]
			self.plotxy(xname, yname)

	def onOpenScatter3d(self):
		if self.dataset is not None:
			xname, yname, zname = self.dataset.column_names[:3]
			self.plotxyz(xname, yname, zname)

	def onOpenSerieSlice(self):
		if self.dataset is not None:
			xname, yname = self.dataset.rank1names[:2]
			self.plotseriexy(xname, yname)

	def onOpenScatter1dSeries(self):
		if self.dataset is not None:
			dialog = vp.SequencePlot(self, self.jobsManager, self.dataset)
			dialog.show()
			self.dataset.executor.execute()

	def onOpenScatter2dSeries(self):
		if self.dataset is not None:
			dialog = vp.ScatterSeries2dPlotDialog(self, self.dataset)
			dialog.show()

	def onOpenHistogram(self):
		if self.dataset is not None:
			xname = self.dataset.column_names[0]
			self.histogram(xname)

	def plotxy(self, xname, yname, **kwargs):
		dialog = vp.ScatterPlotDialog(self, self.jobsManager, self.dataset, app=self.app, **kwargs)
		dialog.add_layer([xname, yname], self.dataset, **kwargs)
		if not vaex.ui.hidden:
			dialog.show()
		else:
			# we get a different output size when we don't show the dialog, which makes testing impossible
			dialog.show()
			dialog.hide()
			#dialog.updateGeometry()
			#dialog.adjustSize()
		#self.dataset.executor.execute()
		#self.dataset.executor.execute()
		self.signal_open_plot.emit(dialog)
		return dialog

	def plotxyz(self, xname, yname, zname, **kwargs):
		dialog = vp.VolumeRenderingPlotDialog(self, self.jobsManager, self.dataset, **kwargs)
		dialog.add_layer([xname, yname, zname], **kwargs)
		dialog.show()
		#self.dataset.executor.execute()
		self.dataset.executor.execute()
		self.signal_open_plot.emit(dialog)
		return dialog

	def plotmatrix(self, *expressions):
		dialog = vp.ScatterPlotMatrixDialog(self, self.jobsManager, self.dataset, expressions)
		dialog.show()
		self.dataset.executor.execute()
		return dialog

	def plotxyz_old(self, xname, yname, zname):
		dialog = vp.PlotDialog3d(self, self.dataset, xname, yname, zname)
		dialog.show()

	def histogram(self, xname, **kwargs):
		dialog = vp.HistogramPlotDialog(self, self.jobsManager, self.dataset, app=self.app, **kwargs)
		dialog.add_layer([xname], **kwargs)
		dialog.show()
		#self.dataset.executor.execute()
		#self.dataset.executor.execute()
		self.signal_open_plot.emit(dialog)
		return dialog

	def onOpenRank(self):
		if self.dataset is not None:
			self.ranking()

	def onOpenTable(self):
		if self.dataset is not None:
			self.tableview()

	def onFractionSet(self):
		index = self.fractionSlider.value()
		fraction = possibleFractions[index]
		if self.dataset:
			self.dataset.set_active_fraction(fraction)
			self.numberLabel.setText("{:,}".format(len(self.dataset)))
			#self.dataset.executor.execute()
			self.dataset.executor.execute()

	def onValueChanged(self, index):
		fraction = possibleFractions[index]
		text = 'Fraction used: %9.4f%%' % (fraction*100)
		self.fractionLabel.setText(text)

	def show_dataset(self, dataset):
		self.dataset = dataset
		self.name.setText(dataset.name)
		self.label_columns.setText(str(dataset.column_count()))
		self.label_length.setText("{:,}".format(self.dataset.full_length()))
		self.numberLabel.setText("{:,}".format(len(self.dataset)))
		fraction = self.dataset.fraction
		distances = np.abs(np.array(possibleFractions) - fraction)
		index = np.argsort(distances)[0]
		self.fractionSlider.setValue(index) # this will fire an event and execute the above event code
		self.button_2d.setEnabled(self.dataset.column_count() > 0)
		#self.scatter2dSeries.setEnabled(len(self.dataset.rank1s) >= 2)
		#self.scatter3dButton.setEnabled(False)
		#self.scatter1dSeries.setEnabled(len(self.dataset.rank1s) >= 1)
		#self.serieSlice.setEnabled(len(self.dataset.rank1s) >= 2)

		self.histogramMenu = QtGui.QMenu(self)
		for column_name in self.dataset.get_column_names():
			#action = QtGui.QAction
			#QtGui.QAction(QtGui.QIcon(iconfile('glue_cross')), '&Pick', self)
			action = QtGui.QAction(column_name, self)
			action.triggered.connect(functools.partial(self.histogram, xname=column_name))
			self.histogramMenu.addAction(action)
		self.button_histogram.setMenu(self.histogramMenu)

		self.scatterMenu = QtGui.QMenu(self)
		for column_name1 in self.dataset.get_column_names():
			#action1 = QtGui.QAction(column_name, self)
			submenu = self.scatterMenu.addMenu(column_name1)
			for column_name2 in self.dataset.get_column_names():
				action = QtGui.QAction(column_name2, self)
				action.triggered.connect(functools.partial(self.plotxy, xname=column_name1, yname=column_name2))
				submenu.addAction(action)
		self.button_2d.setMenu(self.scatterMenu)

		self.scatterMenu3d = QtGui.QMenu(self)
		if 0: # TODO 3d menu takes long to generate when many columns are present, can we do this lazy?
			for column_name1 in self.dataset.get_column_names():
				#action1 = QtGui.QAction(column_name, self)
				submenu = self.scatterMenu3d.addMenu(column_name1)
				for column_name2 in self.dataset.get_column_names():
					subsubmenu = submenu.addMenu(column_name2)
					for column_name3 in self.dataset.get_column_names():
						action = QtGui.QAction(column_name3, self)
						action.triggered.connect(functools.partial(self.plotxyz, xname=column_name1, yname=column_name2, zname=column_name3))
						subsubmenu.addAction(action)
		self.button_3d.setMenu(self.scatterMenu3d)

		if 0:
			self.serieSliceMenu = QtGui.QMenu(self)
			for column_name1 in self.dataset.rank1names:
				#action1 = QtGui.QAction(column_name, self)
				submenu = self.serieSliceMenu.addMenu(column_name1)
				for column_name2 in self.dataset.rank1names:
					action = QtGui.QAction(column_name2, self)
					action.triggered.connect(functools.partial(self.plotseriexy, xname=column_name1, yname=column_name2))
					submenu.addAction(action)
			self.serieSlice.setMenu(self.serieSliceMenu)

	def plotseriexy(self, xname, yname):
		if self.dataset is not None:
			dialog = vp.Rank1ScatterPlotDialog(self, self.jobsManager, self.dataset, xname+"[index]", yname+"[index]")
			self.dataset.executor.execute()
			self.signal_open_plot.emit(dialog)
			dialog.show()

	def tableview(self):
		dialog = TableDialog(self.dataset, self)
		dialog.show()
		return dialog

	def ranking(self, **options):
		dialog = RankDialog(self.dataset, self, self, **options)
		dialog.show()
		return dialog

	def pca(self, **options):
		#dialog = RankDialog(self.dataset, self, self, **options)
		#dialog.show()
		#return dialog
		import vaex.pca
		vaex.pca.pca(self.dataset, self.dataset.get_column_names(), self.jobsManager)


import psutil

class WidgetUsage(QtGui.QWidget):
	def __init__(self, parent):
		super(WidgetUsage, self).__init__(parent)
		self.setMinimumHeight(16)
		self.setMinimumWidth(100)
		self.timer = QtCore.QTimer(self)
		self.timer.timeout.connect(self.update)
		self.timer.start(500)
		self.t_prev = time.time()
		self.bytes_read_prev = psutil.disk_io_counters().read_bytes

	def paintEvent(self, event):
		painter = QtGui.QPainter()
		painter.begin(self)
		painter.fillRect(event.rect(), QtGui.QBrush(QtCore.Qt.white))
		size = self.size()
		width, height = size.width(), size.height()
		self.tool_lines = []
		#self.tool_text = ""
		try:
			def drawbar(index, count, fraction, color=QtCore.Qt.red):
				if fraction == fraction: # check nan
					#print "bar", index, count, height * (index)/ count, height * (index+1)/ count
					rect = QtCore.QRect(0, height * (index)/ count, int(width*fraction+0.5), height/count)
					#painter.setBrush(QtGui.QBrush(QtCore.Qt.blue))
					painter.fillRect(rect, QtGui.QBrush(color))

			cpu_fraction = psutil.cpu_percent()/100.
			#print cpu_fraction
			drawbar(0, 4, cpu_fraction, QtCore.Qt.green)
			self.tool_lines.append("Cpu usage: %.1f%%" % (cpu_fraction*100,))


			vmem = psutil.virtual_memory()
			mem_fraction = (vmem.total-vmem.available) * 1./vmem.total
			self.tool_lines.append("Virtual memory: %s used of %s (=%.1f%%)%%" % (vaex.utils.filesize_format(vmem.total-vmem.available), vaex.utils.filesize_format(vmem.total), mem_fraction*100.))
			drawbar(1, 4, mem_fraction, QtCore.Qt.red)

			swapmem = psutil.swap_memory()
			swap_fraction = swapmem.used * 1./swapmem.total
			drawbar(2, 4, swap_fraction, QtCore.Qt.blue)
			self.tool_lines.append("Swap memory: %s used of %s (=%.1f%%)" % (vaex.utils.filesize_format(swapmem.used), vaex.utils.filesize_format(swapmem.total), swap_fraction*100.))

			self.t_now = time.time()
			self.bytes_read_new = psutil.disk_io_counters().read_bytes
			bytes_per_second = (self.bytes_read_new - self.bytes_read_prev) / (self.t_now - self.t_prev)
			Mbytes_per_second = bytes_per_second/1024**2
			# go from 1 mb to 10*1024 mb/s in log spacing
			disk_fraction = np.clip(np.log2(Mbytes_per_second)/np.log2(10*1024), 0, 1)
			drawbar(3, 4, disk_fraction, QtCore.Qt.magenta)
			self.tool_lines.append("Reading at %.2f MiB/s" % (Mbytes_per_second,))



			self.t_prev = self.t_now
			self.bytes_read_prev = self.bytes_read_new



			self.tool_text = "\n".join(self.tool_lines)
			painter.end()
			self.setToolTip(self.tool_text)
		except:
			pass
from vaex.ui.plot_windows import PlotDialog

class VaexApp(QtGui.QMainWindow):
	"""
	:type windows: list[PlotDialog]
	"""

	signal_samp_notification = QtCore.pyqtSignal(str, str, str, dict, dict)
	signal_samp_call = QtCore.pyqtSignal(str, str, str, str, dict, dict)

	def __init__(self, argv=[], open_default=False):
		super(VaexApp, self).__init__()

		self.windows = []
		self.current_window = None
		self.current_dataset = None

		QtGui.QToolTip.setFont(QtGui.QFont('SansSerif', 10))

		#self.setToolTip('This is a <b>QWidget</b> widget')


		if 0:
			qbtn = QtGui.QPushButton('Quit', self)
			qbtn.clicked.connect(QtCore.QCoreApplication.instance().quit)
			qbtn.resize(qbtn.sizeHint())
			qbtn.move(150, 150)

			btn = QtGui.QPushButton('Button', self)
			btn.setToolTip('This is a <b>QPushButton</b> widget')
			btn.resize(btn.sizeHint())
			btn.move(50, 50)


		#self.setGeometry(300, 300, 250, 150)
		self.resize(700,500)
		#self.center()
		#self.setWindowTitle('vaex samp test')
		self.setWindowTitle('V\xe6X v' + vaex.__version__)
		#self.statusBar().showMessage('Ready')

		self.toolbar = self.addToolBar('Main toolbar')


		self.left = QtGui.QFrame(self)
		self.left.setFrameShape(QtGui.QFrame.StyledPanel)

		self.dataset_selector = DatasetSelector(self.left)
		self.dataset_selector.setMinimumWidth(300)

		self.dataset_panel = DatasetPanel(self, self.dataset_selector.datasets) #QtGui.QFrame(self)
		self.dataset_panel.setFrameShape(QtGui.QFrame.StyledPanel)
		self.main_panel = self.dataset_panel

		self.splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
		self.splitter.addWidget(self.left)
		self.splitter.addWidget(self.dataset_panel)

		#self.hbox = QtGui.QHBoxLayout(self)
		#self.hbox.addWidget(self.splitter)
		self.setCentralWidget(self.splitter)
		#self.setLayout(self.hbox)


		# this widget uses a time which causes an fps drop for opengl
		#self.widget_usage = WidgetUsage(self.left)

		#self.list.resize(30

		self.boxlist = QtGui.QVBoxLayout(self.left)
		self.boxlist.addWidget(self.dataset_selector)
		#self.boxlist.addWidget(self.widget_usage)
		self.left.setLayout(self.boxlist)

		def on_dataset_select(dataset):
			self.current_dataset = dataset
			self.dataset_panel.show_dataset(dataset)
		self.dataset_selector.signal_dataset_select.connect(on_dataset_select)
		#self.list.currentItemChanged.connect(self.infoPanel.onDataSelected)
		#self.dataset_selector.currentItemChanged.connect(self.dataset_panel.onDataSelected)
		#self.dataset_selector.currentItemChanged.connect(self.dataset_panel.onDataSelected)
		#self.list.testfill()

		if not vaex.ui.hidden:
			self.show()
			self.raise_()

		#self.list.itemSelectionChanged.connect(self.right.onDataSelected)



		#self.action_open = QtGui.QAction(vp.iconfile('quickopen-file', '&Open', self)
		#self.action_open.
		self.action_open_hdf5_gadget = QtGui.QAction(QtGui.QIcon(vp.iconfile('table-import')), '&Open gadget hdf5', self)
		self.action_open_hdf5_vaex = QtGui.QAction(QtGui.QIcon(vp.iconfile('table-import')), '&Open GAIA hdf5', self)
		self.action_open_hdf5_amuse = QtGui.QAction(QtGui.QIcon(vp.iconfile('table-import')), '&Open Amuse hdf5', self)
		self.action_open_fits = QtGui.QAction(QtGui.QIcon(vp.iconfile('table-import')), '&Open FITS (binary table)', self)


		self.action_save_hdf5 = QtGui.QAction(QtGui.QIcon(vp.iconfile('table-export')), '&Export to hdf5', self)
		self.action_save_fits = QtGui.QAction(QtGui.QIcon(vp.iconfile('table-export')), '&Export to fits', self)

		exitAction = QtGui.QAction(QtGui.QIcon('icons/png/24x24/actions/application-exit-2.png'), '&Exit', self)
		exitAction.setShortcut('Ctrl+Q')
		exitAction.setShortcut('Alt+Q')
		exitAction.setStatusTip('Exit application')
		exitAction.triggered.connect(QtGui.qApp.quit)
		self.samp = None


		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		self.menu_open = fileMenu.addMenu("&Open")
		self.menu_open.addAction(self.action_open_hdf5_gadget)
		self.menu_open.addAction(self.action_open_hdf5_vaex)
		self.menu_open.addAction(self.action_open_hdf5_amuse)
		if (not frozen) or darwin:
			self.menu_open.addAction(self.action_open_fits)
		fileMenu.addAction(self.action_save_hdf5)
		fileMenu.addAction(self.action_save_fits)
		#fileMenu.addAction(self.action_open)
		fileMenu.addAction(exitAction)


		self.menu_data = menubar.addMenu('&Data')
		def check_memory(bytes):
			if bytes > psutil.virtual_memory().available:
				if bytes < (psutil.virtual_memory().available +psutil.swap_memory().free):
					text = "Action requires %s, you have enough swap memory available but it will make your computer slower, do you want to continue?" % (vaex.utils.filesize_format(bytes),)
					return confirm(self, "Memory usage issue", text)
				else:
					text = "Action requires %s, you do not have enough swap memory available, do you want try anyway?" % (vaex.utils.filesize_format(bytes),)
					return confirm(self, "Memory usage issue", text)

			return True
		for level in [20, 25, 27, 29, 30, 31, 32]:
			N = 2**level
			action = QtGui.QAction('Generate Soneira Peebles fractal: N={:,}'.format(N), self)
			def do(ignore=None, level=level):
				if level < 29:
					if check_memory(4*8*2**level):
						sp = SoneiraPeebles(dimension=4, eta=2, max_level=level, L=[1.1, 1.3, 1.6, 2.])
						self.dataset_selector.add(sp)
				else:
					if check_memory(2*8*2**level):
						sp = SoneiraPeebles(dimension=2, eta=2, max_level=level, L=[1.6, 2.])
						self.dataset_selector.add(sp)
			action.triggered.connect(do)
			self.menu_data.addAction(action)

		for dim in [2,3]:
			if dim == 3:
				res = [128, 256, 512, 1024]
			if dim == 2:
				res = [512, 1024, 2048]
			for N in res:
				for power in [-1.5, -2.5]:
					count = N**dim
					name = 'Zeldovich d={dim} N={N:,}, count={count:,} powerspectrum={power:}'.format(**locals())
					action = QtGui.QAction('Generate '+name, self)
					def do(ignore=None, dim=dim, N=N, power=power, name=name):
						t = None
						z = vaex.dataset.Zeldovich(dim, N, power, t, name=name)
						self.dataset_selector.add(z)
					action.triggered.connect(do)
					self.menu_data.addAction(action)


		use_toolbar = "darwin" not in platform.system().lower()
		use_toolbar = True
		self.toolbar.setIconSize(QtCore.QSize(16, 16))
		#self.toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)

		#self.toolbar.addAction(exitAction)

		self.action_samp_connect = QtGui.QAction(QtGui.QIcon(vp.iconfile('plug-connect')), 'Connect to SAMP HUB', self)
		self.action_samp_connect.setShortcut('Alt+S')
		self.action_samp_connect.setCheckable(True)
		if use_toolbar:
			self.toolbar.addAction(self.action_samp_connect)
		self.action_samp_connect.triggered.connect(self.onSampConnect)

		if 1:
			self.action_samp_table_send = QtGui.QAction(QtGui.QIcon(vp.iconfile('table--arrow')), 'Send active dataset via SAMP', self)
			self.action_samp_table_send.setShortcut('Alt+T')
			if use_toolbar:
				self.toolbar.addAction(self.action_samp_table_send)
			self.action_samp_table_send.triggered.connect(self.onSampSend)

		self.action_samp_sand_table_select_row_list = QtGui.QAction(QtGui.QIcon(vp.iconfile('block--arrow')), 'Send selection via SAMP(table.select.rowlist)', self)
		self.action_samp_sand_table_select_row_list.setShortcut('Alt+R')
		if use_toolbar:
			self.toolbar.addAction(self.action_samp_sand_table_select_row_list)
		self.action_samp_sand_table_select_row_list.triggered.connect(self.on_samp_send_table_select_rowlist)

		self.toolbar.addSeparator()

		self.action_save_hdf5.triggered.connect(self.onExportHdf5)
		self.action_save_fits.triggered.connect(self.onExportFits)

		self.sampMenu = menubar.addMenu('&Samp')
		self.sampMenu.addAction(self.action_samp_connect)
		#self.sampMenu.addAction(self.action_samp_table_send)
		self.sampMenu.addAction(self.action_samp_sand_table_select_row_list)


		if use_toolbar:
			#self.toolbar.addAction(self.action_open_hdf5_gadget)
			#self.toolbar.addAction(self.action_open_hdf5_vaex)
			#if (not frozen) or darwin:
			#	self.toolbar.addAction(self.action_open_fits)
			self.toolbar.addAction(self.action_save_hdf5)
			self.toolbar.addAction(self.action_save_fits)

		if len(argv) == 0 and open_default:
			if custom is not None:
				custom.loadDatasets(self.dataset_selector)
				custom.openPlots(self.dataset_panel)
			elif 1:#frozen:
				#for index, name in list(enumerate("gas halo disk stars sat".split()))[::-1]:
				#	self.dataset_selector.open(os.path.join(application_path, 'data/disk-galaxy.hdf5'), particle_name=name)
				#f = vaex.utils.get_data_file("data/helmi-dezeeuw-2000-10p.hdf5")
				#if f and os.path.exists(f):
				#	self.dataset_selector.open(f)
				#self.dataset_selector.open(os.path.join(application_path, "data/Aq-A-2-999-shuffled-fraction.hdf5"))
				dataset_example = vaex.example()
				if dataset_example:
					self.dataset_selector.add(dataset_example)
		for pluginpath in [os.path.expanduser('~/.vaex/plugin')]:
			logger.debug("pluginpath: %s" % pluginpath)
			if os.path.exists(pluginpath):
				import glob
				paths = glob.glob(pluginpath + "/*.py")
				for path in paths:
					logger.debug("plugin file: %s" % path)
					filename = os.path.basename(path)
					name = os.path.splitext(filename)[0]
					imp.load_source('vaexuser.plugin.' + name, path)

		self.open_generators = [] # for reference counts
		self.action_open_hdf5_gadget.triggered.connect(self.openGenerator(self.gadgethdf5, "Gadget HDF5 file", "*.hdf5"))
		self.action_open_hdf5_vaex.triggered.connect(self.openGenerator(self.gaia_hdf5, "Gaia HDF5 file", "*.hdf5"))
		self.action_open_hdf5_amuse.triggered.connect(self.openGenerator(self.amuse_hdf5, "Amuse HDF5 file", "*.hdf5"))
		if (not frozen) or darwin:
			self.action_open_fits.triggered.connect(self.openGenerator(self.open_fits, "FITS file", "*.fits"))
		self.help_menu = menubar.addMenu('&Help')

		self.action_help = QtGui.QAction("Help", self)
		self.action_credits = QtGui.QAction("Credits", self)
		self.help_menu.addAction(self.action_help)
		self.help_menu.addAction(self.action_credits)

		self.action_help.triggered.connect(self.onActionHelp)
		self.action_credits.triggered.connect(self.onActionCredits)


		self.signal_samp_notification.connect(self.on_samp_notification)
		self.signal_samp_call.connect(self.on_samp_call)

		QtCore.QCoreApplication.instance().aboutToQuit.connect(self.clean_up)
		self.action_samp_connect.setChecked(True)
		self.onSampConnect(ignore_error=True)
		self.dataset_selector.signal_pick.connect(self.on_pick)

		self.samp_ping_timer = QtCore.QTimer()
		self.samp_ping_timer.timeout.connect(self.on_samp_ping_timer)
		#self.samp_ping_timer.start(1000)

		self.highlighed_row_from_samp = False

		def on_open_plot(plot_dialog):
			plot_dialog.signal_samp_send_selection.connect(lambda dataset: self.on_samp_send_table_select_rowlist(dataset=dataset))
			if kernel:
				kernel.shell.push({"plot":plot_dialog})
				kernel.shell.push({"layer":plot_dialog.current_layer})
			self.windows.append(plot_dialog) # TODO remove from list

			def on_close(window):
				self.windows.remove(window)
				if self.current_window == window:
					self.current_window = None
			plot_dialog.signal_closed.connect(on_close)
			self.current_window = plot_dialog

		self.dataset_panel.signal_open_plot.connect(on_open_plot)

		self.signal_promise.connect(self.on_signal_promise)
		self.parse_args(argv)


	signal_promise = QtCore.pyqtSignal(object, object)
	#signal_promise = QtCore.pyqtSignal(str)
	def send_to_main_thread(self, promise, value):
		#print "send promise to main thread using signal", threading.currentThread()
		self.signal_promise.emit(promise, value)
		#self.signal_promise.emit("blaat")

	def on_signal_promise(self, promise, value):
		#print "got promise, and should send it value", value, threading.currentThread()
		promise.fulfill(value)


	def parse_args(self, args):
		#args = sys.argv[1:]
		index = 0
		def error(msg):
			print(msg, file=sys.stderr)
			sys.exit(1)
		hold_plot = False
		plot = None
		while index < len(args):
			filename = args[index]
			filename = args[index]
			print("filename", filename)
			dataset = None
			if filename.startswith("http://"):
				o = urlparse(filename)
				assert o.scheme == "http"
				server = vaex.server(hostname=o.hostname, port = o.port or 80, thread_mover=self.send_to_main_thread)
				datasets = server.datasets()
				first_name = datasets[0].name
				name_list = ", ".join([dataset.name for dataset in datasets])
				if o.path in ["", "/"]:
					if filename.endswith("/"):
						filename = filename[:-1]
					error("please provide a dataset in the url, like %s/%s, or any other dataset from: %s" % (filename, first_name, name_list))
				else:
					name = o.path[1:]
					found = [dataset for dataset in datasets if dataset.name == name]
					if found:
						dataset = found[0]
					else:
						error("could not find dataset %s at the server, choose from: %s" % (name, name_list))
			elif filename[0] == ":": # not a filename, but a classname
				classname = filename.split(":")[1]
				if classname not in vaex.dataset.dataset_type_map:
					print(classname, "does not exist, options are", sorted(vaex.dataset.dataset_type_map.keys()))
					sys.exit(-1)
				class_ = vaex.dataset.dataset_type_map[classname]
				clsargs = [eval(value) for value in filename.split(":")[2:]]
				dataset = class_(*clsargs)
			else:
				options = filename.split(":")
				clsargs = [eval(value) for value in options[1:]]
				filename = options[0]
				dataset = vaex.dataset.load_file(filename, *clsargs)
			if dataset is None:
				error("cannot open file {filename}".format(**locals()))
			index += 1
			self.dataset_selector.add(dataset)

			# for this dataset, keep opening plots (seperated by -) or add layers (seperated by +)
			plot = plot if hold_plot else None
			options = {}
			# if we find --<task> we don't plot but do sth else
			if index < len(args) and args[index].startswith("--") and len(args[index]) > 2:
				task_name = args[index][2:]
				index += 1
				if task_name in ["rank", "pca"]:
					options = {}
					while  index < len(args):
						if args[index] == "-":
							index += 1
							break
						elif args[index] == "--":
							index += 1
							break
						elif "=" in args[index]:
							key, value = args[index].split("=",1)
							options[key] = value
						else:
							error("unkown option for task %r: %r " % (task_name, args[index]))
						index += 1
					if task_name == "rank":
						self.dataset_panel.ranking(**options)
					if task_name == "pca":
						self.dataset_panel.pca(**options)

				else:
					error("unkown task: %r" % task_name)
			#else:
			if 1:
				while index < len(args) and args[index] != "--":
					columns = []
					while  index < len(args) and args[index] not in ["+", "-", "--", "++"]:
						if "=" in args[index]:
							key, value = args[index].split("=",1)
							if ":" in key:
								type, key = key.split(":", 1)
								if type == "vcol":
									dataset.virtual_columns[key] = value
								elif type == "var":
									dataset.variables[key] = value
								else:
									error("unknown expression, %s, type %s not recognized" % (type + ":" + key, type))
							else:
								options[key] = value
						else:
							columns.append(args[index])
						index += 1
					if plot is None:
						if len(columns) == 1:
							plot = self.dataset_panel.histogram(columns[0], **options)
						elif len(columns) == 2:
							plot = self.dataset_panel.plotxy(columns[0], columns[1], **options)
						elif len(columns) == 3:
							plot = self.dataset_panel.plotxyz(columns[0], columns[1], columns[2], **options)
						else:
							error("cannot plot more than 3 columns yet: %r" % columns)
					else:
						layer = plot.add_layer(columns, dataset=dataset, **options)
						layer.jobs_manager.execute()
					options = {}
					if index < len(args) and args[index] == "-":
						plot = None # set to None to create a new plot, + will do a new layer
					if index < len(args) and args[index] == "--":
						hold_plot = False
						break # break out for the next dataset
					if index < len(args) and args[index] == "++":
						hold_plot = True
						break # break out for the next dataset, but keep the same plot
					index += 1
			if index < len(args):
				pass
			index += 1

	def on_samp_ping_timer(self):
		if self.samp:
			connected = self.samp.client.isConnected()
			#print "samp is", "connected" if connected else "disconnected!"
			if not connected:
				self.samp = None
		if self.samp:
			try:
				self.samp.client.ping()
			except:
				print("oops, ping went wrong, disconnect detected")
				try:
					self.samp.disconnect()
				except:
					pass
				self.samp = None
		self.action_samp_connect.setChecked(self.samp is not None)


	def on_pick(self, dataset, row):
		logger.debug("samp pick event")
		# avoid sending an event if this was caused by a samp event
		if self.samp and not self.highlighed_row_from_samp: # TODO: check if connected,
			kwargs = {"row": str(row)}
			if dataset.samp_id:
				kwargs["table-id"] = dataset.samp_id
				#kwargs["url"] = "file:" + dataset.filename
				kwargs["url"] = dataset.samp_id #
			else:
				if dataset.path:
					kwargs["table-id"] = "file:" + dataset.path
					kwargs["url"] = "file:" + dataset.path
				else:
					kwargs["table-id"] = "file:" + dataset.name
					kwargs["url"] = "file:" + dataset.name
			self.samp.client.enotifyAll("table.highlight.row", **kwargs)

	def on_samp_send_table_select_rowlist(self, ignore=None, dataset=None):
		if self.samp: # TODO: check if connected
			dataset = dataset or self.dataset_panel.dataset
			rows = []
			if dataset.mask is not None:
				rows = np.arange(len(dataset))[dataset.mask]
			rowlist = list(map(str, rows))

			kwargs = {"row-list": rowlist}
			if dataset.samp_id:
				kwargs["table-id"] = dataset.samp_id
				#kwargs["url"] = "file:" + dataset.filename
				kwargs["url"] = "file:" +dataset.samp_id #
			else:
				kwargs["table-id"] = "file:" + dataset.path
			self.samp.client.enotifyAll("table.select.rowList", **kwargs)


	def onActionHelp(self):
		filename = vaex.utils.get_data_file("doc/index.html")
		url = "file://" + filename
		vaex.utils.os_open(url)
		#self.webDialog("doc/index.html")

	def onActionCredits(self):
		filename = vaex.utils.get_data_file("doc/credits.html")
		url = "file://" + filename
		vaex.utils.os_open(url)
		#vaex.utils.os_open("doc/credits.html")
		#self.webDialog("html/credits.html")

	def _webDialog(self, url):
		view = QWebView()
		view.load(QtCore.QUrl(url))
		dialog = QtGui.QDialog(self)
		layout = QtGui.QVBoxLayout()
		dialog.setLayout(layout)
		#text = file("html/credits.html").read()
		#print text
		#label = QtGui.QLabel(text, dialog)
		#layout.addWidget(label)
		layout.addWidget(view)
		dialog.resize(300, 300)
		dialog.show()

	def onExportHdf5(self):
		self.export("hdf5")

	def onExportFits(self):
		self.export("fits")

	def export(self, type="hdf5"):
		dataset = self.dataset_panel.dataset
		name = dataset.name + "-mysubset.hdf5"
		options = ["All: %r records, filesize: %r" % (len(dataset), vaex.utils.filesize_format(dataset.byte_size())) ]
		options += ["Selection: %r records, filesize: %r" % (dataset.length(selection=True), vaex.utils.filesize_format(dataset.byte_size(selection=True))) ]

		index = choose(self, "What do you want to export?", "Choose what to export:", options)
		if index is None:
			return
		export_selection = index == 1


		#select_many(None, "lala", ["aap", "noot"] + ["item-%d-%s" % (k, "-" * k) for k in range(30)])
		ok, columns_mask = select_many(self, "Select columns", dataset.get_column_names())
		if not ok: # cancel
			return

		selected_column_names = [column_name for column_name, selected in zip(dataset.get_column_names(), columns_mask) if selected]

		shuffle = dialog_confirm(self, "Shuffle?", "Do you want the dataset to be shuffled (output the rows in random order)")
		if shuffle and dataset.full_length() != len(dataset):
			dialog_info(self, "Shuffle", "You selected shuffling while not exporting the full dataset, will select random rows from the full dataset")
			partial_shuffle = True
		else:
			partial_shuffle = False

		if export_selection and shuffle:
			dialog_info(self, "Shuffle", "Shuffling with selection not supported")
			return

		if type == "hdf5":
			endian_options = ["Native", "Little endian", "Big endian"]
			index = choose(self, "Which endianness", "Which endianness / byte order:", endian_options)
			if index is None:
				return
			endian_option = ["=", "<", ">"][index]


		if type == "hdf5":
			filename = QtGui.QFileDialog.getSaveFileName(self, "Save to HDF5", name, "HDF5 *.hdf5")
			if isinstance(filename, tuple):
				filename = str(filename[0])#]
		else:
			filename = QtGui.QFileDialog.getSaveFileName(self, "Save to col-fits", name, "FITS (*.fits)")
			if isinstance(filename, tuple):
				filename = str(filename[0])#]
		#print args
		filename = str(filename)
		if not filename.endswith("."+type):
			filename += "." + type
		if filename:
			progress_dialog = QtGui.QProgressDialog("Copying data...", "Abort export", 0, 1000, self);
			progress_dialog.setWindowModality(QtCore.Qt.WindowModal);
			progress_dialog.setMinimumDuration(0)
			progress_dialog.setAutoClose(False)
			progress_dialog.setAutoReset(False)
			progress_dialog.show()
			QtCore.QCoreApplication.instance().processEvents()
			def progress(fraction):
				progress_dialog.setValue(int(fraction*1000))
				QtCore.QCoreApplication.instance().processEvents()
				if progress_dialog.wasCanceled():
					dialog_info(self, "Cancel", "Export cancelled")
					return False
				return True

			if type == "hdf5":
				vaex.export.export_hdf5(dataset, filename, column_names=selected_column_names, shuffle=shuffle, selection=export_selection, byteorder=endian_option, progress=progress)
			if type == "fits":
				vaex.export.export_fits(dataset, filename, column_names=selected_column_names, shuffle=shuffle, selection=export_selection, progress=progress)
			progress_dialog.hide()

	def gadgethdf5(self, filename):
		print("filename", filename, repr(filename))
		for index, name in list(enumerate("gas halo disk bulge stars sat".split()))[::-1]:
			self.dataset_selector.addGadgetHdf5(str(filename), name, index)

	def gaia_hdf5(self, filename):
		self.dataset_selector.addHdf5(str(filename))

	def amuse_hdf5(self, filename):
		self.dataset_selector.addAmuse(str(filename))

	def open_fits(self, filename):
		self.dataset_selector.addFits(str(filename))


	def openGenerator(self, callback_, description, filemask):
		#print repr(callback_)
		def open(arg=None, callback_=callback_, filemask=filemask):
			#print repr(callback_), repr(filemask)
			filename = QtGui.QFileDialog.getOpenFileName(self, description, "", filemask)
			if isinstance(filename, tuple):
				filename = str(filename[0])#]
			#print repr(callback_)
			callback_(filename)
		self.open_generators.append(open)
		return open

	def onSampConnect(self, ignore_error=False):
		if self.action_samp_connect.isChecked():
			if self.samp is None:
					self.samp = Samp(daemon=True, name="vaex")
					#self.samp.tableLoadCallbacks.append(self.onLoadTable)
					connected = self.samp.client.isConnected()
					#print "samp is connected:", connected
					if connected:
						self.samp.client.bindReceiveNotification("table.highlight.row", self._on_samp_notification)
						self.samp.client.bindReceiveCall("table.select.rowList", self._on_samp_call)
						self.samp.client.bindReceiveNotification("table.load.votable", self._on_samp_notification)
						self.samp.client.bindReceiveCall("table.load.votable", self._on_samp_call)
						self.samp.client.bindReceiveNotification("table.load.fits", self._on_samp_notification)
						self.samp.client.bindReceiveCall("table.load.fits", self._on_samp_call)
					else:
						if not ignore_error:
							dialog_error(self, "Connecting to SAMP server", "Could not connect, make sure a SAMP HUB is running (for instance TOPCAT)")
						self.samp = None
						self.action_samp_connect.setChecked(False)
		else:
			print("disconnect")
			#try:
			self.samp.client.disconnect()
			self.samp = None
		#self.action_samp_connect.setText("disconnect from SAMP HUB" if self.samp else "conncet to SAMP HUB")
			#except:
			#	dialog_exception(self, "Connecting to SAMP server", "Could not connect, make sure a SAMP HUB is running (for instance TOPCAT)")



	def _on_samp_notification(self, private_key, sender_id, mtype, params, extra):
		# this callback will be in a different thread, so we use pyqt's signal mechanism to
		# push an event in the main thread's event loop
		print(private_key, sender_id, mtype, params, extra)
		self.signal_samp_notification.emit(private_key, sender_id, mtype, params, extra)

	def _on_samp_call(self, private_key, sender_id, msg_id, mtype, params, extra):
		# same as _on_samp_notification
		#print private_key, sender_id, msg_id, mtype, params, extra
		self.signal_samp_call.emit(private_key, sender_id, msg_id, mtype, params, extra)
		self.samp.client.ereply(msg_id, sampy.SAMP_STATUS_OK, result = {"txt": "printed"})

	def on_samp_notification(self, private_key, sender_id, mtype, params, extra):
		# and this should execute in the main thread
		logger.debug("samp notification: %r" % ((private_key, sender_id, mtype),))
		assert QtCore.QThread.currentThread() == main_thread
		def dash_to_underscore(hashmap):
			hashmap = dict(hashmap) # copy
			for key, value in list(hashmap.items()):
				del hashmap[key]
				hashmap[key.replace("-", "_")] = value
			return hashmap
		params = dash_to_underscore(params)
		if mtype == "table.highlight.row":
			self.samp_table_highlight_row(**params)
		if mtype == "table.select.rowList":
			self.samp_table_select_rowlist(**params)
		if mtype == "table.load.votable":
			self.samp_table_load_votable(**params)


	def on_samp_call(self, private_key, sender_id, msg_id, mtype, params, extra):
		# and this should execute in the main thread
		assert QtCore.QThread.currentThread() == main_thread
		# we simply see a call as a notification
		self.on_samp_notification(private_key, sender_id, mtype, params, extra)

	def samp_table_highlight_row(self, row, url=None, table_id=None):
		logger.debug("highlight row: {url}:{row}".format(**locals()))
		print(("highlight row: {url}:{row}".format(**locals())))
		row = int(row)
		# only supports url for the moment
		for id in (url, table_id):
			if id != None:
				for dataset in self._samp_find_datasets(id):
					# avoid triggering another samp event and an infinite loop
					self.highlighed_row_from_samp = True
					try:
						dataset.selectRow(row)
					finally:
						self.highlighed_row_from_samp = False



	def samp_table_select_rowlist(self, row_list, url=None, table_id=None):
		print("----")
		logger.debug("select rowlist: {url}".format(**locals()))
		print(("select rowlist: {url}".format(**locals())))
		row_list = np.array([int(k) for k in row_list])
		did_select = False
		datasets_updated = [] # keep a list to avoid multiple 'setMask' calls (which would do an update twice)
		for id in (url, table_id):
			if id != None:
				for dataset in self._samp_find_datasets(id):
					if dataset not in datasets_updated:
						mask = np.zeros(len(dataset), dtype=np.bool)
						mask[row_list] = True
						print("match dataset", dataset)
						dataset._set_mask(mask)
						did_select = True
					datasets_updated.append(dataset)
		if did_select:
			self.main_panel.jobsManager.execute()


	def samp_table_load_votable(self, url=None, table_id=None, name=None):
		filenames = []
		if table_id is not None:
			filename = table_id
			if filename.startswith("file:/"):
				filename = filename[5:]

			basename, ext = os.path.splitext(filename)
			if os.path.exists(filename):
				filenames.append(filename)
			for other_ext in [".hdf5", ".fits"]:
				filename = basename + other_ext
				print(filename)
				if os.path.exists(filename) and filename not in filenames:
					filenames.append(filename)
			filenames = list(filter(vaex.dataset.can_open, filenames))
		options = []
		for filename in filenames:
			options.append(filename + " | read directly from file (faster)")
		options.append(url + " | load as VOTable (slower)")
		#options.append("link to existing opened dataset")
		for dataset in self.dataset_selector.datasets:
			options.append("link to existing open dataset: " + dataset.name)
		index = choose(self, "SAMP: load table", "Choose how to load table", options)
		if index is not None:
			if index < len(filenames):
				print("open file", filenames[index])
				self.load_file(filenames[index], table_id)
			elif index  == len(filenames):
				self.load_votable(url, table_id)
				print("load votable", url)
			else:
				self.dataset_selector.datasets[index-len(filenames)-1].samp_id = table_id

	def load_file(self, path, samp_id=None):
		dataset_class = None
		for name, class_ in list(vaex.dataset.dataset_type_map.items()):
			if class_.can_open(path):
				dataset_class = class_
				break
		if dataset_class:
			dataset = dataset_class(path)
			dataset.samp_id = samp_id
			self.dataset_selector.add(dataset)

	def load_votable(self, url, table_id):
		table = astropy.io.votable.parse_single_table(url)
		print("done parsing table")
		names = table.array.dtype.names
		dataset = DatasetMemoryMapped(table_id, nommap=True)

		data = table.array.data
		for i in range(len(data.dtype)):
			name = data.dtype.names[i]
			type = data.dtype[i]
			if type.kind in ["f", "i"]: # only store float
				#datagroup.create_dataset(name, data=table.array[name].astype(np.float64))
				#dataset.addMemoryColumn(name, table.array[name].astype(np.float64))
				dataset.addColumn(name, array=table.array[name])
		dataset.samp_id = table_id
		self.dataset_selector.add(dataset)
		return dataset




	def message(self, text, index=0):
		print(text)
		self.messages[index] = text
		text = ""
		keys = list(self.messages.keys())
		keys.sort()
		text_parts = [self.messages[key] for key in keys]
		self.statusBar().showMessage(" | ".join(text_parts))

	def _samp_find_datasets(self, id):
		print(self.dataset_selector.datasets)
		try:
			for dataset in self.dataset_selector.datasets:
				if dataset.matches_url(id) or (dataset.samp_id == id):
					yield dataset
		except:
			logger.exception("problem")


	def onSampSend(self):
		if self.samp is None:
			self.onSampConnect()
		dataset = self.dataset_panel.dataset
		params = {"rows":str(dataset._length), "columns":{}}
		params['id'] = dataset.filename
		type_map = {np.float64:"F8_LE", np.float32:"F4_LE", np.int64:"I8_LE", np.int32:"I4_LE", np.uint64:"U8_LE", np.uint32:"U4_LE"}
		print(type_map)
		for column_name in dataset.column_names:
			type = dataset.dtypes[column_name]
			if hasattr(type, "type"):
				type = type.type # TODO: why is this needed?
			bytes_type = np.zeros(1, dtype=type).dtype.itemsize
			column = {
					"filename":dataset.filenames[column_name],
					"type": type_map[type],
					"byte_offset": str(dataset.offsets[column_name]),
					"type_stride": str(dataset.strides[column_name]),
					"byte_stride": str(dataset.strides[column_name]*bytes_type),
					"bytes_type": str(bytes_type),
					}
			params["columns"][column_name] = column
		self.samp.client.callAll("send_mmap_"+dataset.name,
					{"samp.mtype": "table.load.memory_mapped_columns",
						"samp.params": params})

	def onLoadTable(self, url, table_id, name):
		# this is called from a different thread!
		print("loading table", url, table_id, name)
		try:
			self.load(url, table_id, name)
		except:
			logger.exception("load table")
		return


	def load(self, url, table_id, name):
		print("parsing table...")
		table = astropy.io.votable.parse_single_table(url)
		print("done parsing table")
		names = table.array.dtype.names
		dataset = DatasetMemoryMapped(table_id, nommap=True)

		data = table.array.data
		for i in range(len(data.dtype)):
			name = data.dtype.names[i]
			type = data.dtype[i]
			if type.kind  == "f": # only store float
				#datagroup.create_dataset(name, data=table.array[name].astype(np.float64))
				dataset.addMemoryColumn(name, table.array[name].astype(np.float64))
		self.dataset_selector.add(dataset)
		if 0:
			h5file = h5py.File(hdf5filename, "w", driver="core")
			datagroup = h5file.create_group("data")
			#import pdb
			#pdb.set_trace()
			print("storing data...")

			for i in range(len(data.dtype)):
				name = data.dtype.names[i]
				type = data.dtype[i]
				if type.kind  == "f": # only store float
					datagroup.create_dataset(name, data=table.array[name].astype(np.float64))
			print("storing data done")
		#thread.interrupt_main()
		#sys.exit(0)
		#h5file.close()
		#semaphore.release()
		##samp.client.disconnect()


	def center(self):

		qr = self.frameGeometry()
		cp = QtGui.QDesktopWidget().availableGeometry().center()
		qr.moveCenter(cp)
		self.move(qr.topLeft())

	def closeEvent(self, event):
		print("close event")
		return
		reply = QtGui.QMessageBox.question(self, 'Message',
			"Are you sure to quit?", QtGui.QMessageBox.Yes |
			QtGui.QMessageBox.No, QtGui.QMessageBox.No)

		if reply == QtGui.QMessageBox.Yes:
			event.accept()
		else:
			event.ignore()

	def clean_up(self):
		print("clean up")
		if self.samp is not None:
			print("disconnect samp")
			try:
				self.samp.client.disconnect()
			except:
				logger.exception("error disconnecting from SAMP hub")
		#event.accept()
		return


app = None
kernel = None

#from qtconsole.rich_jupyter_widget import RichJupyterWidget
#from qtconsole.inprocess import QtInProcessKernelManager
#from IPython.lib import guisupport

def print_process_id():
    print(('Process ID is:', os.getpid()))

def main(argv=sys.argv[1:]):
	global main_thread
	global vaex
	global app
	global kernel
	if app is None:
		app = QtGui.QApplication(argv)
		if not (frozen and darwin): # osx app has its own icon file
			import vaex.ui.icons
			icon = QtGui.QIcon(vaex.ui.icons.iconfile('vaex32'))
			app.setWindowIcon(icon)
	#import vaex.ipkernel_qtapp
	#ipython_window = vaex.ipkernel_qtapp.SimpleWindow(app)
	main_thread = QtCore.QThread.currentThread()


	#print select_many(None, "lala", ["aap", "noot"] + ["item-%d-%s" % (k, "-" * k) for k in range(30)])
	#sys.exit(0)


	#sys._excepthook = sys.excepthook
	def qt_exception_hook(exctype, value, traceback):
		print("qt hook")
		sys.__excepthook__(exctype, value, traceback)
		qt_exception(None, exctype, value, traceback)
		#sys._excepthook(exctype, value, traceback)
		#sys.exit(1)
	sys.excepthook = qt_exception_hook
	vaex.promise.Promise.unhandled = staticmethod(qt_exception_hook)
	#raise RuntimeError, "blaat"


	vaex_app = VaexApp(argv, open_default=True)
	if 0:
		#   app = guisupport.get_app_qt4()
		print_process_id()

		# Create an in-process kernel
		# >>> print_process_id(	)
		# will print the same process ID as the main process
		kernel_manager = QtInProcessKernelManager()
		kernel_manager.start_kernel()
		kernel = kernel_manager.kernel
		kernel.gui = 'qt4'
		kernel.shell.push({'foo': 43, 'print_process_id': print_process_id, "vaex_app":vaex_app})

		kernel_client = kernel_manager.client()
		kernel_client.start_channels()

		def stop():
			kernel_client.stop_channels()
			kernel_manager.shutdown_kernel()
			app.exit()

		control = RichJupyterWidget()
		control.kernel_manager = kernel_manager
		control.kernel_client = kernel_client
		control.exit_requested.connect(stop)
		#control.show()

		sys.exit(guisupport.start_event_loop_qt4(app))


	#w = QtGui.QWidget()
	#w.resize(250, 150)
	#w.move(300, 300)
	#w.setWindowTitle('Simple')
	#w.show()
	#ipython_window.show()
	#ipython_window.ipkernel.start()
	sys.exit(app.exec_())


def batch_copy_index(from_array, to_array, shuffle_array):
	N_per_batch = int(1e7)
	length = len(from_array)
	batches = int(math.ceil(float(length)/N_per_batch))
	print(np.sum(from_array))
	for i in range(batches):
		#print "batch", i, "out of", batches, ""
		sys.stdout.flush()
		i1 = i * N_per_batch
		i2 = min(length, (i+1)*N_per_batch)
		#print "reading...", i1, i2
		sys.stdout.flush()
		data = from_array[shuffle_array[i1:i2]]
		#print "writing..."
		sys.stdout.flush()
		to_array[i1:i2] = data
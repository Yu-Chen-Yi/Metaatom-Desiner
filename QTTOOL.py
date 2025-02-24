from PySide6.QtWidgets import  QWidget, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QIcon
import logging
import traceback
import sys
from RCWA import RCWA
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class QtHandler(logging.Handler, QObject):
    log_signal = Signal(str)

    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)

class EmittingStream(QObject):
    text_written = Signal(str)

    def write(self, text):
        if text.strip():
            self.text_written.emit(text)

    def flush(self):
        pass

class OptimizationThread(QThread):
    """
    Thread to run the optimization process without freezing the GUI.
    """
    # Existing signals
    log_signal = Signal(str)

    def __init__(self, args, args_st, log_handler=None):
        super().__init__()
        self.args = args
        self.args_st = args_st
        self.log_handler = log_handler

    def run(self):
        try:
            # Create an instance of EmittingStream
            emitting_stream = EmittingStream()
            emitting_stream.text_written.connect(self.log_signal.emit)

            # Redirect stdout and stderr
            sys.stdout = emitting_stream
            sys.stderr = emitting_stream

            optimizer = RCWA(args=self.args, args_st = self.args_st, log_handler=self.log_handler)
            #optimizer.create_gif()

        except Exception as e:
            # Capture and log the exception
            error_msg = f"Unhandled exception:\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
        
        finally:
            # 清理資源
            self.optimizer = None
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

class SimDOEThread(QThread):
    """
    Thread to run the optimization process without freezing the GUI.
    """
    # Existing signals
    log_signal = Signal(str)

    def __init__(self, args, args_st, log_handler=None):
        super().__init__()
        self.args = args
        self.args_st = args_st
        self.log_handler = log_handler

    def run(self):
        # Create an instance of EmittingStream
        emitting_stream = EmittingStream()
        emitting_stream.text_written.connect(self.log_signal.emit)

        # Redirect stdout and stderr
        sys.stdout = emitting_stream
        sys.stderr = emitting_stream

        optimizer = RCWA(args=self.args, args_st = self.args_st, log_handler=self.log_handler)
        optimizer.init_target()
        optimizer.sim_DOE()

        # Restore stdout and stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

class PlotWindow(QWidget):
    """獨立新視窗用於顯示 Matplotlib 圖"""
    def __init__(self, Mx=0, My=0, parent=None, figure=None, ax=None, name="New Plot Window"):
        super().__init__(parent)
        self.setWindowTitle(name)
        self.setWindowIcon(QIcon("icon.ico"))
        self.setWindowFlag(Qt.Window)  # 設定為獨立視窗
        self.move(Mx, My)
        self.resize(550, 500) 
        self.figure = figure
        self.ax = ax
        self.initUI()

    def initUI(self):
        # 創建 Matplotlib 圖表
        self.canvas = FigureCanvas(self.figure)

        # 使用 QVBoxLayout 排版圖表
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
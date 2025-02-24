import os, sys, yaml, json, dateutil.parser
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QPlainTextEdit, QMessageBox, QApplication, QWidget, 
    QGridLayout, QGroupBox, QFormLayout, QLineEdit, 
    QComboBox, QPushButton, QFileDialog
)
from DataVisualize import DataVisualize
from PySide6.QtGui import QIcon, QFont, QAction
from utils import convert_to_number, list_material
from RCWA import RCWA
from QTTOOL import PlotWindow, QtHandler, sweeptThread, SimDOEThread

class MainWieget(QWidget):
    """
    主要的應用程式介面類別，負責處理所有GUI元件和業務邏輯
    
    屬性:
        local_hwid: 本機硬體識別碼
        license_path: 授權檔案路徑
        public_key_path: 公鑰檔案路徑
        input_fields: 儲存所有輸入欄位的字典
        plot_windows: 儲存所有繪圖視窗的列表
        args: 儲存一般參數的字典
        args_st: 儲存結構參數的列表
        is_dark_mode: 是否為深色模式
    """

    def __init__(self, yaml_file):
        super().__init__()

        """ # ===== 第一步：取得本機硬體碼 =====
        self.local_hwid = get_hardware_id()
        
        # ===== 第二步：讀取並驗證授權檔 =====
        self.license_path = "license.json"   # 假設在同一個資料夾中
        self.public_key_path = "public_key.pem" 

        try:
            self.check_license()
        except Exception as e:
            QMessageBox.critical(self, "Authorization Failed", f"Authorization check failed: {e}")
            sys.exit(1) """

        # 若通過授權，就繼續初始化 UI 或其他功能
        self.init_ui(yaml_file)
        self.input_fields["Shape type"].currentIndexChanged.connect(self.on_shape_type_changed)
        self.on_shape_type_changed()
    
    def init_ui(self, yaml_file):
        """Initialize the user interface"""
        self._init_instance_variables()
        self._setup_main_layout()
        self._create_form_groups(yaml_file)
        self._add_log_area()
        self.apply_dark_mode()

    def _init_instance_variables(self):
        """Initialize instance variables"""
        self.resize(1000, 900)
        self.input_fields = {}
        self.group_box = {}
        self.plot_windows = []
        self.args = {}
        self.args_st = []
        self.is_dark_mode = True

    def _setup_main_layout(self):
        """Setup the main layout"""
        self.main_layout = QGridLayout(self)
        self.setLayout(self.main_layout)

    def _create_form_groups(self, yaml_file):
        """Create form groups from YAML configuration"""
        form_data = self._load_yaml_config(yaml_file)
        row, col = 0, 0
        
        for form_name, form_details in form_data.get("forms", {}).items():
            self.group_box[form_name] = self._create_group_box(form_name, form_details)
            self.main_layout.addWidget(self.group_box[form_name], row, col)
            
            col += 1
            if col > 2:
                col = 0
                row += 1

    def _load_yaml_config(self, yaml_file):
        """Load YAML configuration file"""
        try:
            with open(yaml_file, 'r', encoding="utf-8") as file:
                return yaml.safe_load(file)
        except Exception as e:
            self.error_message(f"Error loading configuration: {str(e)}")
            return {}

    def _create_group_box(self, form_name, form_details):
        """Create a group box with form fields"""
        group_box = QGroupBox(form_name)
        form_layout = QFormLayout()
        group_box.setLayout(form_layout)

        for field in form_details.get("fields", []):
            self._add_field_to_group(field, group_box)

        return group_box

    def _add_field_to_group(self, field, group_box):
        """Add a field to the group box"""
        field_name = field.get("name", "")
        field_type = field.get("type", "")
        values = field.get("values", [])
        if values == 'Materials_data':
            values = list_material(material_dir="Materials_data")
        default_value = field.get("default", "")
        event = None

        if "event" in field and hasattr(self, field["event"].split('.')[-1]):
            event = getattr(self, field["event"].split('.')[-1])

        self.create_input_field(field_name, field_type, group_box, values, default_value, event)

    def _add_log_area(self):
        """Add the log text area"""
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        row = self.main_layout.rowCount()
        self.main_layout.addWidget(self.log_text, row, 0, 1, 4)

    def check_license(self):
        """
        檢查軟體授權，包含以下步驟：
        1. 讀取並解析授權檔案
        2. 驗證數位簽名
        3. 驗證硬體識別碼
        4. 驗證授權期限
        5. 檢查系統時間是否被竄改
        
        如果任何驗證步驟失敗，將拋出異常
        """
        # 讀取並 parse 授權檔
        if not os.path.exists(self.license_path):
            raise Exception("Authorization file not found")

        with open(self.license_path, "r", encoding="utf-8") as f:
            license_data = json.load(f)
        
        # 驗證簽名
        public_key = load_public_key(self.public_key_path)
        if not verify_license_signature(license_data, public_key):
            raise Exception("Authorization file signature verification failed")

        # 驗證硬體碼是否相符
        if license_data["hardware_hash"] != self.local_hwid:
            raise Exception("Hardware ID mismatch")

        # 驗證期限
        expire_str = license_data["expire_date"]  # e.g. "2025-12-31"
        expire_date = dateutil.parser.parse(expire_str).date()
        
        # 取得當前日期(此示例用本機UTC或線上NTP)
        # 1) 線上方式:
        
        ntp_ts = get_ntp_time("time.google.com")
        current_utc = datetime.utcfromtimestamp(ntp_ts).date()
        """ # 2) 離線方式:
        current_utc = datetime.utcnow().date()
        """
        
        if current_utc > expire_date:
            raise Exception("Authorization has expired")

        # 若要防止系統回撥，可檢查本地記錄
        #check_local_time_and_record()

        # ----- 全部檢查通過 -----
        print("Authorization file verified successfully, starting the program")

    def create_combo_box(self, items):
        combo_box = QComboBox()
        combo_box.addItems(items)
        combo_box.setCurrentIndex(0)
        return combo_box

    def create_input_field(self, label_text, field_type, parent_group=None, values=None, default_value="", event=None):
        """
        創建輸入欄位元件
        
        參數:
            label_text: 欄位標籤文字
            field_type: 欄位類型 (combo_box/text_input/opentargetfile/openfolder/button)
            parent_group: 父群組元件
            values: 下拉選單的選項列表
            default_value: 預設值
            event: 按鈕點擊事件處理函數
        """
        input_widget = None

        if field_type == "combo_box":
            input_widget = self.create_combo_box(values)
            self.input_fields[label_text] = input_widget
        elif field_type == "text_input":
            input_widget = QLineEdit(default_value)
            self.input_fields[label_text] = input_widget
        elif field_type == "opentargetfile":
            input_widget = QLineEdit(default_value)
            browse_targetfile_button = QPushButton('Browse')
            browse_targetfile_button.clicked.connect(self.browse_targetfile)
            
        elif field_type == "openfolder":
            input_widget = QLineEdit(default_value)
            browse_folder_button = QPushButton('Browse')
            browse_folder_button.clicked.connect(self.browse_folder)

        elif field_type == "button":  # Adding support for buttons
            input_widget = QPushButton(label_text)
            if event:
                input_widget.clicked.connect(event)
        self.input_fields[label_text] = input_widget
        if parent_group:
            layout = parent_group.layout()
            if field_type in ["combo_box", "text_input", "opentargetfile", "openfolder"]:
                layout.addRow(label_text + ":", input_widget)
                if field_type == "opentargetfile":
                    layout.addRow("", browse_targetfile_button)
                elif field_type == "openfolder":
                    layout.addRow("", browse_folder_button)
            elif field_type == "button":
                layout.addRow(input_widget)

        return input_widget

    
    def save_fields_to_yaml(self, filename: str):
        """
        將所有輸入欄位的當前值儲存到YAML檔案
        
        參數:
            filename: 要儲存的YAML檔案路徑
        """
        data = {}
        for key, widget in self.input_fields.items():
            # QLineEdit → 儲存文字
            if widget.metaObject().className() == "QLineEdit":
                data[key] = widget.text()

            # QComboBox → 儲存當前索引
            elif widget.metaObject().className() == "QComboBox":
                data[key] = widget.currentText()

            # 其他型別依需求擴充
        # 新增擴充：將 self.args_st 儲存進 YAML 資料中
        data['args_st'] = self.args_st

        with open(filename, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True)

    def load_fields_from_yaml(self, filename: str):
        """
        從YAML檔案載入設定值並更新所有輸入欄位
        
        參數:
            filename: 要讀取的YAML檔案路徑
        """
        with open(filename, 'r', encoding='utf-8') as f:
            data = yaml.load(f, Loader=yaml.UnsafeLoader)

        # 先處理 self.args_st 的資料，若存在則更新參數
        if 'args_st' in data:
            self.args_st = data.pop('args_st')
            # 如果有對應的 LayerTableWidget，可在此呼叫更新方法，例如：
            # self.layer_table_widget.update_params(self.args_st)

        for key, value in data.items():
            widget = self.input_fields.get(key)
            if widget is None:
                # 如果程式改版導致 key 不存在，可視需求做錯誤處理或跳過
                continue

            # QLineEdit → 還原文字
            if widget.metaObject().className() == "QLineEdit":
                widget.setText(value)

            # QComboBox → 還原索引
            elif widget.metaObject().className() == "QComboBox":
                # 嘗試尋找對應的文字索引
                index = widget.findText(str(value))
                if index != -1:
                    widget.setCurrentIndex(index)
                else:
                    # 若找不到，則設定為第一個選項（可視需求調整）
                    widget.setCurrentIndex(0)
        self.open_structure_table()
    
    def on_shape_type_changed(self):
        """
        根據下拉式選單選擇的 shape_type，顯示/隱藏對應的參數群組，
        並更新顯示對應的指南圖片。
        """
        current_shape = self.input_fields["Shape type"].currentText()
        if current_shape == "square":
            for _, group_box in self.group_box.items():
                group_box.setVisible(True)
            self.group_box["Parameter2 Sweept"].setVisible(False)
            self.input_fields["Parameter2"].setText("")
            self.input_fields["Parameter2 min"].setText("")
            self.input_fields["Parameter2 max"].setText("")
            self.input_fields["Parameter2 points"].setText("")
            self.group_box["Parameter3 Sweept"].setVisible(False)
            self.input_fields["Parameter3"].setText("")
            self.input_fields["Parameter3 min"].setText("")
            self.input_fields["Parameter3 max"].setText("")
            self.input_fields["Parameter3 points"].setText("")
        elif current_shape == "circle":
            for _, group_box in self.group_box.items():
                group_box.setVisible(True)
            self.group_box["Parameter2 Sweept"].setVisible(False)
            self.input_fields["Parameter2"].setText("")
            self.input_fields["Parameter2 min"].setText("")
            self.input_fields["Parameter2 max"].setText("")
            self.input_fields["Parameter2 points"].setText("")
            self.group_box["Parameter3 Sweept"].setVisible(False)
            self.input_fields["Parameter3 min"].setText("")
            self.input_fields["Parameter3 max"].setText("")
            self.input_fields["Parameter3 points"].setText("")
            self.group_box["Rotate angle Sweept"].setVisible(False)
            self.input_fields["Theta"].setText("")
            self.input_fields["Theta min"].setText("")
            self.input_fields["Theta max"].setText("")
            self.input_fields["Theta points"].setText("")
        elif current_shape == "rectangle":
            for _, group_box in self.group_box.items():
                group_box.setVisible(True)
            self.group_box["Parameter3 Sweept"].setVisible(False)
            self.input_fields["Parameter3"].setText("")
            self.input_fields["Parameter3 min"].setText("")
            self.input_fields["Parameter3 max"].setText("")
            self.input_fields["Parameter3 points"].setText("")
        elif current_shape == "ellipse":
            for _, group_box in self.group_box.items():
                group_box.setVisible(True)
            self.group_box["Parameter3 Sweept"].setVisible(False)
            self.input_fields["Parameter3"].setText("")
            self.input_fields["Parameter3 min"].setText("")
            self.input_fields["Parameter3 max"].setText("")
            self.input_fields["Parameter3 points"].setText("")
        elif current_shape == "rhombus":
            for _, group_box in self.group_box.items():
                group_box.setVisible(True)
            self.group_box["Parameter3 Sweept"].setVisible(False)
            self.input_fields["Parameter3"].setText("")
            self.input_fields["Parameter3 min"].setText("")
            self.input_fields["Parameter3 max"].setText("")
            self.input_fields["Parameter3 points"].setText("")
        elif current_shape == "hollow_square":
            for _, group_box in self.group_box.items():
                group_box.setVisible(True)
            self.group_box["Parameter3 Sweept"].setVisible(False)
            self.input_fields["Parameter3"].setText("")
            self.input_fields["Parameter3 min"].setText("")
            self.input_fields["Parameter3 max"].setText("")
            self.input_fields["Parameter3 points"].setText("")
        elif current_shape == "hollow_circle":
            for _, group_box in self.group_box.items():
                group_box.setVisible(True)
            self.group_box["Parameter3 Sweept"].setVisible(False)
            self.input_fields["Parameter3"].setText("")
            self.input_fields["Parameter3 min"].setText("")
            self.input_fields["Parameter3 max"].setText("")
            self.input_fields["Parameter3 points"].setText("")
            self.group_box["Rotate angle Sweept"].setVisible(False)
            self.input_fields["Theta"].setText("")
            self.input_fields["Theta min"].setText("")
            self.input_fields["Theta max"].setText("")
            self.input_fields["Theta points"].setText("")
        elif current_shape == "cross":
            for _, group_box in self.group_box.items():
                group_box.setVisible(True)
            self.group_box["Parameter3 Sweept"].setVisible(False)
            self.input_fields["Parameter3"].setText("")
            self.input_fields["Parameter3 min"].setText("")
            self.input_fields["Parameter3 max"].setText("")
            self.input_fields["Parameter3 points"].setText("")
    def browse_targetfile(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Target File", "", "Target Order (*.xlsx);;All Files (*)")
        if file_path:
            self.input_fields["Target File"].setText(file_path)

    def browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder_path:
            self.input_fields["Project Folder"].setText(folder_path)

    def run_sweept(self):
        self.get_gui_parameter()
        self.save_fields_to_yaml(filename=os.path.join(self.args["Project Folder"], "DOE_design.yaml"))
        # Disable the run button to prevent multiple runs
        self.input_fields["Start Optimize"].setEnabled(False)
        self.input_fields["Stop Optimize"].setEnabled(True)  # Enable the stop button
        # Create the logging handler for the GUI
        self.qt_handler = QtHandler()
        self.qt_handler.log_signal.connect(self.append_log)

        # Start the sweept in a separate thread
        self.sweept_thread = sweeptThread(args=self.args, args_st=self.args_st, log_handler=self.qt_handler)
        self.sweept_thread.log_signal.connect(self.append_log)
        self.sweept_thread.finished.connect(self.on_sweept_finished)
        self.sweept_thread.start()
        self.append_log("sweept started.")
    
    def stop_sweept(self):
        if self.sweept_thread is not None:
            # Assuming the sweeptThread has a method to stop gracefully
            self.sweept_thread.terminate()  # This forcefully stops the thread, use with caution
            self.append_log("sweept stopped by user.")
            self.on_sweept_finished()

    def on_sweept_finished(self):
        # Re-enable the run button after sweept is finished
        self.input_fields["Start Optimize"].setEnabled(True)
        self.input_fields["Stop Optimize"].setEnabled(False)  # Enable the stop button
        self.append_log("sweept finished.")

    def sim_DOE(self):
        self.get_gui_parameter()
        # Disable the run button to prevent multiple runs
        self.input_fields["RCWA Simulation"].setEnabled(False)

        # Create the logging handler for the GUI
        self.qt_handler = QtHandler()
        self.qt_handler.log_signal.connect(self.append_log)

        # Start the sweept in a separate thread
        self.simDOE_thread = SimDOEThread(args=self.args, args_st=self.args_st, log_handler=self.qt_handler)
        self.simDOE_thread.log_signal.connect(self.append_log)
        self.simDOE_thread.finished.connect(lambda: self.input_fields["RCWA Simulation"].setEnabled(True))
        self.simDOE_thread.start()
        self.append_log("RCWA running")

    def open_structure_table(self):
        self.get_gui_parameter()
        #print(len(self.args_st))
        self.table_window = DataVisualize(args=self.args, args_st=self.args_st)
        self.table_window.argsSent.connect(self.update_args_st)
        self.table_window.show()
        self.table_window.resize(900, 400)

    def get_gui_parameter(self):
        for attr, widget in self.input_fields.items():
            # 假設 widget 是 QLineEdit 或 QComboBox 等有 text() 或 currentText() 的類型
            if isinstance(widget, QLineEdit):
                raw_value = widget.text()
            elif isinstance(widget, QComboBox):
                raw_value = widget.currentText()
            else:
                raw_value = None  # 根據需要處理未知類型

            # 嘗試將值轉換為適當類型
            if raw_value is not None:
                value = convert_to_number(raw_value)
            else:
                value = raw_value  # 保留 None
            # 將 attr 作為字典的鍵，value 作為對應的值
            self.args[attr] = value
            print(f"{attr} : {value} type:{type(value)}")
    
    def update_args_st(self, new_args_st:list):
        """接收來自 LayerTableWidget 的參數並更新"""
        #print("Received new args_st in MainWidget:", new_args_st)
        self.args_st = new_args_st

    def append_log(self, text):
        self.log_text.appendPlainText(text)

    def error_message(self, text):
        """
        顯示一個錯誤訊息的對話框，只有「確認」按鈕可供關閉。
        :param text: 要顯示的錯誤訊息文字
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)       # 顯示警告圖示，可依需求改用 QMessageBox.Critical 等
        msg.setWindowTitle("Error")
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.Ok) # 只顯示「確認」按鈕
        msg.exec_()                            # 以「模態」方式顯示，直到使用者關閉

    def toggle_mode(self):
        """
        切換深夜模式 / 白天模式
        """
        if self.is_dark_mode:
            # 如果目前是深夜模式，改為白天模式
            self.apply_light_mode()
        else:
            # 如果目前是白天模式，改為深夜模式
            self.apply_dark_mode()

        # 狀態翻轉
        self.is_dark_mode = not self.is_dark_mode

    def apply_dark_mode(self):
        """
        套用深夜模式 StyleSheet
        """
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2D2D30;
            }
                           
            QWidget {
                background-color: #2B2B2B;
                color: #FFFFFF;
                font-family: Segoe UI;
            }
            QGroupBox {
                font-family: Segoe UI;
                background-color: #3C3F41;
                border: 1px solid #6E6E6E;
                border-radius: 5px;
                margin-top: 2ex;
                font-size: 10pt;
                font-weight: bold;
                padding: 10px;
            }
            QPlainTextEdit {
                font-family: Segoe UI;
                background-color: #3C3F41;
                color: #FFFFFF;
                font-size: 12pt;
            }
            
            QPushButton {
                font-family: Segoe UI;
                background-color: #878787;
                color: #FFFFFF;
                border: 1px solid #6E6E6E;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505354;
            }
            QLabel {
                font-family: Segoe UI;
                background-color: none; 
                color: #FFFFFF;
            }
        """)

    def apply_light_mode(self):
        """
        套用白天模式 StyleSheet
        （可以根據需求自行調整背景、字色等細節）
        """
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
                           
            QWidget {
                font-family: Segoe UI;
                background-color: #FFFFFF;
                color: #000000;
            }
            QLabel {
                font-family: Segoe UI;
                background-color: none;
                color: #000000;
            }
            QGroupBox {
                font-family: Segoe UI;
                background-color: #FFFFFF;
                border: 1px solid #C0C0C0;
                border-radius: 5px;
                margin-top: 2ex;
                font-size: 10pt;
                font-weight: bold;
                padding: 10px;
            }
            QPlainTextEdit {
                font-family: Segoe UI;
                background-color: #FFFFFF;
                color: #000000;
                font-size: 12pt;
            }
            QPushButton {
                font-family: Segoe UI;
                background-color: #F0F0F0;
                color: #000000;
                font-size: 12pt;
                font-weight: bold;
                border: 1px solid #C0C0C0;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)

    def update_args(self, args_st):
        self.args_st.update(args_st)  # 更新 MainWidget 的參數
        #print("Updated args in MainWidget:", self.args)

# -- 以下是我們要示範的 QMainWindow: FormApp ----
class FormApp(QMainWindow):
    """
    主視窗應用程式類別，負責整體視窗管理和選單功能
    
    屬性:
        main_widget: 主要的介面元件
        is_dark_mode: 是否為深色模式
    """

    def __init__(self, yaml_file):
        super().__init__()
        # 設定視窗大小與標題
        self.setWindowTitle("DOE Designer v1.1.2")
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(1000, 900)
        self.is_dark_mode = True
        # 建立中央的 MainWieget，並作為 QMainWindow 的 Central Widget
        self.main_widget = MainWieget(yaml_file)
        self.setCentralWidget(self.main_widget)
        self.set_dark_mode()
        # 呼叫 create_menus 建立選單
        self.create_menus()

    def create_menus(self):
        """
        創建主視窗的選單列，包含：
        - File選單：儲存/載入設定、退出程式
        - Edit選單：開啟結構表格
        - View選單：切換深淺色模式
        - Help選單：關於資訊
        """
        menubar = self.menuBar()

        # File 選單範例
        file_menu = menubar.addMenu("File")

        #建立「Save file」動作 ---
        save_action = QAction("Save file", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.on_save_file)
        file_menu.addAction(save_action)

        # 建立「Load file」動作 ---
        load_action = QAction("Load file", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.on_load_file)
        file_menu.addAction(load_action)

        # File -> Exit
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit
        edit_menu = menubar.addMenu("Edit")
        #建立「Save file」動作 ---
        open_table_action = QAction("Open ", self)
        open_table_action.setShortcut("Ctrl+L")
        open_table_action.triggered.connect(self.main_widget.open_structure_table)
        edit_menu.addAction(open_table_action)

        # View 選單範例
        view_menu = menubar.addMenu("View")

        # View -> Toggle Mode (呼叫 MainWieget 的切換模式)
        toggle_mode_action = QAction("Toggle Mode", self)
        toggle_mode_action.setShortcut("Ctrl+T")
        toggle_mode_action.triggered.connect(self.toggle_mode)
        toggle_mode_action.triggered.connect(self.main_widget.toggle_mode)
        view_menu.addAction(toggle_mode_action)

        # Help 選單範例
        help_menu = menubar.addMenu("Help")

        # Help -> About
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_message)
        help_menu.addAction(about_action)

    def on_save_file(self):
        """
        觸發「Save file」選單時，跳出對話框取得檔名並呼叫保存函式。
        """
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            "",
            "YAML Files (*.yaml);;All Files (*)"
        )
        if filename:
            self.main_widget.save_fields_to_yaml(filename)

    def on_load_file(self):
        """
        觸發「Load file」選單時，跳出對話框取得檔名並呼叫讀取函式。
        """
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "YAML Files (*.yaml);;All Files (*)"
        )
        if filename:
            self.main_widget.load_fields_from_yaml(filename)

    def show_about_message(self):
        QMessageBox.information(
            self,
            "About",
            "這是 DOE Designer 的範例應用程式。\n版本：v1.0.2"
        )

    def toggle_mode(self):
        """
        切換深淺色模式的外觀主題
        """
        if self.is_dark_mode:
            # 如果目前是深夜模式，改為白天模式
            self.set_bright_mode()
        else:
            # 如果目前是白天模式，改為深夜模式
            self.set_dark_mode()

        # 狀態翻轉
        self.is_dark_mode = not self.is_dark_mode

    def set_dark_mode(self):
        """
        使用簡易的 StyleSheet 模擬暗色佈景
        （更完整的暗色主題可另行參考 Material/QtDark 等套件）。
        """
        dark_qss = """
            QMainWindow {
                background-color: #2D2D30;
            }
            QWidget {
                color: #dddddd;
                background-color: #2D2D30;
            }
            QTableWidget {
                gridline-color: #6c6c6c;
            }
            QPushButton {
                background-color: #3E3E40;
                border: 1px solid #5A5A5A;
            }
            QPushButton:hover {
                background-color: #555557;
            }
        """
        self.setStyleSheet(dark_qss)

    def set_bright_mode(self):
        """
        清除暗色 StyleSheet，回復預設 (或自訂亮色)
        """
        bright_qss = """
            QMainWindow {
                background-color: #f0f0f0;
            }
            QWidget {
                color: #000000;
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #afafaf;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """
        self.setStyleSheet(bright_qss)

# -- 主程式入口 ----------------------------------------
if __name__ == "__main__":
    font = QFont("Segoe UI", 12)  
    app = QApplication(sys.argv)
    app.setFont(font)
    window = FormApp("config.yaml")
    window.show()
    sys.exit(app.exec())
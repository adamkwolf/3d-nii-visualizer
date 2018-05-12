import math
import time

import PyQt5.QtWidgets as QtWidgets
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkUtils import *
from config import *


class MainWindow(QtWidgets.QMainWindow, QtWidgets.QApplication):
    def __init__(self, app):
        self.app = app
        QtWidgets.QMainWindow.__init__(self, None)

        # base setup
        self.renderer, self.frame, self.vtk_widget, self.interactor, self.render_window = self.setup()
        self.brain, self.tumor = setup_brain(self.renderer, self.app.BRAIN_FILE), setup_tumor(self.renderer,
                                                                                              self.app.TUMOR_FILE)

        # setup brain projection
        self.brain_image_prop = setup_projection(self.brain, self.renderer)
        self.brain_slicer_props = setup_slicer(self.renderer, self.brain.reader)
        self.renderer.AddActor(self.brain.labels[0].actor)
        n_labels = int(self.tumor.reader.GetOutput().GetScalarRange()[1])
        n_labels = n_labels if n_labels <= 10 else 10
        for label_idx in range(n_labels):
            self.renderer.AddActor(self.tumor.labels[label_idx].actor)

        # brain pickers
        self.brain_threshold_sp = self.create_new_picker(1000, 0, 5, BRAIN_THRESHOLD, self.brain_threshold_vc)
        self.brain_opacity_sp = self.create_new_picker(1.0, 0.0, 0.1, BRAIN_OPACITY, self.brain_opacity_vc)
        self.brain_smoothness_sp = self.create_new_picker(1000, 100, 100, BRAIN_SMOOTHNESS, self.brain_smoothness_vc)
        self.brain_projection_cb = self.add_brain_projection()
        self.brain_slicer_cb = self.add_brain_slicer()

        # tumor pickers
        self.tumor_opacity_sp = self.create_new_picker(1.0, 0.0, 0.1, TUMOR_OPACITY, self.tumor_opacity_vc)
        self.tumor_smoothness_sp = self.create_new_picker(1000, 100, 100, TUMOR_SMOOTHNESS, self.tumor_smoothness_vc)
        self.tumor_label_cbs = []

        # create grid for all widgets
        self.grid = QtWidgets.QGridLayout()

        # add each widget
        self.add_vtk_window_widget()
        self.add_brain_settings_widget()
        self.add_tumor_settings_widget()
        self.add_views_widget()

        #  set layout and show
        self.render_window.Render()
        self.setWindowTitle(APPLICATION_TITLE)
        self.frame.setLayout(self.grid)
        self.setCentralWidget(self.frame)
        self.set_axial_view()
        self.interactor.Initialize()
        self.show()

    @staticmethod
    def setup():
        """
        Create and setup the base vtk and Qt objects for the application
        """
        renderer = vtk.vtkRenderer()
        frame = QtWidgets.QFrame()
        vtk_widget = QVTKRenderWindowInteractor()
        interactor = vtk_widget.GetRenderWindow().GetInteractor()
        render_window = vtk_widget.GetRenderWindow()

        frame.setAutoFillBackground(True)
        vtk_widget.GetRenderWindow().AddRenderer(renderer)
        render_window.AddRenderer(renderer)
        interactor.SetRenderWindow(render_window)
        interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        return renderer, frame, vtk_widget, interactor, render_window

    def add_brain_slicer(self):
        slicer_cb = QtWidgets.QCheckBox("")
        slicer_cb.clicked.connect(self.brain_slicer_vc)
        return slicer_cb

    def add_vtk_window_widget(self):
        base_brain_file = os.path.basename(self.app.BRAIN_FILE)
        base_tumor_file = os.path.basename(self.app.TUMOR_FILE)
        object_title = str.format("Brain: {}          Tumor: {}", base_brain_file, base_tumor_file)
        object_group_box = QtWidgets.QGroupBox(object_title)
        object_layout = QtWidgets.QVBoxLayout()
        object_layout.addWidget(self.vtk_widget)
        object_group_box.setLayout(object_layout)
        self.grid.addWidget(object_group_box, 0, 2, 5, 5)

    def add_brain_settings_widget(self):
        brain_group_box = QtWidgets.QGroupBox("Brain Settings")
        brain_group_layout = QtWidgets.QGridLayout()
        brain_group_layout.addWidget(QtWidgets.QLabel("Brain Threshold"), 0, 0)
        brain_group_layout.addWidget(QtWidgets.QLabel("Brain Opacity"), 1, 0)
        brain_group_layout.addWidget(QtWidgets.QLabel("Brain Smoothness"), 2, 0)
        brain_group_layout.addWidget(QtWidgets.QLabel("Brain Projection"), 3, 0)
        brain_group_layout.addWidget(QtWidgets.QLabel("Brain Slicer"), 4, 0)
        brain_group_layout.addWidget(self.brain_threshold_sp, 0, 1)
        brain_group_layout.addWidget(self.brain_opacity_sp, 1, 1)
        brain_group_layout.addWidget(self.brain_smoothness_sp, 2, 1)
        brain_group_layout.addWidget(self.brain_projection_cb, 3, 1)
        brain_group_layout.addWidget(self.brain_slicer_cb, 4, 1)
        brain_group_box.setLayout(brain_group_layout)
        self.grid.addWidget(brain_group_box, 0, 0, 1, 2)

    def add_tumor_settings_widget(self):
        tumor_settings_group_box = QtWidgets.QGroupBox("Tumor Settings")
        tumor_settings_layout = QtWidgets.QGridLayout()
        tumor_settings_layout.addWidget(QtWidgets.QLabel("Tumor Opacity"), 0, 0)
        tumor_settings_layout.addWidget(QtWidgets.QLabel("Tumor Smoothness"), 1, 0)
        tumor_settings_layout.addWidget(self.tumor_opacity_sp, 0, 1)
        tumor_settings_layout.addWidget(self.tumor_smoothness_sp, 1, 1)
        tumor_multi_color_radio = QtWidgets.QRadioButton("Multi Color")
        tumor_multi_color_radio.setChecked(True)
        tumor_multi_color_radio.clicked.connect(self.tumor_multi_color_radio_checked)
        tumor_single_color_radio = QtWidgets.QRadioButton("Single Color")
        tumor_single_color_radio.clicked.connect(self.tumor_single_color_radio_checked)
        tumor_settings_layout.addWidget(tumor_multi_color_radio, 2, 0)
        tumor_settings_layout.addWidget(tumor_single_color_radio, 2, 1)
        tumor_settings_layout.addWidget(self.create_new_separator(), 3, 0, 1, 2)

        self.tumor_label_cbs = []
        c_col, c_row = 0, 4  # c_row must always be (+1) of last row
        for i in range(1, 11):
            self.tumor_label_cbs.append(QtWidgets.QCheckBox("Label {}".format(i)))
            tumor_settings_layout.addWidget(self.tumor_label_cbs[i-1], c_row, c_col)
            c_row = c_row + 1 if c_col == 1 else c_row
            c_col = 0 if c_col == 1 else 1

        tumor_settings_group_box.setLayout(tumor_settings_layout)
        self.grid.addWidget(tumor_settings_group_box, 1, 0, 2, 2)

        for i, cb in enumerate(self.tumor_label_cbs):
            if i < len(self.tumor.labels) and self.tumor.labels[i].actor:
                cb.setChecked(True)
                cb.clicked.connect(self.tumor_label_checked)
            else:
                cb.setDisabled(True)

    def add_views_widget(self):
        axial_view = QtWidgets.QPushButton("Axial")
        coronal_view = QtWidgets.QPushButton("Coronal")
        sagittal_view = QtWidgets.QPushButton("Sagittal")
        views_box = QtWidgets.QGroupBox("Views")
        views_box_layout = QtWidgets.QVBoxLayout()
        views_box_layout.addWidget(axial_view)
        views_box_layout.addWidget(coronal_view)
        views_box_layout.addWidget(sagittal_view)
        views_box.setLayout(views_box_layout)
        self.grid.addWidget(views_box, 3, 0, 2, 2)
        axial_view.clicked.connect(self.set_axial_view)
        coronal_view.clicked.connect(self.set_coronal_view)
        sagittal_view.clicked.connect(self.set_sagittal_view)

    @staticmethod
    def create_new_picker(max_value, min_value, step, picker_value, value_changed_func):
        if isinstance(max_value, int):
            picker = QtWidgets.QSpinBox()
        else:
            picker = QtWidgets.QDoubleSpinBox()

        picker.setMaximum(max_value)
        picker.setMinimum(min_value)
        picker.setSingleStep(step)
        picker.setValue(picker_value)
        picker.valueChanged.connect(value_changed_func)
        return picker

    def add_brain_projection(self):
        projection_cb = QtWidgets.QCheckBox("")
        projection_cb.clicked.connect(self.brain_projection_vc)
        return projection_cb

    def tumor_label_checked(self):
        for i, cb in enumerate(self.tumor_label_cbs):
            if cb.isChecked():
                self.tumor.labels[i].property.SetOpacity(self.tumor_opacity_sp.value())
            elif cb.isEnabled():  # labels without data are disabled
                self.tumor.labels[i].property.SetOpacity(0)
        self.render_window.Render()

    def tumor_single_color_radio_checked(self):
        for label in self.tumor.labels:
            if label.property:
                label.property.SetColor(TUMOR_COLORS[0])
        self.render_window.Render()

    def tumor_multi_color_radio_checked(self):
        for label in self.tumor.labels:
            if label.property:
                label.property.SetColor(label.color)
        self.render_window.Render()

    def brain_projection_vc(self):
        checked = self.brain_projection_cb.isChecked()
        self.brain_image_prop.SetOpacity(checked)
        self.render_window.Render()

    def brain_slicer_vc(self):
        checked = self.brain_slicer_cb.isChecked()
        for prop in self.brain_slicer_props:
            if checked:
                prop.GetProperty().SetOpacity(1.0)
            else:
                prop.GetProperty().SetOpacity(0.0)
        self.render_window.Render()

    def brain_opacity_vc(self):
        opacity = round(self.brain_opacity_sp.value(), 2)
        self.brain.labels[0].property.SetOpacity(opacity)
        self.render_window.Render()

    def brain_threshold_vc(self):
        self.process_changes()
        threshold = self.brain_threshold_sp.value()
        self.brain.labels[0].extractor.SetValue(0, threshold)
        self.render_window.Render()

    def brain_smoothness_vc(self):
        self.process_changes()
        smoothness = self.brain_smoothness_sp.value()
        self.brain.labels[0].smoother.SetNumberOfIterations(smoothness)
        self.render_window.Render()

    def tumor_opacity_vc(self):
        opacity = round(self.tumor_opacity_sp.value(), 2)
        for label in self.tumor.labels:
            if label.property:
                label.property.SetOpacity(opacity)
        self.render_window.Render()

    def tumor_smoothness_vc(self):
        self.process_changes()
        smoothness = self.tumor_smoothness_sp.value()
        for label in self.tumor.labels:
            if label.smoother:
                label.smoother.SetNumberOfIterations(smoothness)
        self.render_window.Render()

    def set_axial_view(self):
        self.renderer.ResetCamera()
        fp = self.renderer.GetActiveCamera().GetFocalPoint()
        p = self.renderer.GetActiveCamera().GetPosition()
        dist = math.sqrt((p[0] - fp[0]) ** 2 + (p[1] - fp[1]) ** 2 + (p[2] - fp[2]) ** 2)
        self.renderer.GetActiveCamera().SetPosition(fp[0], fp[1], fp[2] + dist)
        self.renderer.GetActiveCamera().SetViewUp(0.0, 1.0, 0.0)
        self.renderer.GetActiveCamera().Zoom(1.8)
        self.render_window.Render()

    def set_coronal_view(self):
        self.renderer.ResetCamera()
        fp = self.renderer.GetActiveCamera().GetFocalPoint()
        p = self.renderer.GetActiveCamera().GetPosition()
        dist = math.sqrt((p[0] - fp[0]) ** 2 + (p[1] - fp[1]) ** 2 + (p[2] - fp[2]) ** 2)
        self.renderer.GetActiveCamera().SetPosition(fp[0], fp[2] - dist, fp[1])
        self.renderer.GetActiveCamera().SetViewUp(0.0, 0.5, 0.5)
        self.renderer.GetActiveCamera().Zoom(1.8)
        self.render_window.Render()

    def set_sagittal_view(self):
        self.renderer.ResetCamera()
        fp = self.renderer.GetActiveCamera().GetFocalPoint()
        p = self.renderer.GetActiveCamera().GetPosition()
        dist = math.sqrt((p[0] - fp[0]) ** 2 + (p[1] - fp[1]) ** 2 + (p[2] - fp[2]) ** 2)
        self.renderer.GetActiveCamera().SetPosition(fp[2] + dist, fp[0], fp[1])
        self.renderer.GetActiveCamera().SetViewUp(0.0, 0.0, 1.0)
        self.renderer.GetActiveCamera().Zoom(1.6)
        self.render_window.Render()

    @staticmethod
    def create_new_separator():
        horizontal_line = QtWidgets.QWidget()
        horizontal_line.setFixedHeight(1)
        horizontal_line.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        horizontal_line.setStyleSheet("background-color: #c8c8c8;")
        return horizontal_line

    def process_changes(self):
        for _ in range(10):
            self.app.processEvents()
            time.sleep(0.1)

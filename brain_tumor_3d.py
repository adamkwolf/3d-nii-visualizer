import vtk
import PyQt5.QtWidgets as QtWidgets
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import time
import math

# settings
TUMOR_COLOR = (0.8, 0, 0)  # RGB percentages
BRAIN_COLOR = (1.0, 0.9, 0.9)  # RGB percentages
BRAIN_SMOOTHNESS = 50
TUMOR_SMOOTHNESS = 500
BRAIN_THRESHOLD = [200]
TUMOR_LABELS = [1, 2, 3, 4]
BRAIN_OPACITY = 0.1
TUMOR_OPACITY = 1.0
BRAIN_FILE = "./data/original/HGG/Brats17_2013_2_1/Brats17_2013_2_1_t1ce.nii.gz"
TUMOR_FILE = "./data/original/HGG/Brats17_2013_2_1/Brats17_2013_2_1_seg.nii.gz"


# BG_CSS = "background-color: #f4f4f4;"
# GROUPBOX_CSS = "QGroupBox::title { margin: 2px; background-color: rgba(0,0,0,0.0) }; margin-top: 3px;"


class NiiSettings:
    def __init__(self, file, color, opacity, labels, smoothness):
        self.file = file
        self.color = color
        self.opacity = opacity
        self.labels = labels
        self.missing_labels = set()
        self.smoothness = smoothness


class NiiObject:
    def __init__(self):
        self.actor = None
        self.image_actor = None
        self.reader = None
        self.property = None
        self.extractor = None
        self.smoother = None
        self.locator = None
        self.settings = None


class ErrorObserver:
    def __init__(self):
        self.__ErrorOccurred = False
        self.__ErrorMessage = None
        self.CallDataType = 'string0'

    def __call__(self, obj, event, message):
        self.__ErrorOccurred = True
        self.__ErrorMessage = message

    def ErrorOccurred(self):
        occ = self.__ErrorOccurred
        self.__ErrorOccurred = False
        return occ

    def ErrorMessage(self):
        return self.__ErrorMessage


def redirect_vtk_messages():
    """ Redirect VTK related error messages to a file."""
    import tempfile
    tempfile.template = 'vtk-err'
    f = tempfile.mktemp('.log')
    log = vtk.vtkFileOutputWindow()
    log.SetFlush(1)
    log.SetFileName(f)
    log.SetInstance(log)


def read_volume(file_name):
    reader = vtk.vtkNIFTIImageReader()
    reader.SetFileNameSliceOffset(1)
    reader.SetDataByteOrderToBigEndian()
    reader.SetFileName(file_name)
    return reader


def create_brain_extractor(brain):
    brain_extractor = vtk.vtkFlyingEdges3D()
    brain_extractor.SetInputConnection(brain.reader.GetOutputPort())
    brain_extractor.SetValue(0, brain.settings.labels[0])
    return brain_extractor


def create_tumor_extractor(tumor):
    tumor_extractor = vtk.vtkDiscreteMarchingCubes()
    tumor_extractor.SetInputConnection(tumor.reader.GetOutputPort())

    for i, label in enumerate(tumor.settings.labels):
        if label not in tumor.settings.missing_labels:
            tumor_extractor.SetValue(i, label)

    return tumor_extractor


def create_polygon_reducer(obj):
    reducer = vtk.vtkDecimatePro()
    reducer.AddObserver('ErrorEvent', error_observer)  # used to detect labels that don't exist
    reducer.SetInputConnection(obj.extractor.GetOutputPort())
    reducer.SetTargetReduction(0.5)
    reducer.PreserveTopologyOn()

    return reducer


def create_smoother(reducer, smoothness):
    smoother = vtk.vtkSmoothPolyDataFilter()
    smoother.SetInputConnection(reducer.GetOutputPort())
    smoother.SetNumberOfIterations(smoothness)
    return smoother


def create_normals(smoother):
    brain_normals = vtk.vtkPolyDataNormals()
    brain_normals.SetInputConnection(smoother.GetOutputPort())
    brain_normals.SetFeatureAngle(60.0)  # controls the smoothness of the edges
    return brain_normals


def create_stripper(normals):
    brain_stripper = vtk.vtkStripper()
    brain_stripper.SetInputConnection(normals.GetOutputPort())
    return brain_stripper


def create_locator(extractor):
    brain_locator = vtk.vtkCellLocator()
    brain_locator.SetDataSet(extractor.GetOutput())
    brain_locator.LazyEvaluationOn()
    return brain_locator


def create_mapper(stripper):
    brain_mapper = vtk.vtkPolyDataMapper()
    brain_mapper.SetInputConnection(stripper.GetOutputPort())
    brain_mapper.ScalarVisibilityOff()
    # brain_mapper.SetLookupTable(create_tumor_table())
    brain_mapper.Update()
    return brain_mapper


def create_property(opacity, color):
    prop = vtk.vtkProperty()
    prop.SetColor(color[0], color[1], color[2])  # changes the render color (1.0, 0.9, 0.9)
    prop.SetOpacity(opacity)
    return prop


def create_actor(mapper, prop):
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.SetProperty(prop)
    return actor


def create_tumor_table():
    m_mask_opacity = 1
    brain_lut = vtk.vtkLookupTable()
    brain_lut.SetRange(0, 4)
    brain_lut.SetRampToLinear()
    brain_lut.SetValueRange(0, 1)
    brain_lut.SetHueRange(0, 0)
    brain_lut.SetSaturationRange(0, 0)

    brain_lut.SetNumberOfTableValues(10)
    brain_lut.SetTableRange(0, 9)
    brain_lut.SetTableValue(0, 0, 0, 0, 0)
    brain_lut.SetTableValue(1, 1, 0, 0, m_mask_opacity)  # RED
    brain_lut.SetTableValue(2, 0, 1, 0, m_mask_opacity)  # GREEN
    brain_lut.SetTableValue(3, 1, 1, 0, m_mask_opacity)  # YELLOW
    brain_lut.SetTableValue(4, 0, 0, 1, m_mask_opacity)  # BLUE
    brain_lut.SetTableValue(5, 1, 0, 1, m_mask_opacity)  # MAGENTA
    brain_lut.SetTableValue(6, 0, 1, 1, m_mask_opacity)  # CYAN
    brain_lut.SetTableValue(7, 1, 0.5, 0.5, m_mask_opacity)  # RED_2
    brain_lut.SetTableValue(8, 0.5, 1, 0.5, m_mask_opacity)  # GREEN_2
    brain_lut.SetTableValue(9, 0.5, 0.5, 1, m_mask_opacity)  # BLUE_2
    brain_lut.Build()
    return brain_lut


def create_table():
    table = vtk.vtkLookupTable()
    table.SetRange(0.0, 1675.0)  # +1
    table.SetRampToLinear()
    table.SetValueRange(0, 1)
    table.SetHueRange(0, 0)
    table.SetSaturationRange(0, 0)


def add_surface_rendering(nii_obj):
    reducer = create_polygon_reducer(nii_obj)
    smoother = create_smoother(reducer, nii_obj.settings.smoothness)
    normals = create_normals(smoother)
    stripper = create_stripper(normals)
    actor_locator = create_locator(nii_obj.extractor)
    actor_mapper = create_mapper(stripper)
    actor_property = create_property(nii_obj.settings.opacity, nii_obj.settings.color)
    actor = create_actor(actor_mapper, actor_property)
    nii_obj.actor = actor
    nii_obj.smoother = smoother
    nii_obj.locator = actor_locator
    nii_obj.property = actor_property


def create_label(label):
    label = QtWidgets.QLabel(label)
    # label.setStyleSheet("background-color: rgba(0,0,0,0.0)")
    return label


def create_checkbox(label):
    checkbox = QtWidgets.QCheckBox(label)
    # checkbox.setStyleSheet("background-color: rgba(0,0,0,0.0); padding-top: 3px")
    return checkbox


def create_radio_btn(label):
    radio = QtWidgets.QRadioButton(label)
    # radio.setStyleSheet("background-color: rgba(0,0,0,0.0)")
    return radio


class MainWindow(QtWidgets.QMainWindow, QtWidgets.QApplication):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.renderer, self.frame, self.vtk_widget, self.interactor, self.render_window = self.setup()

        self.brain = NiiObject()
        self.brain.settings = NiiSettings(BRAIN_FILE, BRAIN_COLOR, BRAIN_OPACITY, BRAIN_THRESHOLD, BRAIN_SMOOTHNESS)
        self.brain.reader = read_volume(self.brain.settings.file)
        self.brain.extractor = create_brain_extractor(self.brain)
        add_surface_rendering(self.brain)
        self.renderer.AddViewProp(self.brain.actor)

        self.tumor = NiiObject()
        self.tumor.settings = NiiSettings(TUMOR_FILE, TUMOR_COLOR, TUMOR_OPACITY, TUMOR_LABELS, TUMOR_SMOOTHNESS)
        self.tumor.reader = read_volume(self.tumor.settings.file)
        self.tumor.extractor = create_tumor_extractor(self.tumor)
        add_surface_rendering(self.tumor)
        self.renderer.AddViewProp(self.tumor.actor)

        for label in self.tumor.settings.labels:
            self.tumor.extractor.SetValue(0, label)
            self.render_window.Render()
            if error_observer.ErrorOccurred():
                self.tumor.settings.missing_labels.add(label)
            self.tumor.extractor.SetNumberOfContours(0)

        slice_mapper = vtk.vtkImageResliceMapper()
        slice_mapper.SetInputConnection(self.brain.reader.GetOutputPort())
        slice_mapper.SliceFacesCameraOn()
        slice_mapper.SliceAtFocalPointOn()
        slice_mapper.BorderOff()

        self.brain_image_prop = vtk.vtkImageProperty()
        self.brain_image_prop.SetColorWindow(500)
        self.brain_image_prop.SetColorLevel(500)
        self.brain_image_prop.SetAmbient(1.0)
        self.brain_image_prop.SetDiffuse(1.0)
        self.brain_image_prop.SetOpacity(0.0)
        self.brain_image_prop.SetInterpolationTypeToLinear()

        image_slice = vtk.vtkImageSlice()
        image_slice.SetMapper(slice_mapper)
        image_slice.SetProperty(self.brain_image_prop)

        self.renderer.AddViewProp(image_slice)
        self.grid = QtWidgets.QGridLayout()

        # projection
        self.brain_projection_cb = self.add_brain_projection()

        # brain pickers
        self.brain_threshold_sp = self.add_brain_threshold_picker()
        self.brain_opacity_sp = self.add_brain_opacity_picker()
        self.brain_smoothness_sp = self.add_brain_smoothness_picker()

        # tumor pickers
        self.tumor_label_sp = self.add_tumor_threshold_picker()
        self.tumor_opacity_sp = self.add_tumor_opacity_picker()
        self.tumor_smoothness_sp = self.add_tumor_smoothness_picker()

        #  add pickers to layout
        import os
        object_group_box = QtWidgets.QGroupBox(
            "Brain: " + os.path.basename(BRAIN_FILE) + "          Tumor: " + os.path.basename(TUMOR_FILE))
        # object_group_box.setStyleSheet(GROUPBOX_CSS)
        object_layout = QtWidgets.QVBoxLayout()
        object_layout.addWidget(self.vtk_widget)
        object_group_box.setLayout(object_layout)
        self.grid.addWidget(object_group_box, 0, 2, 5, 5)

        brain_group_box = QtWidgets.QGroupBox("Brain Settings")
        # brain_group_box.setStyleSheet(GROUPBOX_CSS)
        brain_group_layout = QtWidgets.QGridLayout()

        brain_group_layout.addWidget(create_label("Brain Threshold"), 0, 0)
        brain_group_layout.addWidget(create_label("Brain Opacity"), 1, 0)
        brain_group_layout.addWidget(create_label("Brain Smoothness"), 2, 0)
        brain_group_layout.addWidget(create_label("Brain Projection"), 3, 0)
        brain_group_layout.addWidget(self.brain_threshold_sp, 0, 1)
        brain_group_layout.addWidget(self.brain_opacity_sp, 1, 1)
        brain_group_layout.addWidget(self.brain_smoothness_sp, 2, 1)
        brain_group_layout.addWidget(self.brain_projection_cb, 3, 1)
        brain_group_box.setLayout(brain_group_layout)
        self.grid.addWidget(brain_group_box, 0, 0, 1, 2)

        tumor_color_group_box = QtWidgets.QGroupBox("Tumor Settings")
        # tumor_color_group_box.setStyleSheet(GROUPBOX_CSS)
        tumor_color_group_layout = QtWidgets.QGridLayout()
        tumor_color_group_layout.addWidget(create_label("Tumor Opacity"), 0, 0)
        tumor_color_group_layout.addWidget(create_label("Tumor Smoothness"), 1, 0)
        tumor_color_group_layout.addWidget(self.tumor_opacity_sp, 0, 1)
        tumor_color_group_layout.addWidget(self.tumor_smoothness_sp, 1, 1)
        self.tumor_single_color_radio = create_radio_btn("Single Color")
        self.tumor_single_color_radio.setChecked(True)
        self.tumor_multi_color_radio = create_radio_btn("Multi Color")
        tumor_color_group_layout.addWidget(self.tumor_single_color_radio, 2, 0)
        tumor_color_group_layout.addWidget(self.tumor_multi_color_radio, 2, 1)
        tumor_color_group_layout.addWidget(self.create_new_separator(), 3, 0, 1, 2)

        self.tumor_label_cbs = [create_checkbox("Label 1"),
                                create_checkbox("Label 2"),
                                create_checkbox("Label 3"),
                                create_checkbox("Label 4")]

        extractor_idx = 0
        for i, cb in enumerate(self.tumor_label_cbs):
            if i + 1 in self.tumor.settings.missing_labels:
                cb.setDisabled(True)
            else:
                cb.setChecked(True)  # all labels on by default
                self.tumor.extractor.SetValue(extractor_idx, i + 1)
                cb.clicked.connect(self.tumor_label_checked)

        tumor_color_group_layout.addWidget(self.tumor_label_cbs[0], 4, 0)
        tumor_color_group_layout.addWidget(self.tumor_label_cbs[1], 4, 1)
        tumor_color_group_layout.addWidget(self.tumor_label_cbs[2], 5, 0)
        tumor_color_group_layout.addWidget(self.tumor_label_cbs[3], 5, 1)

        tumor_color_group_box.setLayout(tumor_color_group_layout)
        self.grid.addWidget(tumor_color_group_box, 1, 0, 2, 2)

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

        # set view
        self.set_axial_view()

        #  set layout and show
        self.setWindowTitle("NIfTI (nii.gz) 3D Visualizer")
        self.frame.setLayout(self.grid)
        self.setCentralWidget(self.frame)
        self.show()
        self.interactor.Initialize()

    def set_axial_view(self):
        self.renderer.ResetCamera()
        fp = self.renderer.GetActiveCamera().GetFocalPoint()
        p = self.renderer.GetActiveCamera().GetPosition()
        dist = math.sqrt((p[0] - fp[0]) ** 2 + (p[1] - fp[1]) ** 2 + (p[2] - fp[2]) ** 2)
        self.renderer.GetActiveCamera().SetPosition(fp[0], fp[1], fp[2] + dist)
        # self.renderer.GetActiveCamera().SetViewUp(0.0, 1.0, 0.0)
        self.render_window.Render()

    def set_coronal_view(self):
        self.renderer.ResetCamera()
        fp = self.renderer.GetActiveCamera().GetFocalPoint()
        p = self.renderer.GetActiveCamera().GetPosition()
        dist = math.sqrt((p[0] - fp[0]) ** 2 + (p[1] - fp[1]) ** 2 + (p[2] - fp[2]) ** 2)
        self.renderer.GetActiveCamera().SetPosition(fp[0], fp[2] + dist, fp[1])
        self.renderer.GetActiveCamera().SetViewUp(0.0, 0.5, 0.5)
        self.render_window.Render()

    def set_sagittal_view(self):
        self.renderer.ResetCamera()
        fp = self.renderer.GetActiveCamera().GetFocalPoint()
        p = self.renderer.GetActiveCamera().GetPosition()
        dist = math.sqrt((p[0] - fp[0]) ** 2 + (p[1] - fp[1]) ** 2 + (p[2] - fp[2]) ** 2)
        self.renderer.GetActiveCamera().SetPosition(fp[2] + dist, fp[1], fp[0])
        self.renderer.GetActiveCamera().SetViewUp(0.0, 0.5, 0.5)
        self.render_window.Render()

    @staticmethod
    def create_new_separator():
        horizontal_line = QtWidgets.QWidget()
        horizontal_line.setFixedHeight(1)
        horizontal_line.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        # horizontal_line.setStyleSheet("background-color: #c8c8c8;")
        return horizontal_line

    @staticmethod
    def setup():
        renderer = vtk.vtkRenderer()
        frame = QtWidgets.QFrame()
        # frame.setStyleSheet(BG_CSS + "color: #444;")
        vtk_widget = QVTKRenderWindowInteractor()
        interactor = vtk_widget.GetRenderWindow().GetInteractor()
        render_window = vtk_widget.GetRenderWindow()

        frame.setAutoFillBackground(True)
        vtk_widget.GetRenderWindow().AddRenderer(renderer)
        render_window.AddRenderer(renderer)
        interactor.SetRenderWindow(render_window)
        interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        return renderer, frame, vtk_widget, interactor, render_window

    def add_brain_opacity_picker(self):
        brain_opacity_sp = QtWidgets.QDoubleSpinBox()
        brain_opacity_sp.setMaximum(1.0)
        brain_opacity_sp.setMinimum(0.0)
        brain_opacity_sp.setSingleStep(0.1)
        brain_opacity_sp.setValue(BRAIN_OPACITY)
        brain_opacity_sp.valueChanged.connect(self.brain_opacity_value_changed)
        return brain_opacity_sp

    def add_brain_threshold_picker(self):
        brain_threshold_sp = QtWidgets.QSpinBox()
        brain_threshold_sp.setMaximum(1000)
        brain_threshold_sp.setMinimum(0)
        brain_threshold_sp.setSingleStep(5)
        brain_threshold_sp.setValue(BRAIN_THRESHOLD[0])
        brain_threshold_sp.valueChanged.connect(self.brain_threshold_value_changed)
        return brain_threshold_sp

    def add_brain_smoothness_picker(self):
        brain_smoothness_sp = QtWidgets.QSpinBox()
        brain_smoothness_sp.setMaximum(1000)
        brain_smoothness_sp.setMinimum(100)
        brain_smoothness_sp.setSingleStep(100)
        brain_smoothness_sp.setValue(BRAIN_SMOOTHNESS)
        brain_smoothness_sp.valueChanged.connect(self.brain_smoothness_value_changed)
        return brain_smoothness_sp

    def add_tumor_opacity_picker(self):
        tumor_opacity_sp = QtWidgets.QDoubleSpinBox()
        tumor_opacity_sp.setMaximum(1.0)
        tumor_opacity_sp.setMinimum(0.0)
        tumor_opacity_sp.setSingleStep(0.1)
        tumor_opacity_sp.setValue(TUMOR_OPACITY)
        tumor_opacity_sp.valueChanged.connect(self.tumor_opacity_value_changed)
        return tumor_opacity_sp

    def add_tumor_threshold_picker(self):
        tumor_threshold_sp = QtWidgets.QSpinBox()
        tumor_threshold_sp.setMaximum(6)
        tumor_threshold_sp.setMinimum(0)
        tumor_threshold_sp.setSingleStep(1)
        tumor_threshold_sp.setValue(TUMOR_LABELS[0])
        # tumor_threshold_sp.valueChanged.connect(self.tumor_label_value_changed)
        return tumor_threshold_sp

    def add_tumor_smoothness_picker(self):
        tumor_smoothness_sp = QtWidgets.QSpinBox()
        tumor_smoothness_sp.setMaximum(1000)
        tumor_smoothness_sp.setMinimum(100)
        tumor_smoothness_sp.setSingleStep(100)
        tumor_smoothness_sp.setValue(TUMOR_SMOOTHNESS)
        tumor_smoothness_sp.valueChanged.connect(self.tumor_smoothness_value_changed)
        return tumor_smoothness_sp

    def add_brain_projection(self):
        projection_cb = create_checkbox("")  # prob no label needed?
        projection_cb.clicked.connect(self.brain_projection_value_changed)
        return projection_cb

    def tumor_label_checked(self):
        """
        Step 1: Set number of contours to 0. This will remove all current contours.
        Step 2: For each checked checkbox, set its contour on the extractor.
        Step 3: Render the updated contour values.
        """
        self.tumor.extractor.SetNumberOfContours(0)
        contour_idx = 0  # must be sequential starting from 0
        for i, cb in enumerate(self.tumor_label_cbs):
            if cb.isChecked():
                self.tumor.extractor.SetValue(contour_idx, i + 1)
                contour_idx += 1
        self.render_window.Render()

    def brain_projection_value_changed(self):
        checked = self.brain_projection_cb.isChecked()
        self.brain_image_prop.SetOpacity(checked)
        self.brain_projection_cb.repaint()
        self.render_window.Render()

    def brain_opacity_value_changed(self):
        opacity = round(self.brain_opacity_sp.value(), 2)
        self.brain.property.SetOpacity(opacity)
        self.render_window.Render()

    def brain_threshold_value_changed(self):
        self.process_changes()
        threshold = self.brain_threshold_sp.value()
        self.brain.extractor.SetValue(0, threshold)
        self.render_window.Render()

    def brain_smoothness_value_changed(self):
        self.process_changes()
        smoothness = self.brain_smoothness_sp.value()
        self.brain.smoother.SetNumberOfIterations(smoothness)
        self.render_window.Render()

    def tumor_opacity_value_changed(self):
        opacity = round(self.tumor_opacity_sp.value(), 2)
        self.tumor.property.SetOpacity(opacity)
        self.render_window.Render()

    def tumor_smoothness_value_changed(self):
        self.process_changes()
        smoothness = self.tumor_smoothness_sp.value()
        self.tumor.smoother.SetNumberOfIterations(smoothness)
        self.render_window.Render()

    @staticmethod
    def process_changes():
        for _ in range(10):
            app.processEvents()
            time.sleep(0.1)


if __name__ == "__main__":
    error_observer = ErrorObserver()
    redirect_vtk_messages()
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())

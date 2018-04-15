import vtk
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys

# settings
TUMOR_COLOR = (0.8, 0, 0)
BRAIN_COLOR = (1.0, 0.9, 0.9)
BRAIN_SMOOTHNESS = 50
TUMOR_SMOOTHNESS = 500
BRAIN_THRESHOLD = 200  # 200 works well for t1ce
TUMOR_THRESHOLD = 2  # the truth.nii.gz files only have 2 colors, anything higher wont work!
BRAIN_OPACITY = 0.1
TUMOR_OPACITY = 1
BRAIN_FILE = "./data/preprocessed/HGG/Brats17_CBICA_AAB_1/t1ce.nii.gz"
TUMOR_FILE = "./data/preprocessed/HGG/Brats17_CBICA_AAB_1/truth.nii.gz"


class CustomInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self, parent=None):
        self.AddObserver("MiddleButtonPressEvent", self.middleButtonPressEvent)
        self.AddObserver("MiddleButtonReleaseEvent", self.middleButtonReleaseEvent)

    def middleButtonPressEvent(self, obj, event):
        print("Middle Button pressed")
        self.OnMiddleButtonDown()
        return

    def middleButtonReleaseEvent(self, obj, event):
        print("Middle Button released")
        self.OnMiddleButtonUp()
        return


def read_volume(file_name):
    reader = vtk.vtkNIFTIImageReader()
    reader.SetFileNameSliceOffset(1)
    reader.SetDataByteOrderToBigEndian()
    reader.SetFileName(file_name)
    return reader


def create_gpu_volume_ray_cast_mapper(reader):
    volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
    volume_mapper.SetInputConnection(reader.GetOutputPort())
    volume_mapper.CroppingOn()
    # volume_mapper.SetCroppingRegionPlanes((-1000, 1000, -1000, 1000, -1000, 1000))  # remove to hide  crap
    return volume_mapper


def create_volume_color():
    volume_color = vtk.vtkColorTransferFunction()
    volume_color.AddRGBPoint(0, 0.0, 0.0, 0.0)
    volume_color.AddRGBPoint(180, 0.3, 0.1, 0.2)
    volume_color.AddRGBPoint(1000, 1.0, 0.7, 0.6)
    volume_color.AddRGBPoint(2000, 1.0, 1.0, 0.9)
    return volume_color


def create_volume_scalar_opacity():
    volume_scalar_opacity = vtk.vtkPiecewiseFunction()
    volume_scalar_opacity.AddPoint(0, 0.0)
    volume_scalar_opacity.AddPoint(180, 0.0)
    volume_scalar_opacity.AddPoint(1000, 0.2)
    volume_scalar_opacity.AddPoint(2000, 0.8)
    return volume_scalar_opacity


def create_volume_gradient_opacity():
    volume_gradient_opacity = vtk.vtkPiecewiseFunction()
    volume_gradient_opacity.AddPoint(0, 0.0)
    volume_gradient_opacity.AddPoint(90, 0.5)
    volume_gradient_opacity.AddPoint(1000, 1.0)
    return volume_gradient_opacity


def create_volume_property(volume_color, volume_scalar_opacity, volume_gradient_opacity):
    volume_property = vtk.vtkVolumeProperty()
    volume_property.SetColor(0, volume_color)
    volume_property.SetScalarOpacity(0, volume_scalar_opacity)
    volume_property.SetGradientOpacity(0, volume_gradient_opacity)
    volume_property.SetInterpolationTypeToLinear()
    volume_property.ShadeOff(0)
    volume_property.SetAmbient(0, 0.6)
    volume_property.SetDiffuse(0, 0.6)
    volume_property.SetSpecular(0, 0.1)
    return volume_property


def create_volume(volume_mapper, volume_property):
    volume = vtk.vtkVolume()
    volume.SetMapper(volume_mapper)
    volume.SetProperty(volume_property)  # if issues then this is problem
    return volume


def create_brain_extractor(reader, threshold):
    brain_extractor = vtk.vtkFlyingEdges3D()
    brain_extractor.SetInputConnection(reader.GetOutputPort())
    brain_extractor.SetValue(0, threshold)
    return brain_extractor


def create_polygon_reducer(extractor):
    reducer = vtk.vtkDecimatePro()
    reducer.SetInputConnection(extractor.GetOutputPort())
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
    return brain_mapper


def create_property(opacity, color):
    property = vtk.vtkProperty()
    property.SetColor(color[0], color[1], color[2])  # changes the render color (1.0, 0.9, 0.9)
    property.SetOpacity(opacity)
    return property


def create_actor(mapper, prop):
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.SetProperty(prop)
    return actor


def create_table():
    table = vtk.vtkLookupTable()  # TODO
    table.SetRange(0, 2000)
    table.SetRampToLinear()
    table.SetValueRange(0, 1)
    table.SetHueRange(0, 0)
    table.SetSaturationRange(0, 0)
    return table


def create_image_color_map(reader, table):
    map_to_colors = vtk.vtkImageMapToColors()
    map_to_colors.SetInputConnection(reader.GetOutputPort())
    map_to_colors.SetLookupTable(table)
    map_to_colors.Update()
    return map_to_colors


def create_image_actor(map_to_colors):
    image_actor = vtk.vtkImageActor()
    image_actor.GetMapper().SetInputConnection(map_to_colors.GetOutputPort())
    image_actor.SetDisplayExtent((0, 0, 0, 0, 0, 0))
    return image_actor


def transform_and_clip_planes(object, volume, volume_mapper, image_actor):
    transform = vtk.vtkTransform()
    transform.RotateWXYZ(-20, 0.0, -0.7, 0.7)
    volume.SetUserTransform(transform)
    object.SetUserTransform(transform)
    image_actor.SetUserTransform(transform)  # might break something
    object_center = volume.GetCenter()
    volume_clip = vtk.vtkPlane()
    volume_clip.SetNormal(0, 1, 0)
    volume_clip.SetOrigin(object_center[0], object_center[1], object_center[2])
    brain_clip = vtk.vtkPlane()
    brain_clip.SetNormal(1, 0, 0)
    brain_clip.SetOrigin(object_center[0], object_center[1], object_center[2])
    volume_mapper.AddClippingPlane(volume_clip)
    volume_mapper.AddClippingPlane(brain_clip)  # SPLITS BRAIN IN HALF dumb
    return object_center


def add_to_view(nii_renderer, nii_render_window, volume, nii_object, image_actor):
    nii_renderer.AddViewProp(volume)
    nii_renderer.AddViewProp(nii_object)
    nii_renderer.AddViewProp(image_actor)
    nii_render_window.Render()


def create_rotation_cones(nii_renderer):
    cone_source = vtk.vtkConeSource()
    cone_source.CappingOn()
    cone_source.SetHeight(12)
    cone_source.SetRadius(5)
    cone_source.SetResolution(31)
    cone_source.SetCenter(6, 0, 0)
    cone_source.SetDirection(-1, 0, 0)
    cone_mapper = vtk.vtkDataSetMapper()
    cone_mapper.SetInputConnection(cone_source.GetOutputPort())
    red_cone = vtk.vtkActor()
    red_cone.PickableOff()
    red_cone.SetMapper(cone_mapper)
    red_cone.GetProperty().SetColor(1, 0, 0)
    green_cone = vtk.vtkActor()
    green_cone.PickableOff()
    green_cone.SetMapper(cone_mapper)
    green_cone.GetProperty().SetColor(0, 1, 0)
    nii_renderer.AddViewProp(red_cone)
    nii_renderer.AddViewProp(green_cone)
    return red_cone, green_cone


def add_object_picker(locator):
    picker = vtk.vtkVolumePicker()
    picker.SetTolerance(1e-6)
    picker.SetVolumeOpacityIsovalue(1)
    picker.AddLocator(locator)


def add_volume_rendering(reader):
    volume_mapper = create_gpu_volume_ray_cast_mapper(reader)
    volume_color = create_volume_color()
    volume_scalar_opacity = create_volume_scalar_opacity()
    volume_gradient_opacity = create_volume_gradient_opacity()
    volume_property = create_volume_property(volume_color, volume_scalar_opacity, volume_gradient_opacity)
    new_volume = create_volume(volume_mapper, volume_property)
    return new_volume, volume_mapper


def add_surface_rendering(reader, color, opacity, threshold, smoothness):
    actor_extractor = create_brain_extractor(reader, threshold)
    reducer = create_polygon_reducer(actor_extractor)
    smoother = create_smoother(reducer, smoothness)
    normals = create_normals(smoother)
    stripper = create_stripper(normals)
    actor_locator = create_locator(actor_extractor)
    actor_mapper = create_mapper(stripper)
    actor_property = create_property(opacity, color)
    actor = create_actor(actor_mapper, actor_property)
    return actor, actor_locator, actor_property, actor_extractor, smoother


def add_mri_object(nii_renderer, nii_window, nii_file, color=(1, 1, 0.9), opacity=1.0, threshold=200, smoothness=50):
    nii_reader = read_volume(nii_file)
    nii_volume, nii_mapper = add_volume_rendering(nii_reader)
    nii_obj, nii_locator, actor_property, actor_extractor, smoother = add_surface_rendering(nii_reader, color, opacity,
                                                                                            threshold, smoothness)
    nii_color_table = create_table()
    nii_color_mapper = create_image_color_map(nii_reader, nii_color_table)
    nii_image_actor = create_image_actor(nii_color_mapper)
    add_to_view(nii_renderer, nii_window, nii_volume, nii_obj, nii_image_actor)
    add_object_picker(nii_locator)
    return nii_obj, actor_property, actor_extractor, smoother


class MainWindow(QtWidgets.QMainWindow, QtWidgets.QApplication):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setup()
        self.add_actors()

        self.grid = QtWidgets.QGridLayout()
        self.form = QtWidgets.QFormLayout()
        self.form.setAlignment(Qt.Qt.AlignLeft)

        # brain pickers
        self.add_brain_threshold_picker()
        self.add_brain_opacity_picker()
        self.add_brain_smoothness_picker()

        # tumor pickers
        self.add_tumor_threshold_picker()
        self.add_tumor_opacity_picker()
        self.add_tumor_smoothness_picker()

        #  add pickers to layout
        self.grid.addItem(self.form, 0, 0)
        self.grid.addWidget(self.vtkWidget, 0, 1)
        self.grid.setAlignment(self.form, Qt.Qt.AlignLeft)
        self.form.setAlignment(self.brain_threshold_sp, Qt.Qt.AlignLeft)
        self.grid.setColumnStretch(0, 0)
        self.grid.setRowStretch(0, 0)

        #  add to brain form
        self.form.addRow(QtWidgets.QLabel("Brain Threshold:"), self.brain_threshold_sp)
        self.form.addRow(QtWidgets.QLabel("Brain Opacity:"), self.brain_opacity_sp)
        self.form.addRow(QtWidgets.QLabel("Brain Smoothness:"), self.brain_smoothness_sp)

        # add to tumor form
        self.form.addRow(QtWidgets.QLabel("Tumor Threshold:"), self.tumor_threshold_sp)
        self.form.addRow(QtWidgets.QLabel("Tumor Opacity:"), self.tumor_opacity_sp)
        self.form.addRow(QtWidgets.QLabel("Tumor Smoothness:"), self.tumor_smoothness_sp)
        self.form.setLabelAlignment(Qt.Qt.AlignLeft)
        self.form.setFormAlignment(Qt.Qt.AlignRight)
        self.form.setSpacing(5)

        #  set layout and show
        self.setWindowTitle("3D Nifti Visualizer")
        self.frame.setLayout(self.grid)
        self.setCentralWidget(self.frame)
        self.show()
        self.interactor.Initialize()

    def add_actors(self):
        self.brain, self.brain_prop, self.brain_thresh, self.brain_smoother = add_mri_object(self.renderer,
                                                                                             self.render_window,
                                                                                             BRAIN_FILE,
                                                                                             BRAIN_COLOR, BRAIN_OPACITY,
                                                                                             BRAIN_THRESHOLD,
                                                                                             BRAIN_SMOOTHNESS)
        self.tumor, self.tumor_prop, self.tumor_thresh, self.tumor_smoother = add_mri_object(self.renderer,
                                                                                             self.render_window,
                                                                                             TUMOR_FILE,
                                                                                             TUMOR_COLOR, TUMOR_OPACITY,
                                                                                             TUMOR_THRESHOLD,
                                                                                             TUMOR_SMOOTHNESS)

    def setup(self):
        self.renderer = vtk.vtkRenderer()
        self.frame = QtWidgets.QFrame()
        self.frame.setAutoFillBackground(True)
        self.vtkWidget = QVTKRenderWindowInteractor()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtkWidget.GetRenderWindow().GetInteractor()
        self.render_window = self.vtkWidget.GetRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        self.interactor.SetRenderWindow(self.render_window)
        self.interactor.SetInteractorStyle(CustomInteractorStyle())

    # todo: brain pickers
    def add_brain_opacity_picker(self):
        self.brain_opacity_sp = QtWidgets.QDoubleSpinBox()
        self.brain_opacity_sp.setSingleStep(0.1)
        self.brain_opacity_sp.setValue(BRAIN_OPACITY)
        self.brain_opacity_sp.setMaximum(1.0)
        self.brain_opacity_sp.setMinimum(0.0)
        self.brain_opacity_sp.valueChanged.connect(self.brain_opacity_value_changed)

    def add_brain_threshold_picker(self):
        self.brain_threshold_sp = QtWidgets.QSpinBox()
        self.brain_threshold_sp.setValue(BRAIN_THRESHOLD)
        self.brain_threshold_sp.setMinimum(100)
        self.brain_threshold_sp.setMaximum(1000)
        self.brain_threshold_sp.setSingleStep(50)
        self.brain_threshold_sp.valueChanged.connect(self.brain_threshold_value_changed)

    def add_brain_smoothness_picker(self):
        self.brain_smoothness_sp = QtWidgets.QSpinBox()
        self.brain_smoothness_sp.setValue(BRAIN_SMOOTHNESS)
        self.brain_smoothness_sp.setMinimum(100)
        self.brain_smoothness_sp.setMaximum(1000)
        self.brain_smoothness_sp.setSingleStep(100)
        self.brain_smoothness_sp.valueChanged.connect(self.brain_smoothness_value_changed)

    # todo: tumor pickers
    def add_tumor_opacity_picker(self):
        self.tumor_opacity_sp = QtWidgets.QDoubleSpinBox()
        self.tumor_opacity_sp.setSingleStep(0.1)
        self.tumor_opacity_sp.setValue(TUMOR_OPACITY)
        self.tumor_opacity_sp.setMaximum(1.0)
        self.tumor_opacity_sp.setMinimum(0.0)
        self.tumor_opacity_sp.valueChanged.connect(self.tumor_opacity_value_changed)

    def add_tumor_threshold_picker(self):
        self.tumor_threshold_sp = QtWidgets.QSpinBox()
        self.tumor_threshold_sp.setValue(TUMOR_THRESHOLD)
        self.tumor_threshold_sp.setMinimum(1)
        self.tumor_threshold_sp.setMaximum(2)
        self.tumor_threshold_sp.setSingleStep(1)
        self.tumor_threshold_sp.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.tumor_threshold_sp.valueChanged.connect(self.tumor_threshold_value_changed)

    def add_tumor_smoothness_picker(self):
        self.tumor_smoothness_sp = QtWidgets.QSpinBox()
        self.tumor_smoothness_sp.setValue(TUMOR_SMOOTHNESS)
        self.tumor_smoothness_sp.setMinimum(100)
        self.tumor_smoothness_sp.setMaximum(1000)
        self.tumor_smoothness_sp.setSingleStep(100)
        self.tumor_smoothness_sp.valueChanged.connect(self.tumor_smoothness_value_changed)

    # todo: brain settings
    def brain_opacity_value_changed(self):
        opacity = round(self.brain_opacity_sp.value(), 2)
        self.brain_prop.SetOpacity(opacity)
        self.render_window.Render()

    def brain_threshold_value_changed(self):
        threshold = self.brain_threshold_sp.value()
        self.brain_thresh.SetValue(0, threshold)
        self.render_window.Render()

    def brain_smoothness_value_changed(self):
        smoothness = self.brain_smoothness_sp.value()
        self.brain_smoother.SetNumberOfIterations(smoothness)
        self.render_window.Render()

    # todo: tumor settings
    def tumor_opacity_value_changed(self):
        opacity = round(self.tumor_opacity_sp.value(), 2)
        self.tumor_prop.SetOpacity(opacity)
        self.render_window.Render()

    def tumor_threshold_value_changed(self):
        threshold = self.tumor_threshold_sp.value()
        self.tumor_thresh.SetValue(0, threshold)
        self.render_window.Render()

    def tumor_smoothness_value_changed(self):
        smoothness = self.tumor_smoothness_sp.value()
        self.tumor_smoother.SetNumberOfIterations(smoothness)
        self.render_window.Render()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())

import vtk

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


def add_to_view(nii_renderer, volume, nii_object, image_actor):
    nii_renderer.AddViewProp(volume)
    nii_renderer.AddViewProp(nii_object)
    nii_renderer.AddViewProp(image_actor)
    render_window.Render()


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


def create_renderer_window_interactor():
    nii_renderer = vtk.vtkRenderer()
    nii_render_window = vtk.vtkRenderWindow()
    nii_interactor = vtk.vtkRenderWindowInteractor()  # nothing goes here
    return nii_renderer, nii_render_window, nii_interactor


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
    # https://www.vtk.org/doc/nightly/html/classvtkStripper.html
    stripper = create_stripper(normals)
    actor_locator = create_locator(actor_extractor)
    actor_mapper = create_mapper(stripper)
    actor_property = create_property(opacity, color)
    actor = create_actor(actor_mapper, actor_property)
    return actor, actor_locator


def add_mri_object(nii_renderer, nii_file, color=(1, 1, 0.9), opacity=1.0, threshold=200, smoothness=50):
    nii_reader = read_volume(nii_file)
    nii_volume, nii_mapper = add_volume_rendering(nii_reader)
    nii_obj, nii_locator = add_surface_rendering(nii_reader, color, opacity, threshold, smoothness)
    nii_color_table = create_table()
    nii_color_mapper = create_image_color_map(nii_reader, nii_color_table)
    nii_image_actor = create_image_actor(nii_color_mapper)
    # nii_obj_center = transform_and_clip_planes(nii_obj, nii_volume, nii_mapper, nii_image_actor)
    add_to_view(nii_renderer, nii_volume, nii_obj, nii_image_actor)
    add_object_picker(nii_locator)


if __name__ == "__main__":
    renderer, render_window, interactor = create_renderer_window_interactor()
    render_window.AddRenderer(renderer)
    interactor.SetRenderWindow(render_window)
    add_mri_object(renderer, BRAIN_FILE, BRAIN_COLOR, BRAIN_OPACITY, BRAIN_THRESHOLD, BRAIN_SMOOTHNESS)
    add_mri_object(renderer, TUMOR_FILE, TUMOR_COLOR, TUMOR_OPACITY, TUMOR_THRESHOLD, TUMOR_SMOOTHNESS)
    interactor.SetInteractorStyle(CustomInteractorStyle())
    interactor.Start()

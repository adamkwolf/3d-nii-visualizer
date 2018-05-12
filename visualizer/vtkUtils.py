import vtk
from ErrorObserver import *
from NiiObject import *
from config import *

from visualizer.NiiLabel import *

error_observer = ErrorObserver()


def read_volume(file_name):
    reader = vtk.vtkNIFTIImageReader()
    reader.SetFileNameSliceOffset(1)
    reader.SetDataByteOrderToBigEndian()
    reader.SetFileName(file_name)
    reader.Update()
    return reader


def create_brain_extractor(brain):
    brain_extractor = vtk.vtkFlyingEdges3D()
    brain_extractor.SetInputConnection(brain.reader.GetOutputPort())
    brain_extractor.SetValue(0, BRAIN_THRESHOLD)
    return brain_extractor


def create_tumor_extractor(tumor):
    tumor_extractor = vtk.vtkDiscreteMarchingCubes()
    tumor_extractor.SetInputConnection(tumor.reader.GetOutputPort())
    return tumor_extractor


def create_polygon_reducer(extractor):
    reducer = vtk.vtkDecimatePro()
    reducer.AddObserver('ErrorEvent', error_observer)  # used to detect labels that don't exist
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


def create_mapper(stripper):
    brain_mapper = vtk.vtkPolyDataMapper()
    brain_mapper.SetInputConnection(stripper.GetOutputPort())
    brain_mapper.ScalarVisibilityOff()
    # brain_mapper.SetLookupTable(create_tumor_table())
    brain_mapper.Update()
    return brain_mapper


def create_property(opacity, color):
    prop = vtk.vtkProperty()
    prop.SetColor(color[0], color[1], color[2])
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


def add_surface_rendering(nii_object, label_idx, label_value):
    nii_object.labels[label_idx].extractor.SetValue(0, label_value)
    nii_object.labels[label_idx].extractor.Update()

    # if the cell size is 0 then there is no label_idx data
    if nii_object.labels[label_idx].extractor.GetOutput().GetMaxCellSize():
        reducer = create_polygon_reducer(nii_object.labels[label_idx].extractor)
        smoother = create_smoother(reducer, nii_object.labels[label_idx].smoothness)
        normals = create_normals(smoother)
        stripper = create_stripper(normals)
        actor_mapper = create_mapper(stripper)
        actor_property = create_property(nii_object.labels[label_idx].opacity, nii_object.labels[label_idx].color)
        actor = create_actor(actor_mapper, actor_property)
        nii_object.labels[label_idx].actor = actor
        nii_object.labels[label_idx].smoother = smoother
        nii_object.labels[label_idx].property = actor_property


def setup_projection(brain, renderer):
    slice_mapper = vtk.vtkImageResliceMapper()
    slice_mapper.SetInputConnection(brain.reader.GetOutputPort())
    slice_mapper.SliceFacesCameraOn()
    slice_mapper.SliceAtFocalPointOn()
    slice_mapper.BorderOff()
    brain_image_prop = vtk.vtkImageProperty()
    brain_image_prop.SetColorWindow(500)
    brain_image_prop.SetColorLevel(500)
    brain_image_prop.SetAmbient(1.0)
    brain_image_prop.SetDiffuse(1.0)
    brain_image_prop.SetOpacity(0.0)
    brain_image_prop.SetInterpolationTypeToLinear()
    image_slice = vtk.vtkImageSlice()
    image_slice.SetMapper(slice_mapper)
    image_slice.SetProperty(brain_image_prop)
    renderer.AddViewProp(image_slice)
    return brain_image_prop


def setup_brain(renderer, file):
    brain = NiiObject()
    brain.file = file
    brain.reader = read_volume(brain.file)
    brain.labels.append(NiiLabel(BRAIN_COLORS[0], BRAIN_OPACITY, BRAIN_SMOOTHNESS))
    brain.labels[0].extractor = create_brain_extractor(brain)
    add_surface_rendering(brain, 0, 20)
    renderer.AddActor(brain.labels[0].actor)
    return brain


def setup_tumor(renderer, file):
    tumor = NiiObject()
    tumor.file = file
    tumor.reader = read_volume(tumor.file)
    n_labels = int(tumor.reader.GetOutput().GetScalarRange()[1])
    n_labels = n_labels if n_labels <= 10 else 10

    for label_idx in range(0, n_labels):
        tumor.labels.append(NiiLabel(TUMOR_COLORS[label_idx], TUMOR_OPACITY, TUMOR_SMOOTHNESS))
        tumor.labels[label_idx].extractor = create_tumor_extractor(tumor)
        add_surface_rendering(tumor, label_idx, label_idx + 1)
        renderer.AddActor(tumor.labels[label_idx].actor)
    return tumor

import vtk

# from vtk.util.misc import vtkGetDataRoot
# from vtk.util.misc import vtkGetTempDir
import sys
# import os
# VTK_DATA_ROOT = vtkGetDataRoot()
# VTK_TEMP_DIR = vtkGetTempDir()

output = vtk.vtkFileOutputWindow()
output.SetFileName("log.txt")
vtk.vtkOutputWindow().SetInstance(output)

test_files = [
    ['minimal.nii.gz', 'out_minimal.nii.gz']
]

display_file = 'data/flair.nii.gz'


def TestDisplay(file):
    # in_path = os.path.join(str(VTK_DATA_ROOT), "Data", file)
    in_path = "./data/flair.nii.gz"
    reader = vtk.vtkNIFTIImageReader()
    reader.SetFileName(in_path)
    reader.Update()

    # # marching cubes?
    # contour = vtk.vtkMarchingCubes()
    # contour.SetInput(brain_reader.GetOutput())
    # contour.Update()
    #
    # mapper = vtk.vtkImageSliceMapper()
    # mapper.SetInput(contour.GetOutput())
    # mapper.Update()

    print(in_path)
    size = reader.GetOutput().GetDimensions()
    center = reader.GetOutput().GetCenter()
    spacing = reader.GetOutput().GetSpacing()
    center1 = (center[0], center[1], center[2])
    center2 = (center[0], center[1], center[2])
    if size[2] % 2 == 1:
        center1 = (center[0], center1[1], center[2] + 0.5 * spacing[2])
    if size[0] % 2 == 1:
        center1 = (center[0] + 0.5 * spacing[0], center[1], center[2])

    v_range = reader.GetOutput().GetScalarRange()
    map1 = vtk.vtkImageSliceMapper()
    map1.BorderOn()
    map1.SliceAtFocalPointOn()
    map1.SliceFacesCameraOn()
    map1.SetInputConnection(reader.GetOutputPort())
    map2 = vtk.vtkImageSliceMapper()
    map2.BorderOn()
    map2.SliceAtFocalPointOn()
    map2.SliceFacesCameraOn()
    map2.SetInputConnection(reader.GetOutputPort())

    slice1 = vtk.vtkImageSlice()
    slice1.SetMapper(map1)
    slice1.GetProperty().SetColorWindow(v_range[1] - v_range[0])
    slice1.GetProperty().SetColorLevel(0.5 * (v_range[0] + v_range[1]))
    slice2 = vtk.vtkImageSlice()
    slice2.SetMapper(map2)
    slice2.GetProperty().SetColorWindow(v_range[1] - v_range[0])
    slice2.GetProperty().SetColorLevel(0.5 * (v_range[0] + v_range[1]))

    ratio = size[0] * 1.0 / (size[0] + size[2])

    ren1 = vtk.vtkRenderer()
    ren1.SetViewport(0, 0, ratio, 1.0)
    ren2 = vtk.vtkRenderer()
    ren2.SetViewport(ratio, 0.0, 1.0, 1.0)
    ren1.AddViewProp(slice1)
    ren2.AddViewProp(slice2)

    cam1 = ren1.GetActiveCamera()
    cam1.ParallelProjectionOn()
    cam1.SetParallelScale(0.5 * spacing[1] * size[1])
    cam1.SetFocalPoint(center1[0], center1[1], center1[2])
    cam1.SetPosition(center1[0], center1[1], center1[2] - 100.0)

    cam2 = ren2.GetActiveCamera()
    cam2.ParallelProjectionOn()
    cam2.SetParallelScale(0.5 * spacing[1] * size[1])
    cam2.SetFocalPoint(center2[0], center2[1], center2[2])
    cam2.SetPosition(center2[0] + 100.0, center2[1], center2[2])

    if "-I" in sys.argv:
        style = vtk.vtkInteractorStyleImage()
        style.SetInteractionModeToImageSlicing()
        i_ren = vtk.vtkRenderWindowInteractor()
        i_ren.SetInteractorStyle(style)

    ren_win = vtk.vtkRenderWindow()
    ren_win.SetSize((size[0] + size[2]) // 2 * 2, size[1] // 2 * 2)
    ren_win.AddRenderer(ren1)
    ren_win.AddRenderer(ren2)
    ren_win.Render()

    if "-I" in sys.argv:
        ren_win.SetInteractor(i_ren)
        i_ren.Initialize()
        i_ren.Start()

    return ren_win


TestDisplay(display_file)

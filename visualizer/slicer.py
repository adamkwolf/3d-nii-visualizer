import vtk


def main():
    colors = vtk.vtkNamedColors()
    file_name = './sample_data/t1ce.nii.gz'
    colors.SetColor("SkinColor", [255, 125, 64, 255])
    colors.SetColor("BkgColor", [51, 77, 102, 255])
    vtk.vtkRenderer()
    renderer = vtk.vtkRenderer()
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)
    renderer.SetBackground(colors.GetColor3d("BkgColor"))
    render_window.SetSize(640, 480)
    reader = vtk.vtkNIFTIImageReader()
    reader.SetFileName(file_name)
    reader.Update()

    brain_extractor = vtk.vtkMarchingCubes()
    brain_extractor.SetInputConnection(reader.GetOutputPort())
    brain_extractor.SetValue(0, 200)

    brain_stripper = vtk.vtkStripper()
    brain_stripper.SetInputConnection(brain_extractor.GetOutputPort())

    brain_mapper = vtk.vtkPolyDataMapper()
    brain_mapper.SetInputConnection(brain_stripper.GetOutputPort())
    brain_mapper.ScalarVisibilityOff()

    brain = vtk.vtkActor()
    brain.SetMapper(brain_mapper)
    brain.GetProperty().SetDiffuseColor(colors.GetColor3d("Ivory"))
    brain.GetProperty().SetOpacity(0.2)

    bw_lut = vtk.vtkLookupTable()
    bw_lut.SetTableRange(0, 2000)
    bw_lut.SetSaturationRange(0, 0)
    bw_lut.SetHueRange(0, 0)
    bw_lut.SetValueRange(0, 1)
    bw_lut.Build()
    # bw_lut = create_tumor_table()

    view_colors = vtk.vtkImageMapToColors()
    view_colors.SetInputConnection(reader.GetOutputPort())
    view_colors.SetLookupTable(bw_lut)
    view_colors.Update()

    sagittal = vtk.vtkImageActor()
    sagittal.GetMapper().SetInputConnection(view_colors.GetOutputPort())
    sagittal.SetDisplayExtent(128, 128, 0, 255, 0, 255)

    axial = vtk.vtkImageActor()
    axial.GetMapper().SetInputConnection(view_colors.GetOutputPort())
    axial.SetDisplayExtent(0, 255, 0, 255, 75, 255)

    coronal = vtk.vtkImageActor()
    coronal.GetMapper().SetInputConnection(view_colors.GetOutputPort())
    coronal.SetDisplayExtent(0, 255, 128, 128, 0, 255)


    camera = vtk.vtkCamera()
    camera.SetViewUp(0, 0, -1)
    camera.SetPosition(0, -1, 0)
    camera.SetFocalPoint(0, 0, 0)
    camera.ComputeViewPlaneNormal()
    camera.Azimuth(30.0)
    camera.Elevation(30.0)
    renderer.AddActor(sagittal)
    renderer.AddActor(axial)
    renderer.AddActor(coronal)
    renderer.AddActor(brain)
    renderer.SetActiveCamera(camera)
    render_window.Render()
    renderer.ResetCamera()
    camera.Dolly(1.5)
    renderer.ResetCameraClippingRange()
    render_window.Render()
    interactor.Initialize()
    interactor.Start()


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


if __name__ == '__main__':
    main()

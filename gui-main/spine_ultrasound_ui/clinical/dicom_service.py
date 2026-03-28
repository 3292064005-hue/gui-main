from pydicom import Dataset, FileDataset
from pydicom.uid import generate_uid
import datetime
import numpy as np
from loguru import logger
import os

class DICOMService:
    """
    Hospital Integration Node.
    Takes the HDF5/Open3D Reconstructed Voxel Grids and packs them into standard
    DICOM (Digital Imaging and Communications in Medicine) Secondary Capture objects.
    This enables the robotic 3D ultrasound data to be natively read by standard Medical 
    Viewers (like 3D Slicer, Radiant, or Horos) and pushed to Hospital PACS servers.
    """
    def __init__(self, output_dir="data/dicom_export/"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def write_3d_volume_to_dicom(self, patient_name: str, patient_id: str, voxel_data: np.ndarray, spacing=(1.0, 1.0, 1.0)):
        """
        Converts the finalized numpy 3D Volume (from HDF5 reconstruction) into a stack of DICOM files.
        """
        logger.info(f"[DICOM] Packaging 3D Spine Reconstruction for {patient_name}...")
        
        study_uid = generate_uid()
        series_uid = generate_uid()
        timestamp = datetime.datetime.now()

        # Assuming voxel_data is shape (Z, Y, X), unsigned 8/16-bit
        # Standardize typing for DICOM PixelData
        if voxel_data.dtype != np.uint16:
            voxel_data = voxel_data.astype(np.uint16)

        num_slices = voxel_data.shape[0]

        for z in range(num_slices):
            file_meta = Dataset()
            file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1' # Explicit VR Little Endian
            file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7' # Secondary Capture
            file_meta.MediaStorageSOPInstanceUID = generate_uid()
            file_meta.ImplementationClassUID = generate_uid()

            # Create the FileDataset instance
            filename = os.path.join(self.output_dir, f"slice_{z:04d}.dcm")
            ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)

            # Patient & Study Attributes
            ds.PatientName = patient_name.replace(" ", "^")
            ds.PatientID = patient_id
            ds.StudyInstanceUID = study_uid
            ds.SeriesInstanceUID = series_uid
            ds.Modality = "US" # Ultrasound
            ds.SeriesDescription = "Robotic 3D Spine Scan"

            # Image metadata
            ds.Columns = voxel_data.shape[2]
            ds.Rows = voxel_data.shape[1]
            ds.PixelSpacing = [spacing[1], spacing[2]]
            ds.SliceThickness = spacing[0]
            ds.InstanceNumber = z + 1
            
            # Pixel Data (16-bit grayscale)
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.BitsAllocated = 16
            ds.BitsStored = 16
            ds.HighBit = 15
            ds.PixelRepresentation = 0 # Unsigned integer

            # Bind raw bytes
            slice_pixels = voxel_data[z, :, :]
            ds.PixelData = slice_pixels.tobytes()

            ds.is_little_endian = True
            ds.is_implicit_VR = False

            # Save the file
            ds.save_as(filename)

        logger.success(f"[DICOM] Successfully exported {num_slices} slices to {self.output_dir}")

# Example Integration:
# dicom_svc = DICOMService()
# dummy_volume = np.random.randint(0, 255, (100, 256, 256), dtype=np.uint16)
# dicom_svc.write_3d_volume_to_dicom("JOHN DOE", "ROBO-10294", dummy_volume)

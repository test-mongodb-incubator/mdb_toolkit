from abc import ABC, abstractmethod
from botocore.exceptions import NoCredentialsError
from io import BytesIO

import fitz  # PyMuPDF
from PIL import Image


def upload_to_s3(local_file, s3_client, bucket_name, s3_key):
    try:
        s3_client.upload_file(local_file, bucket_name, s3_key)
        print(f"Upload Successful: {local_file} to s3://{bucket_name}/{s3_key}")
        return True
    except FileNotFoundError:
        print(f"The file {local_file} was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


class InputHandler(ABC):
    @abstractmethod
    def preprocess(self, input):
        pass

    def parse_metadata(self, input):
        file_metadata = {}
        bucket_name = input.split("/")[2]
        s3_key = "/".join(input.split("/")[3:])

        file_metadata["s3_full_path"] = input
        file_metadata["s3_bucket_name"] = bucket_name
        file_metadata["s3_key"] = s3_key
        return file_metadata
        

class S3PDFHandler(InputHandler):

    def _pdf_to_screenshots(self, s3_client, bucket_name, s3_key, zoom=3.0):
        # open the PDF from S3 and extract the images
        pdf_data = s3_client.get_object(Bucket=bucket_name, Key=s3_key)["Body"].read()

        pdf_stream = BytesIO(pdf_data)
        pdf = fitz.open(stream=pdf_stream, filetype="pdf")

        images = []

        # Loop through each page, render as pixmap, and convert to PIL Image
        mat = fitz.Matrix(zoom, zoom)
        for n in range(pdf.page_count):
            pix = pdf[n].get_pixmap(matrix=mat)

            # Convert pixmap to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)

        # Close the document
        pdf.close()
        return images
    

    def preprocess(self, s3_client, input):
        file_metadata = super().parse_metadata(input)
        images = self._pdf_to_screenshots(s3_client, file_metadata["s3_bucket_name"], file_metadata["s3_key"])
        
        return images, file_metadata


class S3ImageHandler(InputHandler):

    def _open_s3_image(self, s3_client, bucket_name, s3_key):
        image_data = s3_client.get_object(Bucket=bucket_name, Key=s3_key)["Body"].read()
        img = Image.open(BytesIO(image_data))
        return img
    
    def preprocess(self, s3_client, input):
        file_metadata = super().parse_metadata(input)
        image = self._open_s3_image(s3_client, file_metadata["s3_bucket_name"], file_metadata["s3_key"])
        
        return [image], file_metadata

class ImageHandler(S3ImageHandler):
    def __init__(self, bucket_name):
        super().__init__()
        self.bucket_name = bucket_name

    def preprocess(self, s3_client, input):
        file_name = input.split("/")[-1]
        upload_to_s3(input, s3_client, self.bucket_name, file_name)
        return super().preprocess(s3_client, f"s3://{self.bucket_name}/{file_name}") 

class PDFHandler(S3PDFHandler):
    def __init__(self, bucket_name):
        super().__init__()
        self.bucket_name = bucket_name

    def preprocess(self, s3_client, input):
        file_name = input.split("/")[-1]
        upload_to_s3(input, s3_client, self.bucket_name, file_name)
        return super().preprocess(s3_client, f"s3://{self.bucket_name}/{file_name}") 



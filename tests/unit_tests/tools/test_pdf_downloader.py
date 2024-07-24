# File: tests/tools/test_pdf_downloader.py

import os
import pytest
from autobyteus.tools.pdf_downloader import PDFDownloader

@pytest.mark.asyncio
async def test_execute_success():
    downloader = PDFDownloader()
    url = 'https://watermark.silverchair.com/jamasurgery_engelman_2019_sc_190001.pdf?token=AQECAHi208BE49Ooan9kkhW_Ercy7Dm3ZL_9Cf3qfKAc485ysgAAAykwggMlBgkqhkiG9w0BBwagggMWMIIDEgIBADCCAwsGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMYk9AY6wZthMN4DUvAgEQgIIC3OgazfrWt_ZWddRl0mdzhaWrm3WQimEw9zfDMy8dK8m_01TnhqCbCBXKADJcORSoLVo4ElQ3y40XVj6X7PCLWK4DnfoJx7Rd0UAy4_QHvG3jiXtuyN1wwne4zhLoWy6sAY8sBYxSivqbgmKxCq7-7KvhxjEiYlr5dENOr81xbgG3ISLrjm44cD2pH_rXLoR-qzTBLC-gC3HFKjA4NCXdogJM3evtgFRP8R-rWLdkYI7nO-RKUj4sCllh-frJXWeVSQ8fmkAbCxRmhDuqZyz-5-HGywFDCTzb9C0fk9nWm8zsmBBZzJa1O70oka5uRgxKaXbc-GGcG4CbUIHQl4g2ap-SBZC73WmhAKD4m-6O_7jXWqmSFo-RgRMXrNDval2tNauFjSUFiTgHkmjloXugHWrzEIV3wbh_ZZYyIqcPLbDJqrvezLGudvPt10JEm4vIhFoL4sP8Bd9K8Bx11Odzd-UoX8b50dxuCLSkzDWBVoVu8RvesZNqIZVMTLn5YiTI9j7NqgF_Ls8ZRek1-J-kEiafyNmYG3IRA9j2B3G8Hfi7L0HalZTnTarfL8zFLpuI3l6b9yAXo9so_xnIkO_xxxhtbtjM-8ZN7jA1pM3kio5Dn3GyA2BwP67UcHOaLWrijAq0GRTo-p-ElDll57dlzmI9yPz0XmWWZs98wnnThoGQ1HY9qAdnL2G08KWlchsrYdlXoRRRLProFTp3aQp8DXLnQt0LGlQI2iAIbAhFNhsQW4-G19T0JRwIp9q3tPl1eduQmE1z2vzYl8oQC8Ty4bkI4jL7HmmpAaT3VWfi8H93WVP4jk-XSTzhz2-Rn0tPxKIiYeCmSErCN7QM5oTIf0W7vtH8xllJZc6gYmaU7-B8aDR63-2Y_SgvC9X60wznmNwdMmg7izLfye7KkHIoMStzrmnwne2iqRS5tYtkdx3Lb2IsVwlbK_LDwCPqz9ja4JwsoB_m40VuE6h-YA'  # This is a real, publicly available PDF for testing
    
    result = downloader.execute(url=url)
    
    assert "PDF successfully downloaded and saved to" in result
    
    # Extract the file path from the result
    file_path = result.split("saved to ")[-1].strip()
    
    # Check if the file exists
    assert os.path.exists(file_path)
    
    # Check if the file is not empty
    assert os.path.getsize(file_path) > 0
    
    # Clean up: remove the downloaded file
    # os.remove(file_path)

@pytest.mark.asyncio
async def test_execute_invalid_url():
    downloader = PDFDownloader()
    url = 'https://example.com/nonexistent.pdf'  # This URL should not exist
    
    result = downloader.execute(url=url)
    
    assert "Error downloading PDF" in result

@pytest.mark.asyncio
async def test_execute_non_pdf_url():
    downloader = PDFDownloader()
    url = 'https://example.com'  # This URL exists but is not a PDF
    
    result = downloader.execute(url=url)
    
    assert "The URL does not point to a PDF file" in result

@pytest.mark.asyncio
async def test_execute_missing_url():
    downloader = PDFDownloader()
    
    with pytest.raises(ValueError) as excinfo:
        downloader.execute()
    
    assert "The 'url' keyword argument must be specified" in str(excinfo.value)

@pytest.mark.asyncio
async def test_execute_custom_folder():
    downloader = PDFDownloader()
    url = 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'
    custom_folder = 'test_downloads'
    
    result = downloader.execute(url=url, folder=custom_folder)
    
    assert "PDF successfully downloaded and saved to" in result
    assert custom_folder in result
    
    # Extract the file path from the result
    file_path = result.split("saved to ")[-1].strip()
    
    # Check if the file exists in the custom folder
    assert os.path.exists(file_path)
    assert custom_folder in file_path
    
    # Clean up: remove the downloaded file and the custom folder
    os.remove(file_path)
    os.rmdir(custom_folder)
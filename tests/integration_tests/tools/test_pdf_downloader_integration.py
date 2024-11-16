import os
import pytest
import asyncio
from autobyteus.tools.pdf_downloader import PDFDownloader

@pytest.mark.integration
@pytest.mark.asyncio
async def test_yuntsg_pdf_download():
    """
    Integration test for downloading PDF from yuntsg.com
    This test requires internet connection and the service to be available.
    """
    async with PDFDownloader() as downloader:
        # Updated to use the direct PDF URL obtained after the redirect
        url = 'https://www.sh-mirror.com/pdf/image%20recovery%20matters%20a%20recovery%20e%20source%20ieee%20j%20biomed%20health%20inform%20so%202024.pdf?query=pCKr3TZDM1O5OvWsXPHqmUueffIpDjkTTuodIuUvoTViHOe4-97KerE-3IEWmjbg&iv=rnz9zr3FVspfQaUE&token=6185A11C38EC2B024FFDD3E16FE78144BB72DFB03BE53BBFC2976ADC3A2A1037FB12D9E0E0FCF0A265525AC537852486&view=true&type=.pdf'
        
        try:
            result = await downloader.execute(url=url)
            
            # Verify successful download
            assert "PDF successfully downloaded and saved to" in result
            
            # Extract the file path from the result
            file_path = result.split("saved to ")[-1].strip()
            
            # Verify file exists and has content
            assert os.path.exists(file_path)
            assert os.path.getsize(file_path) > 0
            
            # Optional: Basic PDF header check
            with open(file_path, 'rb') as f:
                header = f.read(4)
                assert header == b'%PDF', "File does not start with PDF header"
                
        except Exception as e:
            pytest.fail(f"Test failed: {str(e)}")
            
        finally:
            # Clean up: remove the downloaded file
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_yuntsg_pdf_download_with_custom_folder():
    """
    Integration test for downloading PDF from yuntsg.com to a custom folder
    """
    custom_folder = 'test_downloads'
    async with PDFDownloader(custom_download_folder=custom_folder) as downloader:
        # Updated to use the direct PDF URL obtained after the redirect
        url = 'https://www.sh-mirror.com/pdf/image%20recovery%20matters%20a%20recovery%20e%20source%20ieee%20j%20biomed%20health%20inform%20so%202024.pdf?query=pCKr3TZDM1O5OvWsXPHqmUueffIpDjkTTuodIuUvoTViHOe4-97KerE-3IEWmjbg&iv=rnz9zr3FVspfQaUE&token=6185A11C38EC2B024FFDD3E16FE78144BB72DFB03BE53BBFC2976ADC3A2A1037FB12D9E0E0FCF0A265525AC537852486&view=true&type=.pdf'
        
        try:
            # Create custom folder
            os.makedirs(custom_folder, exist_ok=True)
            
            result = await downloader.execute(url=url)
            
            # Verify successful download
            assert "PDF successfully downloaded and saved to" in result
            assert custom_folder in result
            
            # Extract the file path from the result
            file_path = result.split("saved to ")[-1].strip()
            
            # Verify file exists in custom folder and has content
            assert os.path.exists(file_path)
            assert os.path.getsize(file_path) > 0
            assert custom_folder in file_path
            
        except Exception as e:
            pytest.fail(f"Test failed: {str(e)}")
            
        finally:
            # Clean up: remove the downloaded file and custom folder
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(custom_folder):
                os.rmdir(custom_folder)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_yuntsg_unreachable():
    """
    Test behavior when yuntsg.com is unreachable
    """
    async with PDFDownloader() as downloader:
        # Use invalid subdomain to simulate unreachable service
        url = 'https://invalid.yuntsg.com/pdfviewer?casesid=99609175&type=pm'
        
        try:
            result = await downloader.execute(url=url)
            assert "Failed to download PDF" in result or "Request error" in result
        except Exception as e:
            pytest.fail(f"Test failed: {str(e)}")
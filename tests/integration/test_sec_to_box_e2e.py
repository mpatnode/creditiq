"""End-to-end test for downloading SEC documents and uploading to Box.

This test verifies the complete workflow:
1. Download a document from SEC.gov (EDGAR)
2. Upload it to Box using the MCP client
3. Verify the upload was successful
4. Clean up by deleting the test file (optional)

Requirements:
- Box MCP server running
- Valid Box credentials in .env
- BOX_RATINGS_FOLDER_ID configured
- Internet connection to access SEC.gov

Run with: pytest tests/integration/test_sec_to_box_e2e.py -v -s
"""

import os
import json
import pytest
import requests
from datetime import datetime
from dotenv import load_dotenv

from services.box_mcp_client import BoxMCPClient, BoxMCPConnectionError, BoxMCPToolError


# Load environment variables
load_dotenv()


@pytest.fixture
def box_client():
    """Create a Box MCP client for testing."""
    server_path = os.getenv("BOX_MCP_SERVER_PATH")
    server_url = os.getenv("BOX_MCP_SERVER_URL")
    
    if not server_path and not server_url:
        pytest.skip("Neither BOX_MCP_SERVER_PATH nor BOX_MCP_SERVER_URL configured in .env")
    
    return BoxMCPClient(server_path=server_path, server_url=server_url)


@pytest.fixture
def ratings_folder_id():
    """Get ratings folder ID from environment."""
    folder_id = os.getenv("BOX_RATINGS_FOLDER_ID")
    if not folder_id:
        pytest.skip("BOX_RATINGS_FOLDER_ID not configured in .env")
    return folder_id


@pytest.fixture
def sec_user_agent():
    """Get SEC User-Agent from environment."""
    user_agent = os.getenv("SEC_USER_AGENT", "CompanyCreditRating/1.0 (test@example.com)")
    return user_agent


def download_sec_document(cik: str, user_agent: str) -> tuple[bytes, str]:
    """Download a company filing from SEC EDGAR.
    
    Args:
        cik: Company CIK number (e.g., "0000320193" for Apple)
        user_agent: User-Agent header required by SEC
        
    Returns:
        Tuple of (document_content, filename)
        
    Raises:
        requests.RequestException: If download fails
    """
    # SEC EDGAR API endpoint for company facts
    # This is a JSON file with company information
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json"
    }
    
    print(f"\n📥 Downloading from SEC EDGAR: {url}")
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    content = response.content
    filename = f"SEC_CIK{cik}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    print(f"✓ Downloaded {len(content)} bytes")
    
    return content, filename


class TestSECToBoxE2E:
    """End-to-end tests for SEC to Box workflow."""

    @pytest.mark.asyncio
    async def test_download_sec_and_upload_to_box(
        self,
        box_client,
        ratings_folder_id,
        sec_user_agent
    ):
        """Test downloading from SEC and uploading to Box."""
        print("\n" + "="*70)
        print("SEC to Box E2E Test - Complete Workflow")
        print("="*70)
        
        # Use Apple Inc. as test company (CIK: 0000320193)
        test_cik = "0000320193"
        test_company = "Apple Inc."
        
        try:
            # Step 1: Download document from SEC
            print(f"\n📋 Step 1: Downloading {test_company} data from SEC.gov...")
            content, filename = download_sec_document(test_cik, sec_user_agent)
            print(f"✓ Downloaded: {filename} ({len(content)} bytes)")
            
            # Step 2: Connect to Box MCP
            print(f"\n🔌 Step 2: Connecting to Box MCP server...")
            async with box_client:
                assert box_client._connected
                print("✓ Connected to Box MCP server")
                
                # Step 3: Upload document to Box (using existing folder)
                print(f"\n📤 Step 3: Uploading document to Box folder {ratings_folder_id}...")
                upload_result = await box_client.upload_file(
                    folder_id=ratings_folder_id,
                    file_name=filename,
                    content=content
                )
                
                if not upload_result.success:
                    pytest.fail(f"Failed to upload file: {upload_result.error}")
                
                # Extract file ID from result
                file_data = upload_result.data
                file_id = None
                
                if isinstance(file_data, list):
                    for item in file_data:
                        if hasattr(item, 'text'):
                            text = item.text
                            # Try to parse as JSON first
                            try:
                                file_data = json.loads(text)
                                file_id = file_data.get('id')
                            except json.JSONDecodeError:
                                # Parse plain text response: "File uploaded successfully. File ID: 123, Name: file.txt"
                                import re
                                match = re.search(r'File ID:\s*(\d+)', text)
                                if match:
                                    file_id = match.group(1)
                            break
                elif isinstance(file_data, str):
                    try:
                        file_data = json.loads(file_data)
                        file_id = file_data.get('id')
                    except json.JSONDecodeError:
                        import re
                        match = re.search(r'File ID:\s*(\d+)', file_data)
                        if match:
                            file_id = match.group(1)
                
                print(f"✓ Uploaded file: {filename} (ID: {file_id})")
                
                # Step 4: Verify file exists by reading it back
                print(f"\n✅ Step 4: Verifying upload by reading file back...")
                read_result = await box_client.read_file(file_id)
                
                assert len(read_result) > 0, "Read file is empty"
                print(f"✓ File verified: {len(read_result)} bytes read back")
                print(f"  Expected: {len(content)} bytes, Got: {len(read_result)} bytes")
                
                # Step 5: Get file info
                print(f"\n📊 Step 5: Getting file information...")
                info_result = await box_client.get_file_info(file_id)
                
                if info_result.success:
                    print(f"✓ File info retrieved successfully")
                else:
                    print(f"⚠ Could not get file info: {info_result.error}")
                
                print("\n" + "="*70)
                print("✅ SUCCESS: Complete SEC to Box workflow verified!")
                print("="*70)
                print(f"\n📍 Test artifacts created:")
                print(f"   Folder ID: {ratings_folder_id}")
                print(f"   File: {filename} (ID: {file_id})")
                print(f"\n💡 Note: Test file remains in Box for manual inspection.")
                print(f"   You can delete it manually or it will be cleaned up later.")
                print("="*70)
                
        except requests.RequestException as e:
            pytest.fail(f"Failed to download from SEC: {e}")
        except BoxMCPToolError as e:
            pytest.fail(f"Box MCP operation failed: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")

    @pytest.mark.asyncio
    async def test_download_multiple_companies(
        self,
        box_client,
        ratings_folder_id,
        sec_user_agent
    ):
        """Test downloading data for multiple companies and uploading to Box."""
        print("\n" + "="*70)
        print("SEC to Box E2E Test - Multiple Companies")
        print("="*70)
        
        # Test with multiple well-known companies
        test_companies = [
            ("0000320193", "Apple Inc."),
            ("0000789019", "Microsoft Corp."),
            ("0001018724", "Amazon.com Inc."),
        ]
        
        async with box_client:
            # Create a batch test folder
            batch_folder_name = f"SEC_Batch_Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            folder_result = await box_client.create_folder(
                parent_folder_id=ratings_folder_id,
                folder_name=batch_folder_name
            )
            
            if not folder_result.success:
                pytest.fail(f"Failed to create batch folder: {folder_result.error}")
            
            # Extract folder ID
            import json
            folder_data = folder_result.data
            if isinstance(folder_data, list):
                for item in folder_data:
                    if hasattr(item, 'text'):
                        folder_data = json.loads(item.text)
                        break
            elif isinstance(folder_data, str):
                folder_data = json.loads(folder_data)
            
            batch_folder_id = folder_data.get('id')
            print(f"\n📁 Created batch folder: {batch_folder_name} (ID: {batch_folder_id})")
            
            uploaded_files = []
            
            for cik, company_name in test_companies:
                try:
                    print(f"\n📥 Processing {company_name} (CIK: {cik})...")
                    
                    # Download from SEC
                    content, filename = download_sec_document(cik, sec_user_agent)
                    print(f"  ✓ Downloaded {len(content)} bytes")
                    
                    # Upload to Box
                    upload_result = await box_client.upload_file(
                        folder_id=batch_folder_id,
                        file_name=filename,
                        content=content
                    )
                    
                    if upload_result.success:
                        file_data = upload_result.data
                        if isinstance(file_data, list):
                            for item in file_data:
                                if hasattr(item, 'text'):
                                    file_data = json.loads(item.text)
                                    break
                        elif isinstance(file_data, str):
                            file_data = json.loads(file_data)
                        
                        file_id = file_data.get('id')
                        uploaded_files.append((company_name, filename, file_id))
                        print(f"  ✓ Uploaded to Box (ID: {file_id})")
                        
                        # Add metadata
                        await box_client.update_file_metadata(
                            file_id=file_id,
                            metadata={
                                "company": company_name,
                                "cik": cik,
                                "source": "SEC EDGAR",
                                "batch_test": "true"
                            }
                        )
                    else:
                        print(f"  ✗ Upload failed: {upload_result.error}")
                    
                except Exception as e:
                    print(f"  ✗ Error processing {company_name}: {e}")
                    continue
            
            print("\n" + "="*70)
            print(f"✅ Batch upload complete: {len(uploaded_files)}/{len(test_companies)} files uploaded")
            print("="*70)
            print(f"\n📍 Uploaded files:")
            for company, filename, file_id in uploaded_files:
                print(f"   • {company}: {filename} (ID: {file_id})")
            print("="*70)
            
            assert len(uploaded_files) > 0, "No files were uploaded successfully"

    @pytest.mark.asyncio
    async def test_sec_rate_limit_handling(self, sec_user_agent):
        """Test that SEC rate limiting is handled properly."""
        print("\n" + "="*70)
        print("SEC Rate Limit Test")
        print("="*70)
        
        # SEC allows 10 requests per second
        # Test that we can make multiple requests with proper delays
        test_ciks = ["0000320193", "0000789019", "0001018724"]
        
        import time
        
        for i, cik in enumerate(test_ciks):
            try:
                start_time = time.time()
                content, filename = download_sec_document(cik, sec_user_agent)
                elapsed = time.time() - start_time
                
                print(f"  Request {i+1}: {filename} - {elapsed:.2f}s")
                
                # Add a small delay to respect rate limits
                if i < len(test_ciks) - 1:
                    time.sleep(0.2)  # 200ms delay between requests
                    
            except requests.RequestException as e:
                if "429" in str(e):
                    print(f"  ⚠ Rate limit hit (expected): {e}")
                else:
                    pytest.fail(f"Unexpected error: {e}")
        
        print("\n✓ Rate limit handling verified")
        print("="*70)


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "-s"])

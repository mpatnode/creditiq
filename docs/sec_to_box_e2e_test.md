# SEC to Box E2E Test Documentation

## Overview

The SEC to Box E2E test (`tests/integration/test_sec_to_box_e2e.py`) verifies the complete workflow of downloading company financial data from the SEC EDGAR database and uploading it to Box using the MCP client.

## What It Tests

### 1. Single Company Workflow (`test_download_sec_and_upload_to_box`)

This test performs a complete end-to-end workflow:

1. **Download from SEC EDGAR**
   - Downloads company submission data (JSON format)
   - Uses Apple Inc. (CIK: 0000320193) as test company
   - Respects SEC rate limits and User-Agent requirements

2. **Connect to Box MCP**
   - Establishes connection to Box MCP server
   - Verifies connection is successful

3. **Create Test Folder**
   - Creates a timestamped test folder in Box
   - Folder name format: `SEC_Test_YYYYMMDD_HHMMSS`

4. **Upload Document**
   - Uploads the downloaded SEC document to Box
   - File name format: `SEC_CIK{cik}_YYYYMMDD_HHMMSS.json`

5. **Add Metadata**
   - Tags the file with metadata:
     - Company name
     - CIK number
     - Source (SEC EDGAR)
     - Upload timestamp
     - Test flag

6. **Verify Upload**
   - Reads the file back from Box
   - Verifies file size matches original
   - Confirms data integrity

7. **Get File Info**
   - Retrieves file metadata from Box
   - Displays file information

### 2. Multiple Companies Workflow (`test_download_multiple_companies`)

Tests batch processing of multiple companies:

- Downloads data for Apple, Microsoft, and Amazon
- Creates a single batch folder
- Uploads all files to the same folder
- Adds metadata to each file
- Reports success/failure for each company

### 3. Rate Limit Handling (`test_sec_rate_limit_handling`)

Verifies proper handling of SEC rate limits:

- Makes multiple requests to SEC EDGAR
- Adds delays between requests (200ms)
- Handles 429 (Too Many Requests) responses gracefully

## Test Companies

The test uses well-known public companies with stable CIK numbers:

| Company | CIK | Ticker |
|---------|-----|--------|
| Apple Inc. | 0000320193 | AAPL |
| Microsoft Corp. | 0000789019 | MSFT |
| Amazon.com Inc. | 0001018724 | AMZN |

## Requirements

### Environment Variables

```bash
# Box MCP Server (choose one)
BOX_MCP_SERVER_PATH=/path/to/box-mcp-server
BOX_MCP_SERVER_URL=http://localhost:8005/sse

# Box Configuration
BOX_RATINGS_FOLDER_ID=your-ratings-folder-id

# SEC Configuration
SEC_USER_AGENT=CompanyCreditRating/1.0 (your-email@example.com)
```

### Running Services

- Box MCP server must be running
- Internet connection required for SEC.gov access

## Running the Test

### Quick Run (Recommended)

```bash
./scripts/test_sec_to_box.sh
```

This script:
- Checks environment configuration
- Verifies Box MCP server is accessible
- Runs the main E2E test
- Provides clear success/failure output

### Manual Run

```bash
# Single company test
pytest tests/integration/test_sec_to_box_e2e.py::TestSECToBoxE2E::test_download_sec_and_upload_to_box -v -s

# Multiple companies test
pytest tests/integration/test_sec_to_box_e2e.py::TestSECToBoxE2E::test_download_multiple_companies -v -s

# Rate limit test
pytest tests/integration/test_sec_to_box_e2e.py::TestSECToBoxE2E::test_sec_rate_limit_handling -v -s

# All tests
pytest tests/integration/test_sec_to_box_e2e.py -v -s
```

## Expected Output

```
======================================================================
SEC to Box E2E Test - Complete Workflow
======================================================================

📋 Step 1: Downloading Apple Inc. data from SEC.gov...
📥 Downloading from SEC EDGAR: https://data.sec.gov/submissions/CIK0000320193.json
✓ Downloaded 45678 bytes
✓ Downloaded: SEC_CIK0000320193_20240115_143022.json (45678 bytes)

🔌 Step 2: Connecting to Box MCP server...
✓ Connected to Box MCP server

📁 Step 3: Creating test folder in Box...
✓ Created test folder: SEC_Test_20240115_143022 (ID: 123456789)

📤 Step 4: Uploading document to Box...
✓ Uploaded file: SEC_CIK0000320193_20240115_143022.json (ID: 987654321)

🏷️  Step 5: Adding metadata to file...
✓ Metadata added successfully

✅ Step 6: Verifying upload by reading file back...
✓ File verified: 45678 bytes read back

📊 Step 7: Getting file information...
✓ File info retrieved

======================================================================
✅ SUCCESS: Complete SEC to Box workflow verified!
======================================================================

📍 Test artifacts created:
   Folder: SEC_Test_20240115_143022 (ID: 123456789)
   File: SEC_CIK0000320193_20240115_143022.json (ID: 987654321)

💡 Note: Test folder and file remain in Box for manual inspection.
   You can delete them manually or they will be cleaned up later.
======================================================================
```

## Test Artifacts

The test creates real artifacts in Box:

### Folder Structure

```
/Credit Ratings/
  /SEC_Test_20240115_143022/
    SEC_CIK0000320193_20240115_143022.json
```

Or for batch tests:

```
/Credit Ratings/
  /SEC_Batch_Test_20240115_143022/
    SEC_CIK0000320193_20240115_143022.json
    SEC_CIK0000789019_20240115_143022.json
    SEC_CIK0001018724_20240115_143022.json
```

### File Metadata

Each uploaded file includes metadata:

```json
{
  "company": "Apple Inc.",
  "cik": "0000320193",
  "source": "SEC EDGAR",
  "upload_date": "2024-01-15T14:30:22.123456",
  "test": "true"
}
```

### Cleanup

Test artifacts are **NOT** automatically deleted. Options:

1. **Manual Cleanup**: Delete test folders from Box web interface
2. **Keep for Inspection**: Useful for verifying the workflow
3. **Automated Cleanup**: Implement a cleanup script (future enhancement)

## SEC EDGAR API

### Endpoint Used

```
https://data.sec.gov/submissions/CIK{cik}.json
```

This endpoint returns company submission information including:
- Company details (name, CIK, ticker)
- Recent filings (10-K, 10-Q, 8-K, etc.)
- Filing dates and accession numbers

### Rate Limits

- **Limit**: 10 requests per second
- **User-Agent**: Required with contact information
- **Handling**: Tests include 200ms delays between requests

### Example Response

```json
{
  "cik": "320193",
  "entityType": "operating",
  "sic": "3571",
  "sicDescription": "Electronic Computers",
  "name": "Apple Inc.",
  "tickers": ["AAPL"],
  "exchanges": ["Nasdaq"],
  "filings": {
    "recent": {
      "accessionNumber": [...],
      "filingDate": [...],
      "form": [...]
    }
  }
}
```

## Troubleshooting

### "Failed to download from SEC"

**Causes:**
- No internet connection
- SEC rate limit exceeded
- Invalid CIK number
- Missing or invalid User-Agent

**Solutions:**
- Check internet connectivity
- Verify SEC_USER_AGENT includes valid email
- Add delays between requests
- Use valid CIK numbers

### "Failed to connect to Box MCP server"

**Causes:**
- MCP server not running
- Wrong server path/URL
- Network issues
- Invalid Box credentials

**Solutions:**
- Start Box MCP server
- Verify BOX_MCP_SERVER_PATH or BOX_MCP_SERVER_URL
- Check Box credentials in MCP config
- Test MCP server independently

### "Failed to create test folder"

**Causes:**
- Invalid BOX_RATINGS_FOLDER_ID
- Insufficient Box permissions
- MCP server authentication issues

**Solutions:**
- Verify folder ID in Box web interface
- Check Box app permissions
- Ensure JWT authentication is configured
- Test with Box MCP directly

### "File size mismatch"

**Causes:**
- Network interruption during upload
- Box API issues
- MCP encoding problems

**Solutions:**
- Retry the test
- Check Box service status
- Verify MCP server logs
- Test with smaller files

## Integration with Rating Storage

This E2E test validates the core functionality used by the Rating Storage component:

1. **Document Upload**: Same mechanism used to upload rating reports
2. **Folder Management**: Same pattern for creating company folders
3. **Metadata Tagging**: Same approach for adding rating metadata
4. **File Verification**: Same validation used for rating packages

The test ensures that the Box integration works correctly before using it in production rating workflows.

## Future Enhancements

Potential improvements to the test:

1. **Automatic Cleanup**: Delete test artifacts after verification
2. **More Companies**: Test with additional companies
3. **Different File Types**: Test with PDFs, Excel files, etc.
4. **Error Injection**: Test failure scenarios
5. **Performance Testing**: Measure upload/download speeds
6. **Concurrent Uploads**: Test parallel operations
7. **Large Files**: Test with 10-K filings (larger documents)

## Related Documentation

- [Integration Tests README](../tests/integration/README.md)
- [Rating Storage Usage](./rating_storage_usage.md)
- [Box MCP Documentation](https://developer.box.com/guides/box-mcp/self-hosted/)
- [SEC EDGAR API](https://www.sec.gov/edgar/sec-api-documentation)

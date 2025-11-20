# Integration Tests

This directory contains end-to-end integration tests that verify the complete workflow of the Credit Rating System with real external services.

## Test Files

### `test_box_mcp_e2e.py`
Tests Box MCP integration:
- Connection to Box MCP server
- Folder access verification
- Search functionality
- Complete workflow validation

### `test_sec_to_box_e2e.py`
Tests SEC.gov to Box workflow:
- Downloading company data from SEC EDGAR
- Uploading documents to Box
- Adding metadata to files
- Batch processing multiple companies
- Rate limit handling

## Prerequisites

### 1. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Box MCP Server (choose one)
BOX_MCP_SERVER_PATH=/path/to/box-mcp-server
# OR
BOX_MCP_SERVER_URL=http://localhost:8005/sse

# Box Folder IDs
BOX_METHODOLOGY_FOLDER_ID=your-methodology-folder-id
BOX_RATINGS_FOLDER_ID=your-ratings-folder-id

# SEC Configuration
SEC_USER_AGENT=CompanyCreditRating/1.0 (your-email@example.com)
```

### 2. Box MCP Server

The Box MCP server must be running. Start it with:

```bash
# If using stdio
npx -y @modelcontextprotocol/server-box config.json

# If using SSE (HTTP)
npx -y @modelcontextprotocol/server-box --sse config.json
```

### 3. Internet Connection

Tests require internet access to:
- Connect to Box API (via MCP server)
- Download data from SEC.gov

## Running Tests

### Run All Integration Tests

```bash
pytest tests/integration/ -v -s
```

### Run Specific Test File

```bash
# Box MCP tests only
pytest tests/integration/test_box_mcp_e2e.py -v -s

# SEC to Box tests only
pytest tests/integration/test_sec_to_box_e2e.py -v -s
```

### Run Specific Test

```bash
# Test SEC download and upload
pytest tests/integration/test_sec_to_box_e2e.py::TestSECToBoxE2E::test_download_sec_and_upload_to_box -v -s

# Test multiple companies
pytest tests/integration/test_sec_to_box_e2e.py::TestSECToBoxE2E::test_download_multiple_companies -v -s
```

### Skip Integration Tests

To run only unit tests (skip integration):

```bash
pytest tests/unit/ -v
```

## Test Output

Integration tests provide detailed output showing:
- ✓ Successful operations
- ✗ Failed operations
- ⚠ Warnings (non-critical issues)
- 📥 Downloads
- 📤 Uploads
- 📁 Folder operations
- 🏷️ Metadata operations

Example output:
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

======================================================================
✅ SUCCESS: Complete SEC to Box workflow verified!
======================================================================
```

## Test Artifacts

Integration tests create real artifacts in Box:
- Test folders (e.g., `SEC_Test_20240115_143022`)
- Uploaded files with metadata
- These remain in Box for manual inspection

**Note:** Test artifacts are NOT automatically cleaned up. You can:
1. Delete them manually from Box
2. Keep them for verification
3. Implement cleanup in a separate script

## Troubleshooting

### "BOX_MCP_SERVER_PATH not configured"
- Ensure `.env` file exists with Box MCP configuration
- Verify the MCP server path or URL is correct

### "Failed to connect to Box MCP server"
- Check that the Box MCP server is running
- Verify network connectivity
- Check Box credentials in MCP server config

### "SEC download failed"
- Verify internet connection
- Check SEC_USER_AGENT is configured with valid email
- SEC may rate limit requests (10 per second)

### "Failed to create test folder"
- Verify BOX_RATINGS_FOLDER_ID is correct
- Check Box permissions for the folder
- Ensure MCP server has write access

## Rate Limits

### SEC EDGAR
- 10 requests per second
- Tests include delays to respect limits
- Use a valid User-Agent with contact info

### Box API
- Rate limits handled by Box MCP server
- Retry logic built into BoxMCPClient
- Exponential backoff on failures

## Security Notes

- Never commit `.env` file with real credentials
- SEC User-Agent should include real contact email
- Box credentials are managed by MCP server
- Test files may contain real company data

## CI/CD Integration

To run integration tests in CI/CD:

```yaml
# Example GitHub Actions
- name: Run Integration Tests
  env:
    BOX_MCP_SERVER_URL: ${{ secrets.BOX_MCP_SERVER_URL }}
    BOX_RATINGS_FOLDER_ID: ${{ secrets.BOX_RATINGS_FOLDER_ID }}
    SEC_USER_AGENT: ${{ secrets.SEC_USER_AGENT }}
  run: |
    pytest tests/integration/ -v -s
```

**Note:** Ensure Box MCP server is accessible from CI environment.

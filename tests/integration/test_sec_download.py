"""Test SEC EDGAR download functionality only (no Box required)."""

import os
import pytest
import requests
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()


def download_sec_document(cik: str, user_agent: str) -> tuple[bytes, str]:
    """Download a company filing from SEC EDGAR."""
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


class TestSECDownload:
    """Test SEC EDGAR download functionality."""

    def test_download_apple_data(self):
        """Test downloading Apple Inc. data from SEC."""
        print("\n" + "="*70)
        print("SEC Download Test - Apple Inc.")
        print("="*70)
        
        user_agent = os.getenv("SEC_USER_AGENT", "CompanyCreditRating/1.0 (test@example.com)")
        cik = "0000320193"
        company = "Apple Inc."
        
        print(f"\n📋 Downloading {company} (CIK: {cik}) data from SEC.gov...")
        
        content, filename = download_sec_document(cik, user_agent)
        
        print(f"✓ Downloaded: {filename}")
        print(f"✓ Size: {len(content):,} bytes")
        
        # Verify it's valid JSON
        import json
        data = json.loads(content)
        
        print(f"\n📊 Company Information:")
        print(f"   Name: {data.get('name', 'N/A')}")
        print(f"   CIK: {data.get('cik', 'N/A')}")
        print(f"   Tickers: {', '.join(data.get('tickers', []))}")
        print(f"   Exchanges: {', '.join(data.get('exchanges', []))}")
        print(f"   SIC: {data.get('sic', 'N/A')} - {data.get('sicDescription', 'N/A')}")
        
        # Check for recent filings
        if 'filings' in data and 'recent' in data['filings']:
            recent = data['filings']['recent']
            num_filings = len(recent.get('accessionNumber', []))
            print(f"   Recent Filings: {num_filings}")
            
            if num_filings > 0:
                print(f"\n📄 Most Recent Filings:")
                for i in range(min(5, num_filings)):
                    form = recent['form'][i]
                    date = recent['filingDate'][i]
                    print(f"      {i+1}. {form} - {date}")
        
        print("\n" + "="*70)
        print("✅ SUCCESS: SEC download and parsing verified!")
        print("="*70)
        
        # Assertions
        assert len(content) > 0, "Downloaded content is empty"
        assert data.get('name') == company, f"Company name mismatch"
        assert 'AAPL' in data.get('tickers', []), "AAPL ticker not found"

    def test_download_multiple_companies(self):
        """Test downloading data for multiple companies."""
        print("\n" + "="*70)
        print("SEC Download Test - Multiple Companies")
        print("="*70)
        
        user_agent = os.getenv("SEC_USER_AGENT", "CompanyCreditRating/1.0 (test@example.com)")
        
        companies = [
            ("0000320193", "Apple Inc.", "AAPL"),
            ("0000789019", "Microsoft Corp.", "MSFT"),
            ("0001018724", "Amazon.com Inc.", "AMZN"),
        ]
        
        results = []
        
        for cik, expected_name, expected_ticker in companies:
            try:
                print(f"\n📥 Downloading {expected_name} (CIK: {cik})...")
                
                content, filename = download_sec_document(cik, user_agent)
                
                import json
                data = json.loads(content)
                
                name = data.get('name', 'Unknown')
                tickers = data.get('tickers', [])
                
                print(f"   ✓ {name} - {', '.join(tickers)} ({len(content):,} bytes)")
                
                results.append({
                    'cik': cik,
                    'name': name,
                    'tickers': tickers,
                    'size': len(content),
                    'success': True
                })
                
                # Small delay to respect rate limits
                import time
                time.sleep(0.2)
                
            except Exception as e:
                print(f"   ✗ Failed: {e}")
                results.append({
                    'cik': cik,
                    'success': False,
                    'error': str(e)
                })
        
        print("\n" + "="*70)
        print(f"✅ Downloaded {sum(1 for r in results if r['success'])}/{len(companies)} companies")
        print("="*70)
        
        # Verify at least one succeeded
        assert any(r['success'] for r in results), "All downloads failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

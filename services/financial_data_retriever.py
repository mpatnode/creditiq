"""Financial Data Retriever component for fetching company financial data from SEC EDGAR."""
import os
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

from app.exceptions import (
    CompanyNotFoundError,
    DataProviderUnavailableError,
    DataProviderRateLimitError,
    IncompleteDataError,
    StaleDataError,
    NetworkError,
    RetryExhaustedError,
)


logger = logging.getLogger(__name__)


@dataclass
class Company:
    """Company information."""
    id: str  # CIK number
    name: str
    ticker: str
    exchange: str
    sector: str
    industry: str


@dataclass
class FinancialStatements:
    """Financial statements data."""
    balance_sheet: Dict[str, Any]
    income_statement: Dict[str, Any]
    cash_flow_statement: Dict[str, Any]


@dataclass
class FinancialData:
    """Complete financial data for a company."""
    company_id: str
    company_name: str
    ticker: str
    financial_statements: FinancialStatements
    market_data: Dict[str, Any]
    data_date: datetime


@dataclass
class DataQualityReport:
    """Report on data quality validation."""
    is_complete: bool
    is_fresh: bool
    missing_fields: List[str]
    data_age_days: int
    warnings: List[str]


class FinancialDataRetriever:
    """Retrieve and normalize financial data from SEC EDGAR."""
    
    # SEC requires a User-Agent header with contact information
    USER_AGENT = "CompanyCreditRating/1.0 (contact@example.com)"
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        data_age_threshold_months: int = 12
    ):
        """Initialize the financial data retriever.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            data_age_threshold_months: Maximum age of data in months
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.data_age_threshold_months = data_age_threshold_months
        self.sec_api_base = "https://data.sec.gov"
        self.sec_files_base = "https://www.sec.gov"
        self.headers = {
            "User-Agent": self.USER_AGENT,
            "Accept-Encoding": "gzip, deflate"
        }
        
        # Cache for company tickers mapping
        self._company_tickers_cache: Optional[Dict[str, Any]] = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _make_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request with retry logic.
        
        Args:
            url: Full URL for the request
            params: Optional query parameters
            
        Returns:
            JSON response from the API
            
        Raises:
            DataProviderUnavailableError: If service is unavailable
            DataProviderRateLimitError: If rate limit is exceeded
            NetworkError: If network error occurs
            RetryExhaustedError: If all retries are exhausted
        """
        try:
            logger.debug(f"Making request to {url}")
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            
            # Check for rate limiting
            if response.status_code == 429:
                logger.warning(f"Rate limit exceeded for {url}")
                raise DataProviderRateLimitError(
                    message=f"Rate limit exceeded: {response.text}",
                    user_message="Too many requests. Please wait a moment and try again.",
                    details={"url": url, "status_code": 429}
                )
            
            # Check for service unavailable
            if response.status_code in (502, 503, 504):
                logger.warning(f"Service unavailable: {response.status_code}")
                raise DataProviderUnavailableError(
                    message=f"Service unavailable: {response.status_code}",
                    user_message="Financial data service is temporarily unavailable. Please try again later.",
                    details={"url": url, "status_code": response.status_code}
                )
            
            response.raise_for_status()
            logger.debug(f"Request to {url} succeeded")
            return response.json()
        
        except (DataProviderRateLimitError, DataProviderUnavailableError):
            raise
        except requests.Timeout as e:
            logger.error(f"Request timeout for {url}: {e}")
            raise NetworkError(
                message=f"Request timeout: {e}",
                user_message="Request timed out. Please try again.",
                details={"url": url}
            ) from e
        except requests.ConnectionError as e:
            logger.error(f"Connection error for {url}: {e}")
            raise NetworkError(
                message=f"Connection error: {e}",
                user_message="Network connection error. Please check your connection and try again.",
                details={"url": url}
            ) from e
        except RetryError as e:
            logger.error(f"Request failed after all retries for {url}: {e}", exc_info=True)
            raise RetryExhaustedError(
                message=f"Request failed after multiple attempts: {e}",
                user_message="Service is temporarily unavailable after multiple attempts. Please try again later.",
                details={"url": url, "max_attempts": 3}
            ) from e
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}", exc_info=True)
            raise DataProviderUnavailableError(
                message=f"Request failed: {e}",
                user_message="Financial data service is temporarily unavailable. Please try again later.",
                details={"url": url}
            ) from e

    
    def _load_company_tickers(self) -> Dict[str, Any]:
        """Load company tickers mapping from SEC.
        
        Returns:
            Dictionary mapping tickers to company information
        """
        if self._company_tickers_cache is not None:
            return self._company_tickers_cache
        
        url = f"{self.sec_files_base}/files/company_tickers.json"
        data = self._make_request(url)
        
        # Transform the data structure for easier lookup
        tickers_map = {}
        for key, company_info in data.items():
            ticker = company_info.get('ticker', '').upper()
            if ticker:
                tickers_map[ticker] = {
                    'cik': str(company_info.get('cik_str', '')).zfill(10),
                    'name': company_info.get('title', ''),
                    'ticker': ticker
                }
        
        self._company_tickers_cache = tickers_map
        return tickers_map
    
    def search_companies(self, query: str) -> List[Company]:
        """Search for companies by name or ticker.
        
        Args:
            query: Company name or ticker symbol
            
        Returns:
            List of matching companies
            
        Raises:
            CompanyNotFoundError: If no companies match the query
        """
        try:
            logger.info(f"Searching for companies matching: {query}")
            tickers_map = self._load_company_tickers()
            query_upper = query.upper().strip()
            matches = []
            
            for ticker, info in tickers_map.items():
                # Match by ticker or company name
                if (query_upper in ticker or 
                    query_upper in info['name'].upper()):
                    matches.append(Company(
                        id=info['cik'],
                        name=info['name'],
                        ticker=ticker,
                        exchange="",  # SEC data doesn't include exchange
                        sector="",    # Will be populated from company facts if needed
                        industry=""   # Will be populated from company facts if needed
                    ))
            
            if not matches:
                logger.warning(f"No companies found matching: {query}")
                raise CompanyNotFoundError(
                    message=f"No companies found matching '{query}'",
                    user_message="Company not found. Please check the company name or ticker symbol.",
                    details={"query": query}
                )
            
            logger.info(f"Found {len(matches)} companies matching: {query}")
            return matches
        
        except CompanyNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error searching for companies: {e}", exc_info=True)
            raise DataProviderUnavailableError(
                message=f"Company search failed: {e}",
                user_message="Unable to search for companies. Please try again later.",
                details={"query": query}
            ) from e
    
    def _get_company_facts(self, cik: str) -> Dict[str, Any]:
        """Get company facts from SEC EDGAR.
        
        Args:
            cik: Company CIK number (10 digits, zero-padded)
            
        Returns:
            Company facts data including financial statements
        """
        cik_padded = cik.zfill(10)
        url = f"{self.sec_api_base}/api/xbrl/companyfacts/CIK{cik_padded}.json"
        return self._make_request(url)
    
    def _extract_financial_statements(self, facts: Dict[str, Any]) -> FinancialStatements:
        """Extract and normalize financial statements from company facts.
        
        Args:
            facts: Raw company facts data from SEC
            
        Returns:
            Normalized financial statements
        """
        us_gaap = facts.get('facts', {}).get('us-gaap', {})
        
        # Extract balance sheet items
        balance_sheet = {
            'Assets': self._get_latest_value(us_gaap.get('Assets', {})),
            'AssetsCurrent': self._get_latest_value(us_gaap.get('AssetsCurrent', {})),
            'Liabilities': self._get_latest_value(us_gaap.get('Liabilities', {})),
            'LiabilitiesCurrent': self._get_latest_value(us_gaap.get('LiabilitiesCurrent', {})),
            'StockholdersEquity': self._get_latest_value(us_gaap.get('StockholdersEquity', {})),
            'LongTermDebt': self._get_latest_value(us_gaap.get('LongTermDebt', {})),
            'CashAndCashEquivalents': self._get_latest_value(us_gaap.get('CashAndCashEquivalentsAtCarryingValue', {})),
        }
        
        # Extract income statement items
        income_statement = {
            'Revenues': self._get_latest_value(us_gaap.get('Revenues', {})),
            'CostOfRevenue': self._get_latest_value(us_gaap.get('CostOfRevenue', {})),
            'GrossProfit': self._get_latest_value(us_gaap.get('GrossProfit', {})),
            'OperatingIncome': self._get_latest_value(us_gaap.get('OperatingIncomeLoss', {})),
            'NetIncome': self._get_latest_value(us_gaap.get('NetIncomeLoss', {})),
            'InterestExpense': self._get_latest_value(us_gaap.get('InterestExpense', {})),
        }
        
        # Extract cash flow statement items
        cash_flow_statement = {
            'OperatingCashFlow': self._get_latest_value(us_gaap.get('NetCashProvidedByUsedInOperatingActivities', {})),
            'InvestingCashFlow': self._get_latest_value(us_gaap.get('NetCashProvidedByUsedInInvestingActivities', {})),
            'FinancingCashFlow': self._get_latest_value(us_gaap.get('NetCashProvidedByUsedInFinancingActivities', {})),
            'CapitalExpenditures': self._get_latest_value(us_gaap.get('PaymentsToAcquirePropertyPlantAndEquipment', {})),
        }
        
        return FinancialStatements(
            balance_sheet=balance_sheet,
            income_statement=income_statement,
            cash_flow_statement=cash_flow_statement
        )
    
    def _get_latest_value(self, fact_data: Dict[str, Any]) -> Optional[float]:
        """Extract the most recent value from a fact's data.
        
        Args:
            fact_data: Fact data containing units and values
            
        Returns:
            Most recent value or None if not available
        """
        if not fact_data or 'units' not in fact_data:
            return None
        
        # Try USD first, then other units
        for unit_type in ['USD', 'shares', 'pure']:
            if unit_type in fact_data['units']:
                values = fact_data['units'][unit_type]
                if values:
                    # Sort by end date and get most recent
                    sorted_values = sorted(
                        values,
                        key=lambda x: x.get('end', ''),
                        reverse=True
                    )
                    if sorted_values:
                        return sorted_values[0].get('val')
        
        return None
    
    def _get_latest_filing_date(self, facts: Dict[str, Any]) -> Optional[datetime]:
        """Get the date of the most recent filing.
        
        Args:
            facts: Company facts data
            
        Returns:
            Date of most recent filing or None
        """
        us_gaap = facts.get('facts', {}).get('us-gaap', {})
        latest_date = None
        
        # Check a few key facts to find the most recent date
        for fact_name in ['Assets', 'Revenues', 'NetIncomeLoss']:
            fact_data = us_gaap.get(fact_name, {})
            if 'units' in fact_data:
                for unit_type, values in fact_data['units'].items():
                    for value in values:
                        end_date_str = value.get('end')
                        if end_date_str:
                            try:
                                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                                if latest_date is None or end_date > latest_date:
                                    latest_date = end_date
                            except ValueError:
                                continue
        
        return latest_date
    
    def get_company_data(self, identifier: str) -> FinancialData:
        """Retrieve financial data for a company.
        
        Args:
            identifier: Company ticker symbol or CIK number
            
        Returns:
            Complete financial data for the company
            
        Raises:
            CompanyNotFoundError: If company not found
            IncompleteDataError: If data is incomplete
            DataProviderUnavailableError: If data retrieval fails
        """
        try:
            logger.info(f"Retrieving financial data for: {identifier}")
            
            # If identifier looks like a CIK (numeric), use it directly
            if identifier.isdigit():
                cik = identifier.zfill(10)
                # Look up company name from tickers
                tickers_map = self._load_company_tickers()
                company_name = None
                ticker = None
                for tick, info in tickers_map.items():
                    if info['cik'] == cik:
                        company_name = info['name']
                        ticker = tick
                        break
                if not company_name:
                    logger.warning(f"Company name not found for CIK: {cik}")
                    company_name = f"Company-{cik}"
                    ticker = identifier
            else:
                # Search by ticker
                companies = self.search_companies(identifier)
                if not companies:
                    raise CompanyNotFoundError(
                        message=f"Company not found: {identifier}",
                        user_message="Company not found. Please check the company name or ticker symbol.",
                        details={"identifier": identifier}
                    )
                
                # Use first match
                company = companies[0]
                cik = company.id
                company_name = company.name
                ticker = company.ticker
            
            # Get company facts
            logger.debug(f"Fetching company facts for CIK: {cik}")
            facts = self._get_company_facts(cik)
            
            # Extract financial statements
            logger.debug("Extracting financial statements")
            financial_statements = self._extract_financial_statements(facts)
            
            # Get filing date
            data_date = self._get_latest_filing_date(facts)
            if not data_date:
                logger.warning("Could not determine filing date, using current date")
                data_date = datetime.now()
            
            # Market data placeholder (SEC doesn't provide market data)
            market_data = {
                'note': 'Market data not available from SEC EDGAR',
                'source': 'SEC EDGAR'
            }
            
            financial_data = FinancialData(
                company_id=cik,
                company_name=company_name,
                ticker=ticker,
                financial_statements=financial_statements,
                market_data=market_data,
                data_date=data_date
            )
            
            logger.info(f"Successfully retrieved financial data for {ticker}")
            return financial_data
        
        except CompanyNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve financial data for {identifier}: {e}", exc_info=True)
            raise DataProviderUnavailableError(
                message=f"Failed to retrieve financial data: {e}",
                user_message="Unable to retrieve financial data. Please try again later.",
                details={"identifier": identifier}
            ) from e
    
    def validate_data_quality(self, data: FinancialData) -> DataQualityReport:
        """Validate completeness and freshness of financial data.
        
        Args:
            data: Financial data to validate
            
        Returns:
            Data quality report with validation results
        """
        missing_fields = []
        warnings = []
        
        # Check balance sheet completeness
        required_balance_sheet = ['Assets', 'Liabilities', 'StockholdersEquity']
        for field in required_balance_sheet:
            if data.financial_statements.balance_sheet.get(field) is None:
                missing_fields.append(f"balance_sheet.{field}")
        
        # Check income statement completeness
        required_income = ['Revenues', 'NetIncome']
        for field in required_income:
            if data.financial_statements.income_statement.get(field) is None:
                missing_fields.append(f"income_statement.{field}")
        
        # Check cash flow statement completeness
        required_cash_flow = ['OperatingCashFlow']
        for field in required_cash_flow:
            if data.financial_statements.cash_flow_statement.get(field) is None:
                missing_fields.append(f"cash_flow_statement.{field}")
        
        # Check data freshness
        data_age = datetime.now() - data.data_date
        data_age_days = data_age.days
        threshold_days = self.data_age_threshold_months * 30
        is_fresh = data_age_days <= threshold_days
        
        if not is_fresh:
            warnings.append(
                f"Data is {data_age_days} days old (threshold: {threshold_days} days). "
                "Rating may not reflect current conditions."
            )
        
        is_complete = len(missing_fields) == 0
        
        if not is_complete:
            warnings.append(
                f"Missing {len(missing_fields)} required fields: {', '.join(missing_fields[:3])}"
                + ("..." if len(missing_fields) > 3 else "")
            )
        
        return DataQualityReport(
            is_complete=is_complete,
            is_fresh=is_fresh,
            missing_fields=missing_fields,
            data_age_days=data_age_days,
            warnings=warnings
        )

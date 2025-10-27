"""
Currency utilities for business applications.
"""
from typing import List, Tuple, Dict, Optional
import json

# Comprehensive currency database with major world currencies
CURRENCY_DATABASE = {
    'USD': {'name': 'US Dollar', 'symbol': '$', 'code': 'USD', 'country': 'United States'},
    'EUR': {'name': 'Euro', 'symbol': '€', 'code': 'EUR', 'country': 'European Union'},
    'GBP': {'name': 'British Pound', 'symbol': '£', 'code': 'GBP', 'country': 'United Kingdom'},
    'JPY': {'name': 'Japanese Yen', 'symbol': '¥', 'code': 'JPY', 'country': 'Japan'},
    'CAD': {'name': 'Canadian Dollar', 'symbol': 'C$', 'code': 'CAD', 'country': 'Canada'},
    'AUD': {'name': 'Australian Dollar', 'symbol': 'A$', 'code': 'AUD', 'country': 'Australia'},
    'CHF': {'name': 'Swiss Franc', 'symbol': 'CHF', 'code': 'CHF', 'country': 'Switzerland'},
    'CNY': {'name': 'Chinese Yuan', 'symbol': '¥', 'code': 'CNY', 'country': 'China'},
    'INR': {'name': 'Indian Rupee', 'symbol': '₹', 'code': 'INR', 'country': 'India'},
    'BRL': {'name': 'Brazilian Real', 'symbol': 'R$', 'code': 'BRL', 'country': 'Brazil'},
    'MXN': {'name': 'Mexican Peso', 'symbol': '$', 'code': 'MXN', 'country': 'Mexico'},
    'RUB': {'name': 'Russian Ruble', 'symbol': '₽', 'code': 'RUB', 'country': 'Russia'},
    'KRW': {'name': 'South Korean Won', 'symbol': '₩', 'code': 'KRW', 'country': 'South Korea'},
    'SGD': {'name': 'Singapore Dollar', 'symbol': 'S$', 'code': 'SGD', 'country': 'Singapore'},
    'HKD': {'name': 'Hong Kong Dollar', 'symbol': 'HK$', 'code': 'HKD', 'country': 'Hong Kong'},
    'NZD': {'name': 'New Zealand Dollar', 'symbol': 'NZ$', 'code': 'NZD', 'country': 'New Zealand'},
    'SEK': {'name': 'Swedish Krona', 'symbol': 'kr', 'code': 'SEK', 'country': 'Sweden'},
    'NOK': {'name': 'Norwegian Krone', 'symbol': 'kr', 'code': 'NOK', 'country': 'Norway'},
    'DKK': {'name': 'Danish Krone', 'symbol': 'kr', 'code': 'DKK', 'country': 'Denmark'},
    'PLN': {'name': 'Polish Zloty', 'symbol': 'zł', 'code': 'PLN', 'country': 'Poland'},
    'CZK': {'name': 'Czech Koruna', 'symbol': 'Kč', 'code': 'CZK', 'country': 'Czech Republic'},
    'HUF': {'name': 'Hungarian Forint', 'symbol': 'Ft', 'code': 'HUF', 'country': 'Hungary'},
    'TRY': {'name': 'Turkish Lira', 'symbol': '₺', 'code': 'TRY', 'country': 'Turkey'},
    'ZAR': {'name': 'South African Rand', 'symbol': 'R', 'code': 'ZAR', 'country': 'South Africa'},
    'EGP': {'name': 'Egyptian Pound', 'symbol': 'E£', 'code': 'EGP', 'country': 'Egypt'},
    'NGN': {'name': 'Nigerian Naira', 'symbol': '₦', 'code': 'NGN', 'country': 'Nigeria'},
    'KES': {'name': 'Kenyan Shilling', 'symbol': 'KSh', 'code': 'KES', 'country': 'Kenya'},
    'GHS': {'name': 'Ghanaian Cedi', 'symbol': '₵', 'code': 'GHS', 'country': 'Ghana'},
    'MAD': {'name': 'Moroccan Dirham', 'symbol': 'MAD', 'code': 'MAD', 'country': 'Morocco'},
    'TND': {'name': 'Tunisian Dinar', 'symbol': 'TND', 'code': 'TND', 'country': 'Tunisia'},
    'DZD': {'name': 'Algerian Dinar', 'symbol': 'DZD', 'code': 'DZD', 'country': 'Algeria'},
    'ILS': {'name': 'Israeli Shekel', 'symbol': '₪', 'code': 'ILS', 'country': 'Israel'},
    'AED': {'name': 'UAE Dirham', 'symbol': 'AED', 'code': 'AED', 'country': 'United Arab Emirates'},
    'SAR': {'name': 'Saudi Riyal', 'symbol': 'SAR', 'code': 'SAR', 'country': 'Saudi Arabia'},
    'QAR': {'name': 'Qatari Riyal', 'symbol': 'QAR', 'code': 'QAR', 'country': 'Qatar'},
    'KWD': {'name': 'Kuwaiti Dinar', 'symbol': 'KWD', 'code': 'KWD', 'country': 'Kuwait'},
    'BHD': {'name': 'Bahraini Dinar', 'symbol': 'BHD', 'code': 'BHD', 'country': 'Bahrain'},
    'OMR': {'name': 'Omani Rial', 'symbol': 'OMR', 'code': 'OMR', 'country': 'Oman'},
    'JOD': {'name': 'Jordanian Dinar', 'symbol': 'JOD', 'code': 'JOD', 'country': 'Jordan'},
    'LBP': {'name': 'Lebanese Pound', 'symbol': 'LBP', 'code': 'LBP', 'country': 'Lebanon'},
    'THB': {'name': 'Thai Baht', 'symbol': '฿', 'code': 'THB', 'country': 'Thailand'},
    'VND': {'name': 'Vietnamese Dong', 'symbol': '₫', 'code': 'VND', 'country': 'Vietnam'},
    'IDR': {'name': 'Indonesian Rupiah', 'symbol': 'Rp', 'code': 'IDR', 'country': 'Indonesia'},
    'MYR': {'name': 'Malaysian Ringgit', 'symbol': 'RM', 'code': 'MYR', 'country': 'Malaysia'},
    'PHP': {'name': 'Philippine Peso', 'symbol': '₱', 'code': 'PHP', 'country': 'Philippines'},
    'TWD': {'name': 'Taiwan Dollar', 'symbol': 'NT$', 'code': 'TWD', 'country': 'Taiwan'},
    'PKR': {'name': 'Pakistani Rupee', 'symbol': '₨', 'code': 'PKR', 'country': 'Pakistan'},
    'BDT': {'name': 'Bangladeshi Taka', 'symbol': '৳', 'code': 'BDT', 'country': 'Bangladesh'},
    'LKR': {'name': 'Sri Lankan Rupee', 'symbol': '₨', 'code': 'LKR', 'country': 'Sri Lanka'},
    'NPR': {'name': 'Nepalese Rupee', 'symbol': '₨', 'code': 'NPR', 'country': 'Nepal'},
    'AFN': {'name': 'Afghan Afghani', 'symbol': '؋', 'code': 'AFN', 'country': 'Afghanistan'},
    'IRR': {'name': 'Iranian Rial', 'symbol': 'IRR', 'code': 'IRR', 'country': 'Iran'},
    'IQD': {'name': 'Iraqi Dinar', 'symbol': 'IQD', 'code': 'IQD', 'country': 'Iraq'},
    'SYP': {'name': 'Syrian Pound', 'symbol': 'SYP', 'code': 'SYP', 'country': 'Syria'},
    'YER': {'name': 'Yemeni Rial', 'symbol': 'YER', 'code': 'YER', 'country': 'Yemen'},
    'AMD': {'name': 'Armenian Dram', 'symbol': 'AMD', 'code': 'AMD', 'country': 'Armenia'},
    'AZN': {'name': 'Azerbaijani Manat', 'symbol': 'AZN', 'code': 'AZN', 'country': 'Azerbaijan'},
    'GEL': {'name': 'Georgian Lari', 'symbol': 'GEL', 'code': 'GEL', 'country': 'Georgia'},
    'KZT': {'name': 'Kazakhstani Tenge', 'symbol': 'KZT', 'code': 'KZT', 'country': 'Kazakhstan'},
    'KGS': {'name': 'Kyrgyzstani Som', 'symbol': 'KGS', 'code': 'KGS', 'country': 'Kyrgyzstan'},
    'TJS': {'name': 'Tajikistani Somoni', 'symbol': 'TJS', 'code': 'TJS', 'country': 'Tajikistan'},
    'TMT': {'name': 'Turkmenistani Manat', 'symbol': 'TMT', 'code': 'TMT', 'country': 'Turkmenistan'},
    'UZS': {'name': 'Uzbekistani Som', 'symbol': 'UZS', 'code': 'UZS', 'country': 'Uzbekistan'},
    'MNT': {'name': 'Mongolian Tugrik', 'symbol': '₮', 'code': 'MNT', 'country': 'Mongolia'},
    'KHR': {'name': 'Cambodian Riel', 'symbol': 'KHR', 'code': 'KHR', 'country': 'Cambodia'},
    'LAK': {'name': 'Lao Kip', 'symbol': 'LAK', 'code': 'LAK', 'country': 'Laos'},
    'MMK': {'name': 'Myanmar Kyat', 'symbol': 'MMK', 'code': 'MMK', 'country': 'Myanmar'},
    'BND': {'name': 'Brunei Dollar', 'symbol': 'BND', 'code': 'BND', 'country': 'Brunei'},
    'FJD': {'name': 'Fijian Dollar', 'symbol': 'FJD', 'code': 'FJD', 'country': 'Fiji'},
    'PGK': {'name': 'Papua New Guinea Kina', 'symbol': 'PGK', 'code': 'PGK', 'country': 'Papua New Guinea'},
    'SBD': {'name': 'Solomon Islands Dollar', 'symbol': 'SBD', 'code': 'SBD', 'country': 'Solomon Islands'},
    'VUV': {'name': 'Vanuatu Vatu', 'symbol': 'VUV', 'code': 'VUV', 'country': 'Vanuatu'},
    'WST': {'name': 'Samoan Tala', 'symbol': 'WST', 'code': 'WST', 'country': 'Samoa'},
    'TOP': {'name': 'Tongan Pa\'anga', 'symbol': 'TOP', 'code': 'TOP', 'country': 'Tonga'},
    'XPF': {'name': 'CFP Franc', 'symbol': 'XPF', 'code': 'XPF', 'country': 'French Polynesia'},
    'NZD': {'name': 'New Zealand Dollar', 'symbol': 'NZ$', 'code': 'NZD', 'country': 'New Zealand'},
    'AUD': {'name': 'Australian Dollar', 'symbol': 'A$', 'code': 'AUD', 'country': 'Australia'},
    'XDR': {'name': 'Special Drawing Rights', 'symbol': 'XDR', 'code': 'XDR', 'country': 'IMF'},
    'XAU': {'name': 'Gold (troy ounce)', 'symbol': 'XAU', 'code': 'XAU', 'country': 'Global'},
    'XAG': {'name': 'Silver (troy ounce)', 'symbol': 'XAG', 'code': 'XAG', 'country': 'Global'},
    'BTC': {'name': 'Bitcoin', 'symbol': '₿', 'code': 'BTC', 'country': 'Global'},
    'ETH': {'name': 'Ethereum', 'symbol': 'ETH', 'code': 'ETH', 'country': 'Global'},
}

# Common currencies for better UX (most frequently used)
COMMON_CURRENCIES = [
    'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'INR', 'BRL',
    'MXN', 'RUB', 'KRW', 'SGD', 'HKD', 'NZD', 'SEK', 'NOK', 'DKK', 'PLN',
    'CZK', 'HUF', 'TRY', 'ZAR', 'EGP', 'NGN', 'KES', 'GHS', 'MAD', 'TND',
    'ILS', 'AED', 'SAR', 'QAR', 'KWD', 'BHD', 'OMR', 'JOD', 'LBP', 'THB',
    'VND', 'IDR', 'MYR', 'PHP', 'TWD', 'PKR', 'BDT', 'LKR', 'NPR', 'AFN'
]


def get_all_currencies() -> List[str]:
    """
    Get all available currency codes.
    
    Returns:
        List of currency codes
    """
    return sorted(CURRENCY_DATABASE.keys())


def get_common_currencies() -> List[str]:
    """
    Get curated list of common currencies.
    
    Returns:
        List of common currency codes
    """
    return COMMON_CURRENCIES


def get_currency_info(currency_code: str) -> Optional[Dict]:
    """
    Get detailed information about a currency.
    
    Args:
        currency_code: Three-letter currency code (e.g., 'USD')
        
    Returns:
        Dictionary with currency information or None
    """
    return CURRENCY_DATABASE.get(currency_code.upper())


def get_currency_name(currency_code: str) -> str:
    """
    Get the full name of a currency.
    
    Args:
        currency_code: Three-letter currency code
        
    Returns:
        Currency name or the code if not found
    """
    info = get_currency_info(currency_code)
    return info['name'] if info else currency_code


def get_currency_symbol(currency_code: str) -> str:
    """
    Get the symbol for a currency.
    
    Args:
        currency_code: Three-letter currency code
        
    Returns:
        Currency symbol or the code if not found
    """
    info = get_currency_info(currency_code)
    return info['symbol'] if info else currency_code


def format_currency_choices() -> List[Tuple[str, str]]:
    """
    Format currencies for Django form choices.
    
    Returns:
        List of (currency_code, display_name) tuples
    """
    choices = []
    
    # Add common currencies first
    for currency in COMMON_CURRENCIES:
        if currency in CURRENCY_DATABASE:
            info = CURRENCY_DATABASE[currency]
            display_name = f"{info['name']} ({info['code']}) - {info['symbol']}"
            choices.append((currency, display_name))
    
    # Add separator
    choices.append(('', '──────────────'))
    
    # Add all other currencies
    all_currencies = get_all_currencies()
    for currency in all_currencies:
        if currency not in COMMON_CURRENCIES:
            info = CURRENCY_DATABASE[currency]
            display_name = f"{info['name']} ({info['code']}) - {info['symbol']}"
            choices.append((currency, display_name))
    
    return choices


def format_currency_amount(amount: float, currency_code: str, show_symbol: bool = True) -> str:
    """
    Format a currency amount with proper symbol and formatting.
    
    Args:
        amount: The amount to format
        currency_code: Three-letter currency code
        show_symbol: Whether to show the currency symbol
        
    Returns:
        Formatted currency string
    """
    info = get_currency_info(currency_code)
    symbol = info['symbol'] if info and show_symbol else currency_code
    
    # Basic formatting (can be enhanced with locale-specific formatting)
    if currency_code in ['JPY', 'KRW', 'VND', 'IDR']:
        # No decimal places for these currencies
        formatted_amount = f"{int(amount):,}"
    else:
        # Two decimal places for most currencies
        formatted_amount = f"{amount:,.2f}"
    
    return f"{symbol}{formatted_amount}"


def get_currencies_by_region(region: str) -> List[str]:
    """
    Get currencies by region.
    
    Args:
        region: Region name ('africa', 'asia', 'europe', 'americas', 'oceania')
        
    Returns:
        List of currency codes for the region
    """
    region_mapping = {
        'africa': ['ZAR', 'EGP', 'NGN', 'KES', 'GHS', 'MAD', 'TND', 'DZD'],
        'asia': ['JPY', 'CNY', 'INR', 'KRW', 'SGD', 'HKD', 'THB', 'VND', 'IDR', 'MYR', 'PHP', 'TWD', 'PKR', 'BDT', 'LKR', 'NPR', 'AFN', 'IRR', 'IQD', 'SYP', 'YER', 'AMD', 'AZN', 'GEL', 'KZT', 'KGS', 'TJS', 'TMT', 'UZS', 'MNT', 'KHR', 'LAK', 'MMK', 'BND'],
        'europe': ['EUR', 'GBP', 'CHF', 'RUB', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'TRY', 'ILS'],
        'americas': ['USD', 'CAD', 'BRL', 'MXN', 'ARS', 'CLP', 'COP', 'PEN', 'UYU', 'VES', 'GTQ', 'HNL', 'NIO', 'PAB', 'PYG', 'BOB', 'SRD', 'TTD', 'JMD', 'BBD', 'BZD', 'KYD', 'XCD'],
        'oceania': ['AUD', 'NZD', 'FJD', 'PGK', 'SBD', 'VUV', 'WST', 'TOP', 'XPF'],
        'middle_east': ['AED', 'SAR', 'QAR', 'KWD', 'BHD', 'OMR', 'JOD', 'LBP', 'ILS', 'IRR', 'IQD', 'SYP', 'YER']
    }
    
    return region_mapping.get(region.lower(), [])


def is_valid_currency(currency_code: str) -> bool:
    """
    Check if a currency code is valid.
    
    Args:
        currency_code: Three-letter currency code
        
    Returns:
        True if valid, False otherwise
    """
    return currency_code.upper() in CURRENCY_DATABASE


def get_currency_display_name(currency_code: str) -> str:
    """
    Get display name for a currency.
    
    Args:
        currency_code: Three-letter currency code
        
    Returns:
        Display name string
    """
    info = get_currency_info(currency_code)
    if info:
        return f"{info['name']} ({info['code']}) - {info['symbol']}"
    return currency_code

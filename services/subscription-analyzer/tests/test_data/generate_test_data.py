"""
Synthetic Test Data Generator for Subscription Leak Detector
Generates realistic bank statement data with hidden subscriptions.
GDPR compliant - no real customer data used.
"""

import csv
import random
from datetime import datetime, timedelta
from typing import List, Tuple

# Try to import openpyxl for Excel support
try:
    import openpyxl
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False
    print("Warning: openpyxl not installed. Excel export disabled. Run: pip install openpyxl")


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Subscriptions to simulate (name, base_amount, payment_day, variance)
SUBSCRIPTIONS: List[Tuple[str, float, int, float]] = [
    ("Netflix.com", 17.99, 1, 0.0),           # Fixed price
    ("Spotify Ab", 10.99, 12, 0.0),           # Fixed price
    ("ADOBE CREATIVE CLOUD", 64.99, 6, 0.0),  # Fixed price
    ("AWS EMEA SARL", 140.00, 10, 0.05),      # Variable (cloud usage)
    ("SLACK T0245 H8", 8.25, 3, 0.0),         # Fixed price
    ("AMZN Prime DE", 8.99, 5, 0.0),          # Fixed price
    ("Notion Labs Inc", 15.00, 20, 0.0),      # Fixed price
    ("OPENAI *CHATGPT SUBS", 22.00, 8, 0.0),  # Fixed price
]

# Regular merchants (one-off purchases)
REGULAR_MERCHANTS = [
    ("Carrefour Market Paris", 20.0, 120.0),
    ("UBER TRIP help.uber.com", 8.0, 35.0),
    ("SNCF TGV INOUI", 40.0, 180.0),
    ("Starbucks Coffee", 4.0, 12.0),
    ("Total Energies Station", 45.0, 95.0),
    ("Boulangerie Patisserie", 3.0, 15.0),
    ("Leclerc Hypermarche", 30.0, 200.0),
    ("Pharmacy Lafayette", 5.0, 45.0),
    ("FNAC Marketplace", 15.0, 150.0),
    ("Decathlon Sport", 20.0, 100.0),
]

# Hidden/forgotten subscriptions (the "WOW" factor)
HIDDEN_SUBSCRIPTIONS: List[Tuple[str, float, int, float]] = [
    ("TINDER GOLD", 14.99, 15, 0.0),          # Oops, forgot this one!
    ("NORD VPN Monthly", 11.99, 22, 0.0),     # Security tool forgotten
    ("LINKEDIN PREMIUM", 29.99, 18, 0.0),     # Professional expense
]


def generate_test_data(
    months: int = 3,
    start_date: datetime = datetime(2025, 11, 1),
    include_hidden: bool = True,
    output_prefix: str = "test_statement"
) -> str:
    """
    Generates synthetic bank statement data.
    
    Args:
        months: Number of months to generate
        start_date: Starting date for transactions
        include_hidden: Whether to include "forgotten" subscriptions
        output_prefix: Prefix for output files
    
    Returns:
        Path to generated CSV file
    """
    data = []
    
    # Combine subscriptions
    all_subscriptions = SUBSCRIPTIONS.copy()
    if include_hidden:
        all_subscriptions.extend(HIDDEN_SUBSCRIPTIONS)
    
    # Generate data for each day in the period
    total_days = months * 30
    
    for day_offset in range(total_days):
        current_date = start_date + timedelta(days=day_offset)
        
        # 1. Add subscriptions if it's their payment day
        for sub_name, base_amount, payment_day, variance in all_subscriptions:
            # Allow +/- 1 day variance for realism
            if current_date.day in [payment_day - 1, payment_day, payment_day + 1]:
                # Only trigger once per month (probabilistically handle day variance)
                if current_date.day == payment_day or random.random() < 0.3:
                    # Apply amount variance (for cloud services like AWS)
                    if variance > 0:
                        amount = base_amount * random.uniform(1 - variance, 1 + variance)
                    else:
                        amount = base_amount
                    
                    data.append({
                        "Date": current_date.strftime('%Y-%m-%d'),
                        "Description": sub_name,
                        "Amount": round(amount, 2),
                        "Currency": "EUR"
                    })
        
        # 2. Add random regular purchases (0-4 per day)
        num_purchases = random.randint(0, 4)
        for _ in range(num_purchases):
            merchant, min_amount, max_amount = random.choice(REGULAR_MERCHANTS)
            amount = random.uniform(min_amount, max_amount)
            
            data.append({
                "Date": current_date.strftime('%Y-%m-%d'),
                "Description": merchant,
                "Amount": round(amount, 2),
                "Currency": "EUR"
            })
    
    # Sort by date
    data.sort(key=lambda x: x["Date"])
    
    # Save CSV
    csv_path = f"{output_prefix}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Amount", "Currency"])
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ CSV saved: {csv_path} ({len(data)} transactions)")
    
    # Save Excel if supported
    if EXCEL_SUPPORT:
        xlsx_path = f"{output_prefix}.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Bank Statement"
        
        # Header
        ws.append(["Date", "Description", "Amount", "Currency"])
        
        # Data
        for row in data:
            ws.append([row["Date"], row["Description"], row["Amount"], row["Currency"]])
        
        wb.save(xlsx_path)
        print(f"✅ Excel saved: {xlsx_path}")
    
    # Print summary
    print(f"\n📊 Summary:")
    print(f"   Period: {start_date.strftime('%Y-%m-%d')} to {(start_date + timedelta(days=total_days)).strftime('%Y-%m-%d')}")
    print(f"   Total transactions: {len(data)}")
    print(f"   Subscriptions included: {len(all_subscriptions)}")
    if include_hidden:
        print(f"   Hidden subscriptions: {len(HIDDEN_SUBSCRIPTIONS)} (for WOW effect)")
    
    return csv_path


def generate_simple_csv():
    """Creates a simple, hand-crafted CSV for quick testing."""
    simple_data = """Date,Description,Amount,Currency
2025-12-01,Netflix.com,17.99,EUR
2025-12-02,UBER TRIP help.uber.com,14.50,EUR
2025-12-03,SLACK T0245 H8,8.25,EUR
2025-12-05,AMZN Prime DE,8.99,EUR
2025-12-05,Carrefour Market Paris,45.20,EUR
2025-12-06,ADOBE CREATIVE CLOUD,64.99,EUR
2025-12-10,AWS EMEA SARL,143.20,EUR
2025-12-12,Spotify Ab,10.99,EUR
2025-12-15,Starbucks Coffee,5.50,EUR
2026-01-01,Netflix.com,17.99,EUR
2026-01-03,SLACK T0245 H8,8.25,EUR
2026-01-05,AMZN Prime DE,8.99,EUR
2026-01-06,ADOBE CREATIVE CLOUD,64.99,EUR
2026-01-10,AWS EMEA SARL,145.10,EUR
2026-01-12,Spotify Ab,10.99,EUR
2026-01-14,SNCF TGV INOUI,85.00,EUR
2026-01-20,Notion Labs Inc,15.00,EUR
2026-02-01,Netflix.com,17.99,EUR
2026-02-03,SLACK T0245 H8,8.25,EUR
2026-02-05,AMZN Prime DE,8.99,EUR
2026-02-06,ADOBE CREATIVE CLOUD,64.99,EUR
2026-02-12,Spotify Ab,10.99,EUR
2026-02-20,Notion Labs Inc,15.00,EUR
2026-02-15,TINDER GOLD,14.99,EUR
2026-01-15,TINDER GOLD,14.99,EUR
2025-12-15,TINDER GOLD,14.99,EUR"""

    with open("simple_test.csv", 'w', encoding='utf-8') as f:
        f.write(simple_data)
    
    print("✅ Simple test file saved: simple_test.csv")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Subscription Leak Detector - Test Data Generator")
    print("=" * 60)
    print()
    
    # 1. Generate simple CSV
    generate_simple_csv()
    print()
    
    # 2. Generate large dataset
    generate_test_data(
        months=3,
        start_date=datetime(2025, 11, 1),
        include_hidden=True,
        output_prefix="test_statement"
    )
    
    print()
    print("🎉 Done! Use these files for testing your Subscription Detector.")

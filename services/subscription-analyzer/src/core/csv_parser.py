import pandas as pd
import io
import re
from typing import List
from ..db.models import Transaction
from datetime import datetime

def parse_csv(file_content: bytes, filename: str = "") -> List[Transaction]:
    """
    Parses a CSV or Excel file content into a list of Transaction objects.
    Handles different encodings, separators, and file formats.
    
    Supported formats:
    - CSV (.csv) with comma or semicolon separators
    - Excel (.xlsx, .xls)
    """

    df = None
    
    # Check if Excel file
    if filename.lower().endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(io.BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Could not parse Excel file: {e}")
    else:
        # CSV parsing with encoding detection
        encodings = ['utf-8', 'iso-8859-1', 'cp1252']

        for encoding in encodings:
            try:
                # Try comma, then semicolon
                for sep in [',', ';']:
                    try:
                        # Read first few lines to check
                        temp_df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=sep, nrows=5)
                        if len(temp_df.columns) > 1:
                            # If looks good, read full
                            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=sep)
                            break
                    except:
                        continue
                if df is not None:
                    break
            except:
                continue

    if df is None:
        raise ValueError("Could not parse file. Please ensure it is a valid CSV or Excel file.")

    # Normalize columns
    df.columns = df.columns.str.lower().str.strip()

    # Identify required columns
    date_col = next((c for c in df.columns if 'date' in c), None)
    desc_col = next((c for c in df.columns if any(x in c for x in ['desc', 'merchant', 'text', 'narrative', 'details'])), None)
    amount_col = next((c for c in df.columns if any(x in c for x in ['amount', 'value', 'sum', 'debit', 'credit'])), None)
    curr_col = next((c for c in df.columns if any(x in c for x in ['curr'])), None)

    if not all([date_col, desc_col, amount_col]):
        raise ValueError(f"Missing required columns. Found: date={date_col}, desc={desc_col}, amount={amount_col}. Headers: {list(df.columns)}")

    transactions = []

    for _, row in df.iterrows():
        try:
            # Parse date
            date_str = str(row[date_col])
            try:
                dt = pd.to_datetime(date_str, dayfirst=True).date() # European date format preference
            except:
                dt = pd.to_datetime(date_str).date() # Fallback

            # Parse amount
            amount_val = row[amount_col]
            if isinstance(amount_val, (int, float)):
                amount = float(amount_val)
            else:
                amount_str = str(amount_val).replace(' ', '')
                # If comma is used as decimal separator (EU style)
                if ',' in amount_str and '.' in amount_str:
                     # e.g. 1.000,00 -> 1000.00
                     if amount_str.find(',') > amount_str.find('.'):
                        amount_str = amount_str.replace('.', '').replace(',', '.')
                elif ',' in amount_str:
                    amount_str = amount_str.replace(',', '.')

                amount_str = re.sub(r'[^\d.-]', '', amount_str)
                amount = float(amount_str)

            desc = str(row[desc_col]).strip()
            curr = str(row[curr_col]).strip() if curr_col and pd.notna(row[curr_col]) else "EUR"

            transactions.append(Transaction(
                date=dt,
                description=desc,
                amount=amount,
                currency=curr
            ))
        except Exception as e:
            # Log error but continue
            continue

    return transactions

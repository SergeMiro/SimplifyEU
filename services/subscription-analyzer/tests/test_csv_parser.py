import pytest
from datetime import date
from src.core.csv_parser import parse_csv

def test_parse_valid_csv():
    content = b"Date,Description,Amount\n2023-01-01,Netflix,-15.99\n2023-01-02,Spotify,-9.99"
    transactions = parse_csv(content)
    assert len(transactions) == 2
    assert transactions[0].description == "Netflix"
    assert transactions[0].amount == -15.99
    assert transactions[0].date == date(2023, 1, 1)

def test_parse_semicolon_csv():
    content = b"Date;Description;Amount\n2023-01-01;Netflix;-15,99"
    transactions = parse_csv(content)
    assert len(transactions) == 1
    assert transactions[0].amount == -15.99


import os
import sys
from supabase import create_client

# Hardcoded credentials from what we found in .env files previously viewed
URL = "https://qzdxmogqtcbdouxdmpon.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6ZHhtb2dxdGNiZG91eGRtcG9uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg2MzM2MjksImV4cCI6MjA4NDIwOTYyOX0.DZCdDL3Q_0OkAqAyUe2PUBLpw_F7jOED8xFxvtfpRyk"

def run_migration():
    print(f"Connecting to {URL}...")
    supabase = create_client(URL, KEY)
    
    # Try to execute raw SQL via an RPC function if available, or check if we can query
    # Since we can't run RAW SQL directly via Client library without an RPC wrapper,
    # we usually have to use the Dashboard. 
    # BUT, we can check if the table exists by trying to select from it.
    
    print("Checking if 'analyses' table exists...")
    try:
        res = supabase.table("analyses").select("*").limit(1).execute()
        print("Table 'analyses' exists!")
        print(res)
    except Exception as e:
        print(f"Check failed: {e}")
        print("\nCANNOT AUTHENTICATE AS ADMIN. Please run migration manually.")

if __name__ == "__main__":
    run_migration()

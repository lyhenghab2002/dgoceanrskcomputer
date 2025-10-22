#!/usr/bin/env python3
"""
Check product pricing data
"""
import os
import MySQLdb
from dotenv import load_dotenv

load_dotenv()

def check_products():
    try:
        host = os.getenv('MYSQL_HOST') or 'localhost'
        user = os.getenv('MYSQL_USER') or 'root'
        password = os.getenv('MYSQL_PASSWORD') or '12345'
        database = os.getenv('MYSQL_DB') or 'rskpc'
        
        conn = MySQLdb.connect(host=host, user=user, password=password, database=database)
        cur = conn.cursor()
        
        print("\n" + "="*80)
        print("CHECKING PRODUCT PRICES")
        print("="*80 + "\n")
        
        # Check the HP Pavilion product
        cur.execute("""
            SELECT id, name, price, original_price, (price - original_price) as profit_per_unit
            FROM products
            WHERE name LIKE '%HP Pavilion%'
            LIMIT 5
        """)
        
        products = cur.fetchall()
        
        for product in products:
            product_id, name, price, original_price, profit = product
            print(f"Product: {name}")
            print(f"  ID: {product_id}")
            print(f"  Selling Price: ${price}")
            print(f"  Original Price (Cost): ${original_price}")
            print(f"  Profit per unit: ${profit}")
            
            if profit < 0:
                print(f"  [ERROR] NEGATIVE PROFIT! Original price is HIGHER than selling price!")
                print(f"  [FIX NEEDED] original_price should be YOUR COST, not retail price")
            print()
        
        # Check order 1060 and 1061 specifically
        print("-"*80)
        print("CHECKING TODAY'S ORDERS (1060, 1061):")
        print("-"*80 + "\n")
        
        for order_id in [1060, 1061]:
            cur.execute("""
                SELECT 
                    oi.product_id,
                    p.name,
                    oi.quantity,
                    oi.price as selling_price,
                    p.original_price as cost_price,
                    (oi.price - p.original_price) as profit_per_unit,
                    (oi.price - p.original_price) * oi.quantity as total_profit
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """, (order_id,))
            
            items = cur.fetchall()
            print(f"Order #{order_id}:")
            for item in items:
                pid, pname, qty, sell, cost, profit_per, total_profit = item
                print(f"  Product: {pname}")
                print(f"    Quantity: {qty}")
                print(f"    Selling Price: ${sell}")
                print(f"    Cost (original_price): ${cost}")
                print(f"    Profit per unit: ${profit_per}")
                print(f"    Total Profit: ${total_profit}")
                
                if total_profit < 0:
                    print(f"    [PROBLEM] Negative profit means original_price ({cost}) > selling_price ({sell})")
            print()
        
        print("="*80)
        print("EXPLANATION:")
        print("="*80)
        print("The 'original_price' field should be YOUR COST (what you paid for it),")
        print("NOT the retail/MSRP price. If you're selling for $0.01 but original_price")
        print("is $892, the system thinks you're losing $891.99 per sale!")
        print()
        print("Fix: Update products table with correct cost prices (what YOU paid)")
        print("="*80 + "\n")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_products()



from shared import get_db_connection

def init_translation_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("Initializing product_translations table...")
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopee_orders.product_translations (
                product_id VARCHAR(50) NOT NULL,
                field_type VARCHAR(20) NOT NULL,
                translated_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (product_id, field_type)
            )
        """)
        conn.commit()
        print("Table created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_translation_table()

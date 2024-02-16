import csv
from faker import Faker

fake = Faker()

def generate_synthetic_data(num_rows):
    data = []
    for _ in range(num_rows):
        record_id = fake.random_int(min=100000, max=999999)
        first_name = fake.first_name()
        last_name = fake.last_name()
        address = fake.address().replace("\n", ", ")
        email_address = fake.email()
        product_sku = fake.random_int(min=1000, max=9999)
        product_quantity = fake.random_int(min=1, max=10)
        
        row = [record_id,first_name, last_name, address, email_address, product_sku, product_quantity]
        data.append(row)
    
    return data

# Generate 100 rows of synthetic data
num_rows = 100
synthetic_data = generate_synthetic_data(num_rows)

# Save data to CSV file
filename = "sample.csv"
with open(filename, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["record_id","first_name", "last_name", "address", "email_address", "product_sku", "product_quantity"])  # Write header
    writer.writerows(synthetic_data)  # Write rows

print(f"Data saved to {filename}.")

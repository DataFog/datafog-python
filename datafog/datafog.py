from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from werkzeug.utils import secure_filename
import os
import logging
import binascii
import faker
from faker import Faker
from .models import ValueMapping, Base
import typing
from typing import Optional, Dict, Tuple, List, Any
import hashlib

# Logging
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


class DataFog:

    def __init__(self, db_path='sqlite:///./test.db'):
        self.engine = create_engine(db_path, echo = False)
        Base.metadata.create_all(self.engine)  # Create tables
        self.Session = sessionmaker(bind=self.engine)
        self.ban_list =["address","age","bank_account","credit_card",
        "credit_card_expiration","date","email_address","first_name",
        "ip_address","last_name","location","city","latlong","country",
        "state","zip","name","occupation","passport_number","password",
        "phone_number","product_sku","routing_number","ssn","time","username","license_plate"]

 # Put your initial list here
        self.ban_list_version = 1

    def show_banlist(self):
        print(f"Ban List Version {self.ban_list_version}:")
        print(self.ban_list)

    def add_to_banlist(self, *args):
        added_fields = [field for field in args if field not in self.ban_list]
        if not added_fields:
            print("No new fields to add.")
            return
        self.ban_list.extend(added_fields)
        self.ban_list_version += 1
        print(f"Successfully added: {added_fields}")
        print(f"Updated Ban List (Version {self.ban_list_version}):")
        print(self.ban_list)

    def remove_from_banlist(self, *args):
        original_len = len(self.ban_list)
        self.ban_list = [field for field in self.ban_list if field not in args]
        removed_fields = args if len(self.ban_list) < original_len else []
        if not removed_fields:
            print("No fields to remove.")
            return
        self.ban_list_version += 1
        print(f"Successfully removed: {removed_fields}")
        print(f"Updated Ban List (Version {self.ban_list_version}):")
        print(self.ban_list)

    def scan(self, input_path: str) -> Tuple[bool, List[str]]:
        """
        The method returns a tuple, where the first element is the boolean contains_pii
         and the second element is the list pii_fields. You can then call this method 
         and handle the output as needed in your specific use case. 
         For example, you could convert the list of PII fields to JSON.
        """
        fake = Faker()

        # Read the file from input_path
        df = pd.read_csv(input_path)

        # Initialize empty list for PII fields
        pii_fields = []

        for col in df.columns:
            if col in self.ban_list:
                pii_fields.append(col)

        # Determine if any PII fields were found
        contains_pii = len(pii_fields) > 0

        return contains_pii, pii_fields

    def swap(self, input_path: str, output_path: str) -> bool:
        # Faker Setup
        fake = Faker()

        faker_methods = {
            "address": fake.address,
            "age": lambda: fake.random_int(min=18, max=90),
            "bank_account": fake.bban,
            "credit_card": fake.credit_card_full,
            "credit_card_expiration": fake.credit_card_expire,
            "date": fake.date,
            "email_address": fake.email,
            "first_name": fake.first_name,
            "ip_address": fake.ipv4,
            "last_name": fake.last_name,
            "location": fake.location_on_land,
            "city": fake.city,
            "latlong": fake.latlng,
            "country": fake.country,
            "state": fake.state,
            "zip": fake.postcode,
            "name": fake.name,
            "occupation": fake.job,
            "password": lambda: fake.password(length=12, special_chars=False, upper_case=True),
            "phone_number": fake.phone_number,
            "product_sku": fake.isbn13,
            "routing_number": fake.aba,
            "ssn": fake.ssn,
            "time": fake.time,
            "license_plate": fake.license_plate
            }


        

        # Read the file from train_path
        df = pd.read_csv(input_path)

        for col in df.columns:
            if col in self.ban_list and col in faker_methods:
                original_values = df[col].tolist()  # Keep a list of original values
                df[col] = df[col].apply(lambda x: faker_methods[col]())  # Synthetic values
                synthetic_values = df[col].tolist()  # Keep a list of synthetic values

            # Save each original and synthetic value pair in the database
                for original, synthetic in zip(original_values, synthetic_values):
                    self.save(record_id=None, field_name=col, original_value=original, new_value=synthetic)

        # Save the modified DataFrame to a new file
        df.to_csv(os.path.join(output_path, 'synthetic_output.csv'), index=False)


        print(df)
        return True


    @staticmethod
    def redact(value: str) -> str:
        return "[REDACTED]"

    @staticmethod
    def hash(value: str) -> str:
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    def save(self, record_id, field_name, original_value, new_value):
        # create a new session
        session = self.Session()

        try:
            # create a new ValueMapping instance
            data = ValueMapping(
                record_id=record_id,
                field_name=field_name,
                original_value=original_value,
                new_value=new_value,
            )

            # add and commit
            session.add(data)
            session.commit()

        except Exception as e:
            print(f"An error occurred: {e}")
            session.rollback()  # Rollback the changes on error

        finally:
            session.close()  # Close the session



    def process_kafka_record(self, record: Dict) -> Dict:
        """
        Process a Kafka record: lookup in the ValueMapping table and swap the original values 
        with the new values for each key that matches a 'fieldname' in the record.
        """
        # Step 2-3: Parse the record to isolate the message
        message = record['message']  # or however you access the message in the record
        
        # Step 4: Perform a lookup on the ValueMapping table and grab all records that match the record_id
        record_id = message.get('record_id')
        value_mappings = self.lookup(record_id)

        # Step 5: If there is a record that is a match, swap out the original values with the new values
        if value_mappings:
            for value_mapping in value_mappings:
                if value_mapping.field_name in message:
                    message[value_mapping.field_name] = value_mapping.new_value
        
        # Step 6: Return the modified record
        record['message'] = message
        return record

    def lookup(self, record_id: str) -> Optional[List[ValueMapping]]:
        """
        Query the ValueMapping table for records that match the given record_id.
        """
        session = self.Session()  # create a session
        value_mappings = session.query(ValueMapping).filter_by(record_id=record_id).all()
        return value_mappings if value_mappings else None




    def swap_back(self, record: Dict) -> Dict:
        """
        Process a Kafka record: lookup in the ValueMapping table and swap the synthetic values 
        with the original values for each key that matches a 'fieldname' in the record.
        """
        # Parse the record to isolate the message
        message = record['message']  # or however you access the message in the record

        # Perform a lookup on the ValueMapping table and grab all records that match the record_id
        record_id = message.get('record_id')
        value_mappings = self.lookup(record_id)

        # If there is a record that is a match, swap out the synthetic values with the original values
        if value_mappings:
            for value_mapping in value_mappings:
                if value_mapping.field_name in message:
                    message[value_mapping.field_name] = value_mapping.original_value

        # Return the modified record
        record['message'] = message
        return record

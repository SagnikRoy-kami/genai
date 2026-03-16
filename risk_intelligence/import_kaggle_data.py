import csv
import requests
import time

csv_file_path = "kaggle_data/project_risk_raw_dataset.csv" 
new_rag_records = []

print("Reading the Kaggle CSV dataset...")

try:
    with open(csv_file_path, mode='r', encoding='utf-8-sig') as file:
        csv_reader = csv.DictReader(file)
        
        for row in csv_reader:
            context_text = (
                f"Project {row['Project_ID']} is a {row['Project_Type']} project using {row['Methodology_Used']} methodology. "
                f"It has a budget of ${float(row['Project_Budget_USD']):.2f} over {row['Estimated_Timeline_Months']} months. "
                f"The team experience level is {row['Team_Experience_Level']}, and the complexity score is {row['Complexity_Score']}. "
                f"It had {row['Historical_Risk_Incidents']} historical risk incidents and {row['External_Dependencies_Count']} external dependencies. "
                f"The final assessed risk level for this project was {row['Risk_Level']}."
            )
            
            new_rag_records.append({
                "id": f"kaggle_{row['Project_ID']}",  # <--- WE ADDED THIS LINE!
                "text": context_text,
                "metadata": {"source": "kaggle_project_risk_dataset", "type": "historical_project"}
            })

    print(f"Successfully formatted {len(new_rag_records)} historical projects.")
    
    # --- NEW BATCHING LOGIC ---
    BATCH_SIZE = 100
    total_batches = (len(new_rag_records) // BATCH_SIZE) + (1 if len(new_rag_records) % BATCH_SIZE != 0 else 0)
    
    print(f"Sending them in {total_batches} batches of {BATCH_SIZE} to prevent server overload...\n")
    
    for i in range(0, len(new_rag_records), BATCH_SIZE):
        batch = new_rag_records[i : i + BATCH_SIZE]
        current_batch_num = (i // BATCH_SIZE) + 1
        
        print(f"Sending Batch {current_batch_num}/{total_batches} ({len(batch)} records)...")
        
        response = requests.post(
            "http://127.0.0.1:8000/api/rag/ingest", 
            json={"records": batch}
        )
        
        if response.status_code == 200:
            print(f"  ✅ Batch {current_batch_num} SUCCESS")
        else:
            print(f"  ❌ Batch {current_batch_num} FAILED: {response.text}")
            print("Stopping script to prevent further errors.")
            break
            
        # Pause for 1 second to let ChromaDB generate the embeddings safely
        time.sleep(1)

    print("\n🎉 Finished Data Ingestion!")

except FileNotFoundError:
    print(f"❌ ERROR: Could not find '{csv_file_path}'. Make sure it is in the same folder as this script!")
except requests.exceptions.ConnectionError:
    print("❌ ERROR: Could not connect to the server. Make sure 'python main.py' is running in another terminal window!")
except Exception as e:
    print(f"❌ ERROR: {e}")
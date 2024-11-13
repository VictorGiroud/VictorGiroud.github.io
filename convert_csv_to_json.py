import csv
import json

def csv_to_json(csv_filepath, json_filepath):
    data = []
    with open(csv_filepath, mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        
        for row in csv_reader:
            commune = {
                "code_commune": row["code_commune"],
                "nom_commune": row["nom_commune"],
                "code_departement": row["code_departement"],
                "nom_departement": row["nom_departement"],
                "nom_region": row["nom_region"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "images": [
                    row["image_1"],
                    row["image_2"],
                    row["image_3"],
                    row["image_4"]
                ]
            }
            data.append(commune)
    
    # Enregistrer les données en JSON
    with open(json_filepath, mode='w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

# Utilisation du script
csv_filepath = 'enedis_data_with_images.csv'
json_filepath = 'enedis_data.json'     # Le fichier JSON de sortie
csv_to_json(csv_filepath, json_filepath)

import requests
import csv
import os

# Paramètres principaux
LIMIT_DATA = 10  # Limite de données à traiter par département
DEPARTMENTS_TO_FETCH = 95  # Nombre de départements à traiter
MIN_IMAGE_SIZE = 20000  # Taille minimale en octets pour une image valide

# URL de l'API Enedis
url_base_data = "https://data.enedis.fr/api/explore/v2.1/catalog/datasets/poste-electrique/records"

# URL de Google Street View
street_view_url = "https://maps.googleapis.com/maps/api/streetview"
api_key_google = "secret"

# Dossier pour stocker les images
image_dir = "images"
os.makedirs(image_dir, exist_ok=True)

# Liste des orientations à tester (0°, 90°, 180°, 270°)
headings = [0, 90, 180, 270]

def fetch_enedis_data():
    print("Début de la récupération des données Enedis.")
    data = []
    for dept_code in range(1, DEPARTMENTS_TO_FETCH + 1):
        dept_code_str = str(dept_code).zfill(2)
        params = {
            "limit": LIMIT_DATA * 2,  # Récupère le double de la limite pour avoir de la marge
            "refine": f"code_departement:{dept_code_str}"
        }
        print(f"Récupération des données pour le département {dept_code_str} avec limite de {LIMIT_DATA * 5}.")
        response = requests.get(url_base_data, params=params)
        results = response.json().get("results", [])
        
        # Extraction des coordonnées depuis chaque record
        for commune in results:
            lat = commune.get("geo_point_2d", {}).get("lat")
            lon = commune.get("geo_point_2d", {}).get("lon")
            if lat and lon:
                data_entry = {
                    "code_commune": commune.get("code_commune"),
                    "nom_commune": commune.get("nom_commune"),
                    "code_departement": commune.get("code_departement"),
                    "nom_departement": commune.get("nom_departement"),
                    "nom_region": commune.get("nom_region"),
                    "latitude": lat,
                    "longitude": lon,
                }
                data.append(data_entry)
                print(f"Ajout d'un poste électrique : {data_entry}")
                
    print(f"Récupération terminée pour {DEPARTMENTS_TO_FETCH} départements, {len(data)} enregistrements récupérés.")
    return data


def check_image_exists(lat, lon, heading):
    """Vérifie si une image existe à la position et orientation spécifiées."""
    metadata_url = "https://maps.googleapis.com/maps/api/streetview/metadata"
    params = {
        "location": f"{lat},{lon}",
        "heading": heading,
        "key": api_key_google
    }
    
    response = requests.get(metadata_url, params=params)
    
    if response.status_code == 200:
        metadata = response.json()
        if metadata.get("status") == "OK":
            print(f"Image disponible pour {lat},{lon} avec orientation {heading}.")
            return True
        else:
            print(f"Aucune image trouvée pour {lat},{lon} avec orientation {heading}.")
            return False
    else:
        print(f"Erreur de l'API Image Metadata pour {lat},{lon} avec orientation {heading}. Code statut : {response.status_code}.")
        return False


def download_images_for_location(lat, lon, base_filename):
    image_paths = []
    print(f"Téléchargement des images pour la position {lat}, {lon}.")

    for i, heading in enumerate(headings):
        # Vérification de l'existence de l'image avant de la télécharger
        if not check_image_exists(lat, lon, heading):
            print(f"Passage de l'orientation {heading} (image inexistante).")
            continue  # Si l'image n'existe pas, on passe à l'orientation suivante

        params = {
            "size": "600x400",
            "location": f"{lat},{lon}",
            "heading": heading,
            "key": api_key_google
        }
        response = requests.get(street_view_url, params=params)
        
        # Vérification de la taille de l'image
        if response.status_code == 200:
            print(f"Réponse de l'image pour orientation {heading}: {len(response.content)} octets.")
            if len(response.content) > MIN_IMAGE_SIZE:
                image_filename = f"{base_filename}_heading_{i}.jpg"
                with open(image_filename, "wb") as img_file:
                    img_file.write(response.content)
                image_paths.append(image_filename)
                print(f"Image valide enregistrée pour {lat}, {lon} avec orientation {heading}.")
            else:
                print(f"Image ignorée (taille insuffisante) pour {lat}, {lon} avec orientation {heading}.")
        else:
            print(f"Erreur de téléchargement de l'image pour orientation {heading} à {lat}, {lon}. Code statut: {response.status_code}")

        if len(image_paths) == 4:  # On arrête si on a déjà 4 images valides
            break

    # Complète avec des valeurs vides si moins de 4 images valides ont été trouvées
    while len(image_paths) < 4:
        image_paths.append("")
        print("Aucune image valide supplémentaire trouvée pour cet enregistrement, ajout d'un champ vide.")

    return image_paths


def process_data(data):
    csv_filename = "enedis_data_with_images.csv"
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as csv_file:
        fieldnames = ["code_commune", "nom_commune", "code_departement", "nom_departement", "nom_region", "latitude", "longitude", "image_1", "image_2", "image_3", "image_4"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        
        dept_counts = {}
        
        print(f"Début de l'écriture dans le fichier CSV : {csv_filename}.")
        for index, row in enumerate(data):
            dept_code = row["code_departement"]
            
            # Initialisation du comptage pour le département si nécessaire
            if dept_code not in dept_counts:
                dept_counts[dept_code] = 0
            
            # Vérification si la limite est atteinte pour ce département
            if dept_counts[dept_code] >= LIMIT_DATA:
                print(f"Limite atteinte pour le département {dept_code}, passage au suivant.")
                continue  # Passer à l'enregistrement suivant sans l'ajouter pour ce département
            
            print (f"{row}")
            lat, lon = row["latitude"], row["longitude"]
            base_filename = os.path.join(image_dir, f"image_{index}")
            
            # Téléchargement des images pour chaque orientation
            image_paths = download_images_for_location(lat, lon, base_filename)
            
            # N'enregistre la ligne que si au moins une image est valide
            if any(image_paths):
                row["image_1"], row["image_2"], row["image_3"], row["image_4"] = image_paths
                writer.writerow(row)
                print(f"Ligne ajoutée pour {lat}, {lon} avec images.")
            else:
                print(f"Ligne ignorée pour {lat}, {lon} (aucune image valide trouvée).")

    print(f"Écriture dans le fichier CSV terminée. Fichier disponible : {csv_filename}.")

# Exécution du script
print("Script démarré.")
data = fetch_enedis_data()
process_data(data)
print("Script terminé.")

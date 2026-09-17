"""
downloads the raw dataset straight from the UCI Machine Learning Repository.
this project does not bundle the raw csv in the repo itself, since it's about 18 megabytes
and the license already allows redistribution, there's just no good reason to store a
large file in git when a two-line download does the same job on demand. this script only
uses python's standard library, so nothing needs to be pip installed just to fetch data.
"""

# urllib.request is python's built-in tool for downloading a file from a url
import urllib.request
# zipfile is python's built-in tool for reading the contents of a .zip archive
import zipfile
# os is used to create the data folder if it doesn't already exist
import os

# the official, permanent download link for this dataset on the UCI repository
DATASET_URL = "https://archive.ics.uci.edu/static/public/296/diabetes+130-us+hospitals+for+years+1999-2008.zip"
# where the downloaded zip file will be temporarily saved
ZIP_DESTINATION = "data/diabetes_130_us_hospitals.zip"
# the folder everything gets extracted into
DATA_FOLDER = "data"


def download_dataset():
    """
    downloads the zip archive from UCI and saves it to disk. this is a separate function
    from extraction so a slow download and a fast extraction step are easy to tell apart
    if something goes wrong
    """
    # make sure the data folder exists before we try to save a file into it
    os.makedirs(DATA_FOLDER, exist_ok=True)
    # let the person running this script know something is happening, since the download
    # can take a little while depending on their connection
    print(f"downloading dataset from {DATASET_URL} ...")
    # urlretrieve fetches the url and writes the response straight to ZIP_DESTINATION
    urllib.request.urlretrieve(DATASET_URL, ZIP_DESTINATION)
    # confirm the download finished before moving on
    print("download complete.")


def extract_dataset():
    """
    unzips the downloaded archive into the data folder, giving us diabetic_data.csv and
    IDS_mapping.csv, which is everything the rest of the project needs
    """
    # open the zip file we just downloaded in read mode
    with zipfile.ZipFile(ZIP_DESTINATION, "r") as zip_file:
        # extractall pulls every file inside the zip out into the data folder
        zip_file.extractall(DATA_FOLDER)
    # let the person running this know exactly where to find the extracted files
    print(f"extracted diabetic_data.csv and IDS_mapping.csv into {DATA_FOLDER}/")


def fetch_and_prepare_dataset():
    """
    the single function the rest of the project calls: downloads the zip, then extracts
    it, so cli.py only ever needs to call one function to get usable data on disk
    """
    # step one: get the zip file onto disk
    download_dataset()
    # step two: unpack the csv files we actually need out of that zip
    extract_dataset()


# this block only runs when the file is executed directly (python fetch_data.py), not
# when it's imported by another file like cli.py, which is the standard python pattern
# for making a file both an importable module and a standalone script
if __name__ == "__main__":
    fetch_and_prepare_dataset()

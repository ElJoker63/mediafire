import hashlib
import http.client
import urllib.parse
from re import findall
from time import sleep
from io import BytesIO
from gzip import GzipFile
from requests import get
from gazpacho import Soup
from threading import BoundedSemaphore, Thread, Event
from os import path, makedirs, remove, chdir, getcwd

class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

NON_ALPHANUM_FILE_OR_FOLDER_NAME_CHARACTERS = "-_. "
NON_ALPHANUM_FILE_OR_FOLDER_NAME_CHARACTER_REPLACEMENT = "-"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Accept-Encoding": "gzip",
}

def hash_file(filename: str) -> str:
    h = hashlib.sha256()
    with open(filename, "rb") as file:
        chunk = 0
        while chunk != b"":
            chunk = file.read(1024)
            h.update(chunk)
    return h.hexdigest()

def normalize_file_or_folder_name(filename: str) -> str:
    return "".join(
        [
            (
                char
                if (
                    char.isalnum()
                    or char in NON_ALPHANUM_FILE_OR_FOLDER_NAME_CHARACTERS
                )
                else NON_ALPHANUM_FILE_OR_FOLDER_NAME_CHARACTER_REPLACEMENT
            )
            for char in filename
        ]
    )

def print_error(link: str):
    print(
        f"{bcolors.FAIL}Deleted file or Dangerous File Blocked\n"
        f"{bcolors.WARNING}Take a look if you want to be sure: {link}{bcolors.ENDC}"
    )

def get_files_or_folders_api_endpoint(filefolder: str, folder_key: str, chunk: int = 1, info: bool = False) -> str:
    return (
        f"https://www.mediafire.com/api/1.4/folder"
        f"/{'get_info' if info else 'get_content'}.php?r=utga&content_type={filefolder}"
        f"&filter=all&order_by=name&order_direction=asc&chunk={chunk}"
        f"&version=1.5&folder_key={folder_key}&response_format=json"
    )

def get_info_endpoint(file_key: str) -> str:
    return f"https://www.mediafire.com/api/file/get_info.php?quick_key={file_key}&response_format=json"

def get_folders(folder_key: str, folder_name: str, threads_num: int, first: bool = False) -> None:
    if first:
        r = get(get_files_or_folders_api_endpoint("folder", folder_key, info=True))
        folder_name = path.join(
            folder_name,
            normalize_file_or_folder_name(r.json()["response"]["folder_info"]["name"]),
        )
    if not path.exists(folder_name):
        makedirs(folder_name)
    chdir(folder_name)
    download_folder(folder_key, threads_num)
    folder_content = get(
        get_files_or_folders_api_endpoint("folders", folder_key)
    ).json()["response"]["folder_content"]
    if "folders" in folder_content:
        for folder in folder_content["folders"]:
            get_folders(folder["folderkey"], folder["name"], threads_num)
            chdir("..")

def download_folder(folder_key: str, threads_num: int) -> None:
    data = []
    chunk = 1
    more_chunks = True
    try:
        while more_chunks:
            r_json = get(
                get_files_or_folders_api_endpoint("files", folder_key, chunk=chunk)
            ).json()
            more_chunks = r_json["response"]["folder_content"]["more_chunks"] == "yes"
            data += r_json["response"]["folder_content"]["files"]
            chunk += 1
    except KeyError:
        print("Invalid link")
        return
    event = Event()
    threadLimiter = BoundedSemaphore(threads_num)
    total_threads = []
    for file in data:
        total_threads.append(
            Thread(
                target=download_file,
                args=(
                    file,
                    event,
                    threadLimiter,
                ),
            )
        )
    for thread in total_threads:
        thread.start()
    try:
        while True:
            if all(not t.is_alive() for t in total_threads):
                break
            sleep(0.01)
    except KeyboardInterrupt:
        print(f"{bcolors.WARNING}Closing all threads{bcolors.ENDC}")
        event.set()
        for thread in total_threads:
            thread.join()
        print(f"{bcolors.WARNING}{bcolors.BOLD}Download interrupted{bcolors.ENDC}")
        exit(0)

def get_file(key: str, output_path: str = None) -> None:
    file_data = get(get_info_endpoint(key)).json()["response"]["file_info"]
    if output_path:
        current_dir = getcwd()
        filename = path.join(output_path, file_data["filename"])
        chdir(output_path)
    else:
        filename = file_data["filename"]
    download_file(file_data)
    if output_path:
        chdir(current_dir)
    return filename

def get_download_progress(filename):
    if not hasattr(get_download_progress, "progress"):
        get_download_progress.progress = {}
    return get_download_progress.progress.get(filename, (0, 0))

def download_file(file: dict, event: Event = None, limiter: BoundedSemaphore = None) -> None:
    if limiter:
        limiter.acquire()
    download_link = file["links"]["normal_download"]
    filename = normalize_file_or_folder_name(file["filename"])
    if path.exists(filename):
        if hash_file(filename) == file["hash"]:
            print(f"{bcolors.WARNING}{filename}{bcolors.ENDC} already exists, skipping")
            if limiter:
                limiter.release()
            return
        else:
            print(
                f"{bcolors.WARNING}{filename}{bcolors.ENDC} already exists but corrupted, downloading again"
            )
    print(f"{bcolors.OKBLUE}Downloading {filename}{bcolors.ENDC}")
    if event:
        if event.is_set():
            if limiter:
                limiter.release()
            return
    parsed_url = urllib.parse.urlparse(download_link)
    conn = http.client.HTTPConnection(parsed_url.netloc)
    conn.request(
        "GET",
        parsed_url.path,
        headers=HEADERS,
    )
    response = conn.getresponse()
    if response.getheader("Content-Encoding") == "gzip":
        compressed_data = response.read()
        conn.close()
        with GzipFile(fileobj=BytesIO(compressed_data)) as f:
            html = f.read().decode("utf-8")
            soup = Soup(html)
            download_link = soup.find("a", {"id": "downloadButton"}).attrs["href"]
            parsed_url = urllib.parse.urlparse(download_link)
            conn = http.client.HTTPConnection(parsed_url.netloc)
            conn.request(
                "GET",
                parsed_url.path,
                headers=HEADERS,
            )
            response = conn.getresponse()
    if 400 <= response.status < 600:
        conn.close()
        print_error(download_link)
        if limiter:
            limiter.release()
        return
    
    total_size = int(response.getheader('Content-Length', 0))
    bytes_downloaded = 0
    
    with open(filename, "wb") as f:
        while True:
            chunk = response.read(4096)
            if event and event.is_set():
                conn.close()
                f.close()
                remove(filename)
                print(
                    f"{bcolors.WARNING}Partially downloaded {filename} deleted{bcolors.ENDC}"
                )
                if limiter:
                    limiter.release()
                return
            if not chunk:
                break
            bytes_downloaded += len(chunk)
            f.write(chunk)
            
            # Update progress
            if not hasattr(get_download_progress, "progress"):
                get_download_progress.progress = {}
            get_download_progress.progress[filename] = (bytes_downloaded, total_size)
    
    conn.close()
    print(f"{bcolors.OKGREEN}{filename}{bcolors.ENDC} downloaded")
    if limiter:
        limiter.release()

def download_from_mediafire(url, output_path='.', threads=10):
    folder_or_file = findall(
        r"mediafire\.com/(folder|file|file_premium)\/([a-zA-Z0-9]+)", url
    )
    if not folder_or_file:
        return "Invalid link"
    t, key = folder_or_file[0]
    if t in {"file", "file_premium"}:
        return get_file(key, output_path)
    elif t == "folder":
        get_folders(key, output_path, threads, first=True)
        return "All downloads completed"
    else:
        return "Invalid link"

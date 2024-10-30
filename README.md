# Mediafire for Python

![Mediafire](https://static.mediafire.com/images/backgrounds/header/mf_logo_u1_full_color_reversed.svg)

This is a Python module that allows you to download files and folders from Mediafire. It supports multi-threading for faster downloads and provides error handling for deleted or blocked files.

## Installation

You can install the module using pip:

pip install git+https://github.com/ElJoker63/mediafire.git

## Usage

To use the module, simply import the `download_from_mediafire()` function and call it with the Mediafire URL, output path, and number of threads:

```python
from mediafire import download_from_mediafire

url = 'https://www.mediafire.com/folder/example_folder'
output_path = 'downloads'
threads = 10

result = download_from_mediafire(url, output_path, threads)
print(result)
```

The function will return the filename of the downloaded file or a message indicating that the download was successful for a folder.
Features

Download files and folders from Mediafire
Support for multi-threading to speed up downloads
Error handling for deleted or blocked files
Automatic normalization of filenames to avoid issues with special characters
Resumable downloads for partially downloaded files

Dependencies
The module uses the following Python libraries:

- hashlib
- http.client
- urllib.parse
- re
- time
- io
- gzip
- requests
- gazpacho
- threading
- os

Contributing
If you find any issues or have suggestions for improvements, feel free to open an issue or submit a pull request on the GitHub repository.
License
This project is licensed under the MIT License.
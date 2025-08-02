# find-torrent-files

A Python library for finding torrent file data in a filesystem.

Imagine you've:

1. downloaded a torrent containing a large file (e.g., a multi-gigabyte movie),
2. copied/moved/renamed the large file somewhere in your filesystem, and
3. deleted files from the torrent downloads directory.

Well, now you're in a pickle if you want to re-add this torrent to your client.
You don't know where the large file is and you don't want to re-download the
whole thing (your ratio is already low enough).

Or, you may have gotten rid of some small supplemental files (e.g., `.nfo` or
subtitle files) but still have the large file. These are tolerable to
redownload.

**Enter `find-torrent-files`**: This script helps you find the large file in
your filesystem and verify that it matches the torrent's metadata. Small amounts
of missing data are acceptable (10 MiB by default, configurable).

# Process

1. Put all the torrents you wish to look for in the cwd's `torrents/` directory.
   The torrents should be in `.torrent` format. See `TORRENTS_DIR`.
2. For each file in each torrent, look in the search dirs (i.e., where you've
   copied/moved/renamed the large file) for files that match the torrent file
   size. See `SEARCH_DIRS`. File size retrieval is super fast, so this is a good
   step to find candidates. If most of the data of the torrent is found, the
   file is considered a match. (Defaults to 10 MiB, but can be configured with
   `FAIL_THRESHOLD_BYTES`.)
3. Continuing with each file in each torrent, if a file that (mostly) matches
   the size is found, read the file in pieces and compare the SHA1 hash to the
   pieces in the torrent metadata. If most of the pieces match, the file is
   considered a match. (Defaults to 10 MiB worth of pieces, but can be
   configured with `FAIL_THRESHOLD_BYTES`.)
4. If the hashes (mostly) match, the file is considered a match and the torrent
   is considered found. Then, `find-torrent-files` will **hardlink** the
   torrent's data files to the `TORRENT_CLIENT_DOWNLOAD_DIR` directory with
   proper naming and directory structure, and the torrent file is moved to the
   `TORRENTS_TO_IMPORT_DIR` directory for import into your torrent client.

# Usage

```bash
uv run main.py
```

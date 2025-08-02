# find-torrent-files

A Python script for finding torrent file data in a filesystem.

Imagine you've:

1. downloaded a torrent containing a large file (e.g., a multi-gigabyte movie),
2. copied/moved/renamed the large file somewhere in your filesystem, and
3. deleted the files from your torrent client's download directory.

Well, now you're in a pickle if you want to re-add this torrent to your client.
You don't know where the large file is and you don't want to re-download the
whole thing (your ratio is already low enough). You may be able to do this
manually for a few instances, but what if you have hundreds of torrents?

Or, you may have gotten rid of some small supplemental files (e.g., `.nfo` or
subtitle files) but still have the large file somewhere on your system. These
are tolerable to redownload (by our standards).

**Enter `find-torrent-files`**: This script helps you find the large file in
your filesystem and verify that it matches the torrent's metadata. Small amounts
of missing data are acceptable (10 MiB by default, configurable).

## How it works

1. Before running, put all the `.torrent` files you wish to search for in a
   directory (such as `torrents/`). Pass this path to the `--torrents-dir`
   option.

2. For each file in each torrent, look in the search directories (i.e., where
   you've copied/moved/renamed the large file, passed with `--search-dir` one or
   more times) for files that match the torrent file size.

   File size retrieval is super fast, so quickly narrows down candidates. If
   most of the data of the torrent is found, the file is considered a match.
   (Defaults to at most 10 MiB of missing files, but can be configured with
   `--fail-threshold-bytes`.)

3. Continuing with each torrent, if most of the files' data is found by size,
   compare the files by piece using their SHA1 hashlist (this is how bittorrent
   checks integrity). If most of the pieces match, the torrent is considered a
   match. (Defaults to 10 MiB worth of missing pieces, but can be configured
   with `--fail-threshold-bytes`.) Note that this step takes a long time.

4. If the pieces (mostly) match, then the torrent is considered found. Then,
   `find-torrent-files` will **hardlink** the torrent's data files to the
   `--client-download-dir` directory with proper naming and directory
   structure, and the torrent file is moved to the `--matched-torrents-dir`
   directory for import into your torrent client.

## Usage

```bash
git clone https://github.com/t-mart/find-torrent-files.git
cd find-torrent-files
uv run find-torrent-files --help
```

Example dry run:

```bash
uv run find-torrent-files \
  --dry-run \
  --search-dir ~/Movies \
  --client-download-dir ~/Downloads/ \
  --torrents-dir ./torrents \
  --matched-torrents-dir ./matched-torrents
```

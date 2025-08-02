from pathlib import Path
from collections import defaultdict
import humanize

from lib.torrent import Torrent, FileMapping

SEARCH_DIRS = [
  Path("/data/Movies"),
  Path("/data/TV Shows"),
]
TORRENT_CLIENT_DOWNLOAD_DIR = Path("/data/Downloads")
FAIL_THRESHOLD_BYTES = 10 * 1024 * 1024  # 10 MiB

TORRENTS_DIR = Path("./torrents")
TORRENTS_TO_IMPORT_DIR = Path("./torrents_to_import")

TORRENTS_DIR.mkdir(parents=True, exist_ok=True)
TORRENTS_TO_IMPORT_DIR.mkdir(parents=True, exist_ok=True)


def get_data_dir_sizes() -> dict[int, list[Path]]:
  data_dir_sizes: dict[int, list[Path]] = defaultdict(list)
  for data_dir in SEARCH_DIRS:
    for file in data_dir.rglob("*"):
      if file.is_file():
        size = file.stat().st_size
        data_dir_sizes[size].append(file)
  return data_dir_sizes


if __name__ == "__main__":
  data_dir_sizes = get_data_dir_sizes()

  torrents_files = list(TORRENTS_DIR.glob("*.torrent"))

  fail_threshold_bytes = 100 * 1024 * 1024

  for torrent_file in torrents_files:
    torrent = Torrent.from_file(torrent_file)
    # print(torrent_file)
    torrent_size = torrent.size
    human_torrent_size = humanize.naturalsize(torrent_size, binary=True)
    file_count = len(torrent.files)
    missing_file_count = 0
    missing_bytes_count = 0
    file_mappings: list[FileMapping] = []
    for file in torrent.files:
      human_file_size = humanize.naturalsize(file.length, binary=True)
      matches = data_dir_sizes.get(file.length, [])
      if len(matches) != 1:
        missing_file_count += 1
        missing_bytes_count += file.length
      else:
        found_file = matches[0]
        file_mappings.append(
          FileMapping(fs_file_path=found_file, torrent_file_path=file.path)
        )

    print(f"Torrent: {torrent_file.name}")
    print(
      f"Missing files: {missing_file_count} / {file_count} ({missing_file_count / file_count:.2%})"
    )

    human_missing_bytes = humanize.naturalsize(missing_bytes_count, binary=True)
    print(
      f"Missing bytes: {human_missing_bytes} / {human_torrent_size} ({missing_bytes_count / torrent_size:.2%})"
    )

    if missing_bytes_count >= fail_threshold_bytes:
      print(f"❌ Skipping torrent due to high missing bytes: {humanize.naturalsize(missing_bytes_count, binary=True)}")
      print("-" * 40)
      continue

    total_pieces = len(torrent.pieces)
    mismatched_pieces = 0
    for piece_match in torrent.check_pieces(file_mappings=file_mappings):
      if not piece_match:
        mismatched_pieces += 1
    mismatched_pieces_bytes = mismatched_pieces * torrent.piece_length
    print(f"Mismatched pieces: {mismatched_pieces:,} / {total_pieces:,} ({mismatched_pieces / total_pieces:.2%})")

    if mismatched_pieces_bytes >= fail_threshold_bytes:
      print(f"❌ Skipping torrent due to high mismatched pieces: {humanize.naturalsize(mismatched_pieces_bytes, binary=True)}")
      print("-" * 40)
      continue

    # now, hardlink the files to the downloads directory
    for file_mapping in file_mappings:
      fs_file_path = file_mapping.fs_file_path
      download_file_path = TORRENT_CLIENT_DOWNLOAD_DIR / file_mapping.torrent_file_path
      if download_file_path.exists():
        raise FileExistsError(
          f"Download file already exists: {download_file_path}"
        )
      download_file_path.parent.mkdir(parents=True, exist_ok=True)
      download_file_path.hardlink_to(fs_file_path)
      print(f"Linked {fs_file_path} to {download_file_path}")

    # and move the torrent file to the import directory
    import_torrent_path = TORRENTS_TO_IMPORT_DIR / torrent_file.name
    torrent_file.rename(import_torrent_path)
    print(f"Moved torrent file to {import_torrent_path}")
    print(f"✅ Processed torrent: {torrent_file.name}")

    print("-" * 40)

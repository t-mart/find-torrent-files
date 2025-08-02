from pathlib import Path
from collections import defaultdict
import contextlib
from dataclasses import dataclass

import humanize

from find_torrent_files.torrent import Torrent, FileMapping


def get_data_dir_sizes(search_dirs: list[Path]) -> dict[int, list[Path]]:
  data_dir_sizes: dict[int, list[Path]] = defaultdict(list)
  for data_dir in search_dirs:
    for file in data_dir.rglob("*"):
      if file.is_file():
        size = file.stat().st_size
        data_dir_sizes[size].append(file)
  return data_dir_sizes


@contextlib.contextmanager
def separate_stdout():
  yield
  print("-" * 40)


@dataclass
class FindSizeMatchResult:
  file_mappings: list[FileMapping]
  missing_file_count: int
  missing_bytes_count: int


def find_size_matches(
  *,
  data_dir_sizes: dict[int, list[Path]],
  torrent: Torrent,
) -> FindSizeMatchResult:
  missing_file_count = 0
  missing_bytes_count = 0

  matched_file_mappings: list[FileMapping] = []

  for file in torrent.files:
    matches = data_dir_sizes.get(file.length, [])
    if len(matches) != 1:
      missing_file_count += 1
      missing_bytes_count += file.length
      if len(matches) > 1:
        print(
          f"Found {len(matches)} multiple size matches for {file.path}, considering "
          "missing"
        )
    else:
      found_file = matches[0]
      matched_file_mappings.append(
        FileMapping(fs_file_path=found_file, torrent_file_path=file.path)
      )

  return FindSizeMatchResult(
    file_mappings=matched_file_mappings,
    missing_file_count=missing_file_count,
    missing_bytes_count=missing_bytes_count,
  )


@dataclass
class CheckPiecesResult:
  mismatched_pieces: int


def check_pieces(
  *, torrent: Torrent, file_mappings: list[FileMapping], show_progress: bool = False
) -> CheckPiecesResult:
  mismatched_pieces = 0
  for piece_match in torrent.check_pieces(
    file_mappings=file_mappings, show_progress=show_progress
  ):
    if not piece_match:
      mismatched_pieces += 1

  return CheckPiecesResult(mismatched_pieces=mismatched_pieces)


def process_match(
  *,
  torrent_file: Path,
  matched_file_mappings: list[FileMapping],
  client_download_dir: Path,
  matched_torrents_dir: Path,
  dry_run: bool = False,
):
  # hardlink the files to the downloads directory
  for file_mapping in matched_file_mappings:
    fs_file_path = file_mapping.fs_file_path
    download_file_path = client_download_dir / file_mapping.torrent_file_path
    if download_file_path.exists():
      raise FileExistsError(f"Download file already exists: {download_file_path}")
    if not dry_run:
      download_file_path.parent.mkdir(parents=True, exist_ok=True)
      download_file_path.hardlink_to(fs_file_path)
      print(f"Hardlink {fs_file_path} to {download_file_path}")
    else:
      print(f"Would hardlink {fs_file_path} to {download_file_path}")

  # and move the torrent file to the import directory
  import_torrent_path = matched_torrents_dir / torrent_file.name
  if not dry_run:
    matched_torrents_dir.mkdir(parents=True, exist_ok=True)
    torrent_file.rename(import_torrent_path)
    print(f"Move torrent file to {import_torrent_path}")
  else:
    print(f"Would move torrent file to {import_torrent_path}")
  print(f"✅ Processed torrent: {torrent_file.name}")


def find_torrent(
  *,
  data_dir_sizes: dict[int, list[Path]],
  torrent_file: Path,
  client_download_dir: Path,
  fail_threadhold_bytes: int,
  matched_torrents_dir: Path,
  dry_run: bool = False,
  show_progress: bool = False,
) -> bool:
  torrent = Torrent.from_file(torrent_file)

  size_match_result = find_size_matches(data_dir_sizes=data_dir_sizes, torrent=torrent)
  missing_file_count = size_match_result.missing_file_count
  missing_bytes_count = size_match_result.missing_bytes_count
  matched_file_mappings = size_match_result.file_mappings

  file_count = len(torrent.files)
  print(f"Torrent: {torrent_file.name}")
  print(
    f"Missing files: {missing_file_count} / {file_count} "
    f"({missing_file_count / file_count:.2%})"
  )

  human_missing_bytes = humanize.naturalsize(missing_bytes_count, binary=True)
  human_torrent_size = humanize.naturalsize(torrent.size, binary=True)
  print(
    f"Missing bytes: {human_missing_bytes} / {human_torrent_size} "
    f"({missing_bytes_count / torrent.size:.2%})"
  )

  human_fail_threadhold_bytes = humanize.naturalsize(fail_threadhold_bytes, binary=True)
  if missing_bytes_count > fail_threadhold_bytes:
    print(
      f"❌ Skipping torrent due to missing > {human_fail_threadhold_bytes}: "
      f"{humanize.naturalsize(missing_bytes_count, binary=True)}"
    )
    return False

  check_pieces_result = check_pieces(
    torrent=torrent, file_mappings=matched_file_mappings, show_progress=show_progress
  )
  total_pieces = len(torrent.pieces)
  mismatched_pieces = check_pieces_result.mismatched_pieces
  mismatched_pieces_bytes = check_pieces_result.mismatched_pieces * torrent.piece_length
  print(
    f"Mismatched pieces: {mismatched_pieces:,} / {total_pieces:,} "
    f"({mismatched_pieces / total_pieces:.2%})"
  )

  if mismatched_pieces_bytes > fail_threadhold_bytes:
    print(
      f"❌ Skipping torrent due to missing pieces > {human_fail_threadhold_bytes}: "
      f"{humanize.naturalsize(mismatched_pieces_bytes, binary=True)}"
    )
    return False

  process_match(
    torrent_file=torrent_file,
    matched_file_mappings=matched_file_mappings,
    client_download_dir=client_download_dir,
    matched_torrents_dir=matched_torrents_dir,
    dry_run=dry_run,
  )

  return True


def find_torrents(
  search_dirs: list[Path],
  client_download_dir: Path,
  fail_threadhold_bytes: int,
  torrents_dir: Path,
  matched_torrents_dir: Path,
  dry_run: bool = False,
  show_progress: bool = True,
):
  data_dir_sizes = get_data_dir_sizes(search_dirs)

  torrents_files = list(torrents_dir.glob("*.torrent"))

  for torrent_file in torrents_files:
    with separate_stdout():
      find_torrent(
        data_dir_sizes=data_dir_sizes,
        torrent_file=torrent_file,
        client_download_dir=client_download_dir,
        fail_threadhold_bytes=fail_threadhold_bytes,
        matched_torrents_dir=matched_torrents_dir,
        dry_run=dry_run,
        show_progress=show_progress,
      )

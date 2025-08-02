from typing_extensions import Annotated
from pathlib import Path

import typer

from find_torrent_files.find import find_torrents


def find_cli(
  search_dir: Annotated[
    list[Path],
    typer.Option(
      exists=True, file_okay=False, help="Directories to search for data files"
    ),
  ],
  client_download_dir: Annotated[
    Path,
    typer.Option(
      help="Directory where your torrent client downloads files. Matched files will be hardlinked here"
    ),
  ],
  torrents_dir: Annotated[
    Path, typer.Option(help="Directory containing torrent files")
  ],
  matched_torrents_dir: Annotated[
    Path,
    typer.Option(help="Directory to which matched torrents are moved"),
  ] = Path("./matched-torrents"),
  fail_threshold_bytes: Annotated[
    int,
    typer.Option(help="Threshold in bytes for missing files to fail"),
  ] = 50 * 1024 * 1024,
  dry_run: Annotated[
    bool,
    typer.Option(
      "--dry-run",
      "-d",
      is_flag=True,
      help="If set, no data files will be hardlinked nor torrent files moved",
    ),
  ] = False,
  show_progress: Annotated[
    bool,
    typer.Option(
      "--show-progress",
      "-p",
      is_flag=True,
      help="If set, shows progress bars for file matching and piece checking",
    ),
  ] = True,
):
  find_torrents(
    search_dirs=search_dir,
    client_download_dir=client_download_dir,
    fail_threshold_bytes=fail_threshold_bytes,
    torrents_dir=torrents_dir,
    matched_torrents_dir=matched_torrents_dir,
    dry_run=dry_run,
    show_progress=show_progress,
  )


typer.run(find_cli)

from typing import Iterator, IO
import bencodepy
from pathlib import Path
from dataclasses import dataclass
from .nullio import NullBytesIO
import hashlib
import math


@dataclass
class TorrentFile:
  length: int
  path: Path

  @classmethod
  def from_files_dict(cls, file_entry: dict[bytes, int | list[bytes]], root: Path):
    length = file_entry.get(b"length")
    path_segments = file_entry.get(b"path")
    path = root / Path(*[segment.decode("utf-8") for segment in path_segments])
    return cls(length=length, path=path)


@dataclass
class FileMapping:
  fs_file_path: Path
  torrent_file_path: Path


@dataclass
class Torrent:
  name: Path
  files: list[TorrentFile]
  piece_length: int
  pieces: list[bytes]

  @classmethod
  def from_file(cls, file_path: Path):
    with open(file_path, "rb") as f:
      torrent_data = bencodepy.decode(f.read())

    info = torrent_data.get(b"info")

    name = Path(info.get(b"name").decode("utf-8"))

    piece_length = info.get(b"piece length")

    pieces_value = info.get(b"pieces")
    pieces = [pieces_value[i : i + 20] for i in range(0, len(pieces_value), 20)]

    files_value = info.get(b"files")
    if files_value is None:
      files = [TorrentFile(length=info.get(b"length"), path=name)]
    else:
      files = [
        TorrentFile.from_files_dict(file, root=name) for file in info.get(b"files", [])
      ]

    return cls(
      name=name,
      piece_length=piece_length,
      pieces=pieces,
      files=files,
    )

  @property
  def hashlist(self) -> bytes:
    return b"".join(self.pieces)

  @property
  def size(self) -> int:
    return sum(file.length for file in self.files)

  def check_pieces(self, file_mappings: list[FileMapping]) -> Iterator[bool]:
    """
    Checks the integrity of the torrent pieces against their SHA-1 hashes.
    Args:
        file_mappings: A list of FileMapping objects that map torrent files to their
                       corresponding filesystem paths. To allow for missing files,
                       the mapping can omit entries for files that are unavailable. In
                       this case, the piece will be checked against null bytes.

    Yields:
        bool: True if the piece matches the expected hash, False otherwise.
    """
    piece_reader = PieceReader.from_torrent(self, file_mappings)
    for piece_index, piece in enumerate(piece_reader.read()):
      yield hashlib.sha1(piece).digest() == self.pieces[piece_index]


class PieceReader:
  def __init__(
    self,
    *,
    piece_length: int,
    torrent_files: list[tuple[int, Path]] = [],
    file_mappings: dict[Path, Path] = {},
  ):
    if piece_length < 1024 * 16:
      raise ValueError("Piece length must be at least 16 KiB.")
    log2_piece_length = math.log2(piece_length)
    if not log2_piece_length.is_integer():
      raise ValueError("Piece length must be a power of 2.")
    self.piece_length = piece_length
    self.torrent_files = torrent_files
    self.file_mappings = file_mappings

  @classmethod
  def from_torrent(cls, torrent: Torrent, file_mappings: list[FileMapping]):
    return cls(
      piece_length=torrent.piece_length,
      torrent_files=[(file.length, file.path) for file in torrent.files],
      file_mappings={fm.torrent_file_path: fm.fs_file_path for fm in file_mappings},
    )

  def read(self) -> Iterator[bytes]:
    # return pieces of piece_length bytes from the torrent files. this views the torrent
    # files as a contiguous byte stream ordered in the way they are listed in the
    # torrent. if the torrent file is not mapped to a fs file, return null-bytes for the
    # piece. if the length of the torrent is not a multiple of piece_length, the last
    # piece will be shorter than piece_length. also, pieces may span multiple torrent
    # files.
    buffer = bytearray()

    # fast fail if fs file size does not exist or does not match torrent file size
    for torrent_file_size, torrent_file_path in self.torrent_files:
      fs_file_path = self.file_mappings.get(torrent_file_path)
      if fs_file_path is None:
        continue
      if not fs_file_path.is_file():
        raise FileNotFoundError(
          f"File {fs_file_path} not found for torrent's {torrent_file_path}"
        )
      size = fs_file_path.stat().st_size
      if size != torrent_file_size:
        raise ValueError(
          f"Torrent file size {torrent_file_size} does not match fs file size {size} for {torrent_file_path}"
        )

    for file_length, torrent_file_path in self.torrent_files:
      fs_file_path = self.file_mappings.get(torrent_file_path)

      if fs_file_path is None:
        file = NullBytesIO(size=file_length)
      else:
        file = open(fs_file_path, "rb")

      while True:
        bytes_to_read = self.piece_length - len(buffer)
        data = file.read(bytes_to_read)

        if not data:
          break

        buffer.extend(data)

        if len(buffer) == self.piece_length:
          yield bytes(buffer)
          buffer.clear()

      file.close()

    if buffer:
      yield bytes(buffer)


if __name__ == "__main__":
  import sys

  if len(sys.argv) != 2:
    print("Usage: python torrent.py <torrent_file_path>")
    sys.exit(1)

  torrent_file_path = Path(sys.argv[1])
  torrent = Torrent.from_file(torrent_file_path)
  print(f"Torrent Name: {torrent.name}")
  print(f"Total Size: {torrent.size} bytes")
  print(f"Number of Files: {len(torrent.files)}")
  for file in torrent.files:
    print(f" - {file.path}: {file.length} bytes")

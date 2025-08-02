import io
import os

class NullBytesIO(io.RawIOBase):
    """
    A file-like object that produces a specified number of null bytes when read.

    This class implements the io.RawIOBase interface, making it compatible
    with other modules that expect binary file objects (like io.BufferedReader).
    It is seekable and readable, but not writable.
    """

    def __init__(self, size: int):
        """
        Initializes the stream.

        Args:
            size: The total number of null bytes this stream should produce.
        """
        if size < 0:
            raise ValueError("Size must be a non-negative integer.")
        self._size = size
        self._position = 0

    def readable(self) -> bool:
        """Returns True, as the stream is readable."""
        return True

    def writable(self) -> bool:
        """Returns False, as the stream is not writable."""
        return False

    def seekable(self) -> bool:
        """Returns True, as the stream supports seeking."""
        return True

    def tell(self) -> int:
        """Returns the current stream position."""
        return self._position

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        """
        Change the stream position to the given byte offset.

        Args:
            offset: The offset is interpreted relative to the position indicated by whence.
            whence: The default value for whence is SEEK_SET (absolute file positioning).
                    Other values are SEEK_CUR (seek relative to the current position) and
                    SEEK_END (seek relative to the file's end).

        Returns:
            The new absolute position.
        """
        if whence == os.SEEK_SET:
            new_pos = offset
        elif whence == os.SEEK_CUR:
            new_pos = self._position + offset
        elif whence == os.SEEK_END:
            new_pos = self._size + offset
        else:
            raise ValueError(f"Invalid whence value: {whence}")

        if not (0 <= new_pos <= self._size):
            raise ValueError("Seek position is out of bounds.")
        
        self._position = new_pos
        return self._position

    def read(self, size: int = -1) -> bytes:
        """
        Read and return up to `size` bytes.

        If the argument is omitted, None, or negative, data is read and
        returned until EOF is reached.

        Returns:
            A bytes object containing null bytes, or an empty bytes object at EOF.
        """
        if self._position >= self._size:
            # End of "file" has been reached
            return b''

        remaining_bytes = self._size - self._position

        if size == -1 or size > remaining_bytes:
            bytes_to_read = remaining_bytes
        else:
            bytes_to_read = size

        # The data is just null bytes
        data = b'\x00' * bytes_to_read
        self._position += bytes_to_read
        
        return data


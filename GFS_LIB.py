import win32file
import pywintypes
import math

def getfullneed(toread, filename_to_open, offset, disk=True):
    if disk:
        try:
            handle = win32file.CreateFile(
                filename_to_open,
                win32file.GENERIC_READ,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )
            SECTOR_SIZE = 512
            aligned_offset = (offset // SECTOR_SIZE) * SECTOR_SIZE
            offset_diff = offset - aligned_offset
            aligned_toread = math.ceil((toread + offset_diff) / SECTOR_SIZE) * SECTOR_SIZE
            win32file.SetFilePointer(handle, aligned_offset, win32file.FILE_BEGIN)
            result, data = win32file.ReadFile(handle, aligned_toread)
            return data[offset_diff:offset_diff + toread]
        except pywintypes.error as e:
            raise IOError(f"Error accessing disk: {e}")
        finally:
            if 'handle' in locals():
                win32file.CloseHandle(handle)
    else:
        with open(filename_to_open,"rb") as f:
            f.seek(offset)
            return f.read(toread)